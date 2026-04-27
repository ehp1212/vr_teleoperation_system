using System;
using System.Collections;
using System.Text;
using NativeWebSocket;
using Unity.WebRTC;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UI;
using Utils;

public class WebRTCClient : MonoBehaviour
{
    private const string renderStage = "render";
    private const string recvStage = "recv";
    
    [Header("Connection")]
    [SerializeField] private string _ipAddress = "172.20.10.8";

    [Header("Control")]
    [SerializeField] private Transform _target;
    [SerializeField] private float _rotationDeadzone = 0.2f;
    private Quaternion _lastSentRotation = Quaternion.identity;
    [SerializeField] private InputActionReference _rightThumbstickAction;
    
    [Header("Texture")]
    [SerializeField] private RawImage _rgbImage;
    [SerializeField] private RawImage _depthImage;
    
    [Header("Telemetry")]
    [SerializeField] private Utils.TelemetryUI _telemetryUI;
    
    private RTCPeerConnection _pc;
    private WebSocket _ws;

    private RTCDataChannel _poseChannel;
    private float _timer = 0f;
    private PoseMessage msg = new();

    private int _trackCount = 0;

    private Utils.Logger _logger;
    
    private double _lastPoseSentTime; 
    private double _lastFrameTime;    
    
    public Texture2D DepthImage
    {
        get
        {
            if (_depthImage == null) return null;
            
            return _depthImage.texture as Texture2D;
        }
    }

    private void Awake()
    {
        _logger = new Utils.Logger("unity_log.jsonl");
    }

    async void Start()
    {
        StartCoroutine(WebRTC.Update());

        _ws = new WebSocket($"ws://{_ipAddress}:8765");

        _ws.OnOpen += OnWsOpen;
        _ws.OnClose += OnWsClose;
        _ws.OnError += OnWsError;
        _ws.OnMessage += OnMessageReceived;

        await _ws.Connect();
    }

    private void Update()
    {
        _ws.DispatchMessageQueue();
        var now = Time.realtimeSinceStartupAsDouble;

        if (_rgbImage.texture != null)
        {
            var displayLatency = (now - _lastPoseSentTime) * 1000.0;
        
            var frameGap = (now - _lastFrameTime) * 1000.0;
            _lastFrameTime = now;

            _logger.Log("render", 0, now, "rgb");

            if (_telemetryUI != null)
            {
                _telemetryUI.UpdateTelemetry(new TelemetryData
                {
                    renderTs = now,
                    latencyMs = displayLatency,
                    frameGapMs = frameGap,
                    isNewFrame = true
                });
            }
        }

        _timer += Time.deltaTime;
        if (_timer > 0.02f)
        {
            SendPose();
            _lastPoseSentTime = now; // 송신 시점 기록
            _timer = 0f;
        }
    }

    // ======================
    // WebSocket
    // ======================
    private void OnWsOpen()
    {
        Debug.Log("[WS] Connected");

        SendJson(new RoleMessage { role = "headset" });
        SendJson(new ReadyMessage { type = "ready", from = "headset" });
    }

    private void OnWsClose(WebSocketCloseCode code)
    {
        Debug.Log("[WS] Closed");
    }

    private void OnWsError(string err)
    {
        Debug.LogError("[WS] Error: " + err);
    }

    private void OnMessageReceived(byte[] bytes)
    {
        var message = Encoding.UTF8.GetString(bytes);
        var data = JsonUtility.FromJson<Message>(message);

        switch (data.type)
        {
            case "offer":
                StartCoroutine(HandleOffer(data));
                break;

            case "ice":
                var candidate = new RTCIceCandidate(new RTCIceCandidateInit()
                {
                    candidate = data.candidate,
                    sdpMid = data.sdpMid,
                    sdpMLineIndex = data.sdpMLineIndex
                });

                _pc.AddIceCandidate(candidate);
                break;
        }
    }

    // ======================
    // WebRTC
    // ======================
    private IEnumerator HandleOffer(Message data)
    {
        var config = default(RTCConfiguration);
        _pc = new RTCPeerConnection(ref config);

        _pc.OnConnectionStateChange = state =>
        {
            Debug.Log($"[PC] {state}");
        };
        
        SetupPeerConnection();
        
        var offerDesc = new RTCSessionDescription
        {
            type = RTCSdpType.Offer,
            sdp = data.sdp
        };

        yield return _pc.SetRemoteDescription(ref offerDesc);

        var answerOp = _pc.CreateAnswer();
        yield return answerOp;

        var answer = answerOp.Desc;
        yield return _pc.SetLocalDescription(ref answer);

        SendJson(new AnswerMessage
        {
            type = "answer",
            sdp = answer.sdp,
            from = "headset"
        });
    }

    private void SetupPeerConnection()
    {
        _pc.OnDataChannel = channel =>
        {
            Debug.Log($"[DC] {channel.Label}");

            if (channel.Label == "control")
                SetupPoseChannel(channel);
            else if (channel.Label == "depth")
                SetupDepthChannel(channel);
        };

        _pc.OnIceCandidate = candidate =>
        {
            if (candidate == null) return;

            SendJson(new IceMessage
            {
                type = "ice",
                candidate = candidate.Candidate,
                sdpMid = candidate.SdpMid,
                sdpMLineIndex = candidate.SdpMLineIndex ?? 0,
                from = "headset"
            });
        };

        _pc.OnTrack = e =>
        {
            Debug.Log("[PC] Track: " + e);

            if (e.Track is VideoStreamTrack videoStreamTrack)
            {
                var slot = _trackCount;
                _trackCount++;

                videoStreamTrack.OnVideoReceived += texture =>
                {
                    if (slot == 0) // RGB
                    {
                        _rgbImage.texture = texture;
                    }
                    else if (slot == 1) // Depth
                    {
                        _depthImage.texture = texture;
                    }
                };
            }
        };
    }

    // ======================
    // Pose
    // ======================
    private void SetupPoseChannel(RTCDataChannel channel)
    {
        _poseChannel = channel;

        channel.OnOpen = () => Debug.Log("[Pose] Open");
        channel.OnClose = () => Debug.Log("[Pose] Close");
    }

    private void SendPose()
    {
        if (_poseChannel == null || _poseChannel.ReadyState != RTCDataChannelState.Open)
            return;
        
        msg.type = "input";
        var input = _rightThumbstickAction.action.ReadValue<Vector2>();
        msg.control = new Vector2(input.x, input.y); 

        var currentRot = _target.rotation;
        var angleDiff = Quaternion.Angle(_lastSentRotation, currentRot);
        if (angleDiff > _rotationDeadzone)
        {
            msg.rotation = new Vector4(currentRot.x, currentRot.y, currentRot.z, currentRot.w);
            _lastSentRotation = currentRot;
        }
        else
        {
            msg.rotation = new Vector4(_lastSentRotation.x, _lastSentRotation.y,
                _lastSentRotation.z, _lastSentRotation.w);
        }

        _poseChannel.Send(JsonUtility.ToJson(msg));
    }

    // ======================
    // Depth Channel
    // ======================
    private void SetupDepthChannel(RTCDataChannel channel)
    {
        channel.OnMessage = bytes =>
        {
        };
    }

    private void SendJson(object obj)
    {
        _ws.SendText(JsonUtility.ToJson(obj));
    }
}