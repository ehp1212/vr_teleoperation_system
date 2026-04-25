using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using NativeWebSocket;
using Unity.WebRTC;
using UnityEngine;

public class WebRTCClient : MonoBehaviour
{
    [SerializeField] private string _ipAddress = "172.20.10.8";

    private RTCPeerConnection _pc;
    private WebSocket _ws;
    
    private RTCDataChannel _poseChannel;
    private float _timer = 0f;
    private PoseMessage msg = new PoseMessage();

    async void Start()
    {
        StartCoroutine(WebRTC.Update());
        
        _ws = new WebSocket($"ws://{_ipAddress}:8765");
        Debug.Log($"Connecting to {_ipAddress}");
        
        _ws.OnOpen += OnWsOnOnOpen;
        _ws.OnClose += OnWsClose;
        _ws.OnError += OnWsError;
        _ws.OnMessage += OnMessageReceived;
        
        await _ws.Connect();
    }

    private void Update()
    {
        _timer += Time.deltaTime;
        
        _ws.DispatchMessageQueue();

        if (_timer > 0.02f)
        {
            SendPose();
            _timer = 0f;
        }
    }

    private void SendPose()
    {
        if (_poseChannel == null || _poseChannel.ReadyState != RTCDataChannelState.Open)
            return;
        
        // Pose msg 
        var serializedMsg = CreatePoseMessage();
        _poseChannel.Send(serializedMsg);
    }

    private void OnWsOnOnOpen()
    {
        Debug.Log($"[WebSocket] Connected");

        var roleMsg = new RoleMessage()
        {
            role = "headset"
        };
        
        SendJson(roleMsg);
        
        var readyMsg = new ReadyMessage
        {
            type = "ready", 
            from = "headset"
        };
        
        SendJson(readyMsg);
    }

    private void OnWsClose(WebSocketCloseCode closeCode)
    {
        Debug.Log($"[WebSocket] Disconnected");
    }

    private void OnWsError(string errorMsg)
    {
        Debug.LogError($"[WebSocket] Error: {errorMsg}");
    }

    private void OnMessageReceived(byte[] bytes)
    {
        var message = Encoding.UTF8.GetString(bytes);
        Debug.Log($"[Websocket] Received: {message}");

        var data = JsonUtility.FromJson<Message>(message);
        switch (data.type)
        {
            case "offer":
                StartCoroutine(HandleOffer(data));
                break;
            case "candidate":
                return;
            case "ice":
                Debug.Log("ICE received");

                var candidate = new RTCIceCandidate(new RTCIceCandidateInit()
                {
                    candidate = data.candidate,
                    sdpMid = data.sdpMid,
                    sdpMLineIndex = data.sdpMLineIndex
                });

                _pc.AddIceCandidate(candidate);
                return;
        }
    }

    private IEnumerator HandleOffer(Message data)
    {
        _pc = new RTCPeerConnection();

        _pc.OnConnectionStateChange = state =>
        {
            Debug.Log($"[Websocket] State: {state}");
        };

        _pc.OnIceConnectionChange = state =>
        {
            Debug.Log($"[Websocket] State: {state}");
        };

        SetupPeerConnection();
                
        // Set up remote
        var offerDesc = new RTCSessionDescription()
        {
            type = RTCSdpType.Offer,
            sdp = data.sdp
        };

        var op = _pc.SetRemoteDescription(ref offerDesc);
        yield return op;
        
        if (op.IsError)
        {
            Debug.LogError("[WebRTC] SetRemoteDescription failed: " + op.Error.message);
            yield break;
        }

        var answerOp = _pc.CreateAnswer();
        yield return answerOp;
        if (answerOp.IsError)
        {
            Debug.LogError("[WebRTC] CreateAnswer failed: " + answerOp.Error.message);
            yield break;
        }

        var answer = answerOp.Desc;
        
        var localOp = _pc.SetLocalDescription(ref answer);
        yield return localOp;

        if (localOp.IsError)
        {
            Debug.LogError("[WebRTC] SetLocalDescription failed: " + localOp.Error.message);
            yield break;
        }

        var msg = new AnswerMessage()
        {
            type = "answer",
            sdp = answer.sdp,
            from = "headset"
        };
        
        SendJson(msg);
        Debug.Log("[Websocket] Answer sent");
    }

