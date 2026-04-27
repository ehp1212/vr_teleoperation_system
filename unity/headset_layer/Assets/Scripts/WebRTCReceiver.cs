using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.UI;
using Unity.WebRTC;
using NativeWebSocket;

public class WebRTCReceiver : MonoBehaviour
{
    private RTCPeerConnection pc;
    private WebSocket ws;

    [Header("UI")]
    public RawImage isaacImage;
    public RawImage hwImage;

    private int trackCount = 0;
    [SerializeField] private string _signalingIP = "172.20.10.8";
    [SerializeField] private int signalingPort = 8765;


    async void Start()
    {
        StartCoroutine(WebRTC.Update());
        
        // PeerConnection 
        pc = new RTCPeerConnection();

        pc.AddTransceiver(TrackKind.Video);
        pc.AddTransceiver(TrackKind.Video);

        pc.OnIceCandidate = candidate =>
        {
            if (candidate == null) return;

            if (candidate.SdpMLineIndex == null) return;
            var msg = new SignalingMessage
            {
                type = "candidate",
                candidate = candidate.Candidate,
                sdpMid = candidate.SdpMid,
                sdpMLineIndex = (int)candidate.SdpMLineIndex
            };

            ws.SendText(JsonUtility.ToJson(msg));
        };

        pc.OnConnectionStateChange = state =>
        {
            Debug.Log("[WebRTC] Connection state: " + state);
        };

        // Track
        pc.OnTrack = e =>
        {
            Debug.Log("[WebRTC] Track received");

            if (e.Track is VideoStreamTrack videoTrack)
            {
                int slot = trackCount;
                trackCount++;

                videoTrack.OnVideoReceived += texture =>
                {
                    Debug.Log("[WebRTC] Frame received: " + texture.width + "x" + texture.height);

                    if (slot == 0)
                    {
                        isaacImage.texture = texture;
                        Debug.Log("ISAAC assigned");
                    }
                    else if (slot == 1)
                    {
                        // hwImage.texture = texture;
                        Debug.Log("HARDWARE assigned");
                    }
                };
            }
        };

        // =====================
        // WebSocket 
        // =====================
        var url = $"ws://{_signalingIP}:{signalingPort}";
        Debug.Log("[WebSocket] Connecting to: " + url);
        
        ws = new WebSocket(url); // ← IP 수정 필수

        ws.OnOpen += () =>
        {
            Debug.Log("[WebSocket] Connected");
        };

        ws.OnMessage += (bytes) =>
        {
            string message = Encoding.UTF8.GetString(bytes);
            Debug.Log("[WebSocket] Received: " + message);

            var data = JsonUtility.FromJson<SignalingMessage>(message);

            if (data.type == "offer")
            {
                StartCoroutine(HandleOffer(data));
            }
            else if (data.type == "candidate")
            {
                var candidate = new RTCIceCandidate(new RTCIceCandidateInit
                {
                    candidate = data.candidate,
                    sdpMid = data.sdpMid,
                    sdpMLineIndex = data.sdpMLineIndex
                });

                pc.AddIceCandidate(candidate);
            }
        };
        
        ws.OnError += (e) =>
        {
            Debug.LogError("[WebSocket] Error: " + e);
        };

        ws.OnClose += (e) =>
        {
            Debug.Log("[WebSocket] Closed");
        };

        await ws.Connect();
    }

    // =====================
    // Offer -> Answer 
    // =====================
    IEnumerator HandleOffer(SignalingMessage data)
    {
        Debug.Log("[WebRTC] Handling Offer");

        var desc = new RTCSessionDescription
        {
            type = RTCSdpType.Offer,
            sdp = data.sdp
        };

        var remoteOp = pc.SetRemoteDescription(ref desc);
        yield return remoteOp;

        if (remoteOp.IsError)
        {
            Debug.LogError("[WebRTC] SetRemoteDescription failed: " + remoteOp.Error.message);
            yield break;
        }

        var answerOp = pc.CreateAnswer();
        yield return answerOp;

        if (answerOp.IsError)
        {
            Debug.LogError("[WebRTC] CreateAnswer failed: " + answerOp.Error.message);
            yield break;
        }

        var answer = answerOp.Desc;

        var localOp = pc.SetLocalDescription(ref answer);
        yield return localOp;

        if (localOp.IsError)
        {
            Debug.LogError("[WebRTC] SetLocalDescription failed: " + localOp.Error.message);
            yield break;
        }

        var msg = new SignalingMessage
        {
            type = "answer",
            sdp = answer.sdp
        };

        ws.SendText(JsonUtility.ToJson(msg));
        Debug.Log("[WebRTC] Answer sent");
    }

    void Update()
    {
        ws.DispatchMessageQueue();
    }

    async void OnDestroy()
    {
        await ws.Close();
        pc.Close();
    }
}

[Serializable]
public class SignalingMessage
{
    public string type;
    public string sdp;
    public string candidate;
    public string sdpMid;
    public int sdpMLineIndex;
}