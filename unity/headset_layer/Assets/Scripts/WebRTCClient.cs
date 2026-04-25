using System;
using System.Collections;
using System.Collections.Generic;
using System.Net.NetworkInformation;
using System.Text;
using NativeWebSocket;
using Unity.WebRTC;
using UnityEngine;
using UnityEngine.UI;

public class WebRTCClient : MonoBehaviour
{
    [SerializeField] private string _ipAddress = "172.20.10.8";

    [Header("Texture")]
    [SerializeField] private RawImage _depthImage;
    
    private RTCPeerConnection _pc;
    private WebSocket _ws;
    
    private RTCDataChannel _poseChannel;
    private float _timer = 0f;
    private PoseMessage msg = new();

    private Texture2D _depthTexture;
    private byte[] _depthBuffer;

    private int _width = 320;
    private int _height = 240;
    
    private bool hasNewDepthData;
    private byte[] _lastestDepth;

    private const float maxRange = 5.0f;

    private void Awake()
    {
        _depthTexture = new Texture2D(_width, _height, TextureFormat.RGB24, false);
        _depthBuffer = new byte[_width * _height * 3];
        
        _depthImage.texture = _depthTexture;
    }

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
    
        // Publish pose data 
        if (_timer > 0.02f)
        {
            SendPose();
            _timer = 0f;
        }
        
        if (hasNewDepthData)
        {
            // header
            var w = BitConverter.ToInt32(_lastestDepth, 0);
            var h = BitConverter.ToInt32(_lastestDepth, 4);
            var timestamp = BitConverter.ToDouble(_lastestDepth, 8);

            // safety check
            if (w <= 0 || h <= 0 || w > 4096 || h > 4096)
            {
                Debug.LogError($"Invalid depth size: {w}x{h}");
                hasNewDepthData = false;
                return;
            }

            if (w != _width || h != _height)
            {
                _width = w;
                _height = h;

                _depthTexture = new Texture2D(_width, _height, TextureFormat.RGB24, false);
                _depthBuffer = new byte[_width * _height * 3];

                _depthImage.texture = _depthTexture;
            }

            var expectedPayloadSize = _width * _height * 2; // float16
            var actualPayloadSize = _lastestDepth.Length - 16;

            if (actualPayloadSize < expectedPayloadSize)
            {
                Debug.LogWarning($"Incomplete depth payload: {actualPayloadSize}/{expectedPayloadSize}");
                return;
            }
            
            var depthBytes = new byte[expectedPayloadSize];
            Buffer.BlockCopy(_lastestDepth, 16, depthBytes, 0, expectedPayloadSize);
            
            var depth = ConvertToFloat(depthBytes);
            UpdateTexture(depth);
            
            hasNewDepthData = false;
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

    #region Web Socket Callbacks

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

    #endregion

    private IEnumerator HandleOffer(Message data)
    {
        _pc = new RTCPeerConnection();

        _pc.OnConnectionStateChange = state =>
        {
            Debug.Log($"[Websocket] Connection State: {state}");
        };

        _pc.OnIceConnectionChange = state =>
        {
            Debug.Log($"[Websocket] ICE State: {state}");
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
        channel.OnMessage = bytes =>
        {
            if (bytes.Length < 16)
            {
                Debug.LogWarning("Depth packet too small");
                return;
            }

            hasNewDepthData = true;
            _lastestDepth = bytes;
        };
    }

    private float[] ConvertToFloat(byte[] bytes)
    {
        var count = bytes.Length / 2;
        var result = new float[count];

        for (var i = 0; i < count; i++)
        {
            var half = BitConverter.ToUInt16(bytes, i * 2);
            result[i] = HalfToFloat(half);
        }

        return result;
    }

    private float HalfToFloat(ushort value)
    {
        var sign = (value >> 15) & 0x00000001;
        var exponent = (value >> 10) & 0x0000001F;
        var mantissa = value & 0x000003FF;

        if (exponent == 0)
        {
            if (mantissa == 0)
            {
                return sign == 1 ? -0.0f : 0.0f;
            }
            else
            {
                return (float)((sign == 1 ? -1 : 1) *
                               mantissa *
                               Math.Pow(2, -24));
            }
        }
        else if (exponent == 31)
        {
            if (mantissa == 0)
            {
                return sign == 1 ? float.NegativeInfinity : float.PositiveInfinity;
            }
            else
            {
                return float.NaN;
            }
        }

        return (float)((sign == 1 ? -1 : 1) *
                       (1 + mantissa / 1024.0) *
                       Math.Pow(2, exponent - 15));
    }

    // Convert data to texture
    private void UpdateTexture(float[] depth)
    {
        var count = Mathf.Min(depth.Length, _depthBuffer.Length);
        for (var i = 0; i < count; i++)
        {
            var d = depth[i];
            var normalized = Mathf.Clamp01(d / maxRange);
            var v = (byte)(normalized * 255);

            var idx = i * 3;
            
            _depthBuffer[idx + 0] = v;
            _depthBuffer[idx + 1] = v;
            _depthBuffer[idx + 2] = v;
        }

        _depthTexture.LoadRawTextureData(_depthBuffer);
        _depthTexture.Apply();
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