    private void SetupPeerConnection()
    {
        _pc.OnDataChannel = channel =>
        {
            Debug.Log($"Data channel received: " + channel.Label);

            switch (channel.Label)
            {
                case "control":
                    SetupPoseChannel(channel);
                    break;
                
                case "depth":
                    SetUpDepthChannel(channel);
                    break;
            }
        };
        
       _pc.OnIceCandidate = candidate =>
        {
            if (candidate == null) return;

            SendJson(new IceMessage()
            {
                type = "ice",
                candidate = candidate.Candidate,
                sdpMid = candidate.SdpMid,
                sdpMLineIndex = candidate.SdpMLineIndex,
                from = "headset"
            });
        };
    }

    private void SetupPoseChannel(RTCDataChannel channel)
    {
        _poseChannel = channel;

        _poseChannel.OnOpen = () =>
        {
            Debug.Log("[Pose Channel] Open");
        };

        _poseChannel.OnClose = () =>
        {
            Debug.Log("[Pose Channel] Close");
        };
    }

    private void SetUpDepthChannel(RTCDataChannel channel)
    {
        var width = 0;
        var height = 0;

        var buffer = new List<byte>();
        var receivingPayload = false;
        
        channel.OnMessage = bytes =>
        {
            Debug.Log("Received message: " + bytes.Length);
            if (!receivingPayload)
            {
                // header
                width = BitConverter.ToInt32(bytes, 0);
                height = BitConverter.ToInt32(bytes, 4);
                var timestamp = BitConverter.ToDouble(bytes, 8);

                Debug.Log($"Depth Header: {width}x{height}: {timestamp}");

                buffer.Clear();
                receivingPayload = true;
                return;
            }
            
            buffer.AddRange(bytes);
            
            var expectedSize = width * height * 2; // float16

            if (buffer.Count > expectedSize)
            {
                var depthBytes = buffer.ToArray();
                ProcessDepth(depthBytes, width, height);
                
                receivingPayload = false;
            }
        };
        
    }

    private void ProcessDepth(byte[] depthBytes, int width, int height)
    {
        var count = depthBytes.Length / 2;
        var depth = new float[count];

        for (int i = 0; i < count; i++)
        {
            var half = BitConverter.ToUInt16(depthBytes, i * 2);
            depth[i] = half;
        }
        
        Debug.Log("Depth sample: " + depth[0]);
    }

    private void SendJson(object obj)
    {
        var json = JsonUtility.ToJson(obj);
        _ws.SendText(json);
    }

    private string CreatePoseMessage()
    {
        var q = transform.rotation;

        msg.type = "input";
        msg.rotation.x = q.x;
        msg.rotation.y = q.y;
        msg.rotation.z = q.z;
        msg.rotation.w = q.w;

        msg.control.x = 0;
        msg.control.y = 0;
        
        return JsonUtility.ToJson(msg);
    }
}

[Serializable]
public class PoseMessage
{
    public string type;

    public Vector4 rotation;
    public Vector2 control;
}

internal class AnswerMessage
{
    public string type;
    public string sdp;
    public string from;
}

internal class IceMessage
{
    public string type;
    public string candidate;
    public string sdpMid;
    public int? sdpMLineIndex;
    public string from;
}

[Serializable]
public class RoleMessage
{
    public string role;
}

public class ReadyMessage
{
    public string type;
    public string from;
}

[Serializable]
public class Message
{
    public string type;
    public string sdp;

    public string candidate;
    public string sdpMid;
    public int sdpMLineIndex;
}
