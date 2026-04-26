using System;
using System.Collections;
using System.Text;
using NativeWebSocket;
using Unity.WebRTC;
using UnityEngine;
using UnityEngine.UI;
using Utils;

public class WebRTCClient : MonoBehaviour
{
    private const string renderStage = "render";
    private const string recvStage = "recv";
    
    [SerializeField] private string _ipAddress = "172.20.10.8";

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
    
    // Texture reuse
    private Texture2D _rgbTex2D;
    private Texture2D _depthTex2D;

    // frame tracking
    private int _lastRgbFrameId = -1;
    private int _lastDepthFrameId = -1;
    private double _lastRecvTsRgb;
    private bool _newRgbFrame;
    
    private Texture _prevRgbTex;
    private Texture _prevDepthTex;

    private double _lastRecvTsDepth;
    private bool _newDepthFrame;

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
        _timer += Time.deltaTime;
        _ws.DispatchMessageQueue();

        var now = Time.realtimeSinceStartupAsDouble;
        
        /* =========================
         * RECV (frame arrival detect)
         * ========================= */
        if (_rgbImage.texture != null)
        {
            if (_rgbImage.texture != _prevRgbTex)
            {
                _lastRecvTsRgb = now;
                _prevRgbTex = _rgbImage.texture;
                _newRgbFrame = true;

                _logger.Log("recv", 0, _lastRecvTsRgb, "rgb"); // frame_id는 지금 무의미
            }
        }

        if (_depthImage.texture != null)
        {
            if (_depthImage.texture != _prevDepthTex)
            {
                _lastRecvTsDepth = now;
                _prevDepthTex = _depthImage.texture;
                _newDepthFrame = true;

                _logger.Log("recv", 0, _lastRecvTsDepth, "depth");
            }
        }

        /* =========================
         * RENDER
         * ========================= */
        double renderTs = now;

        if (_lastRecvTsRgb > 0)
        {
            _logger.Log("render", 0, renderTs, "rgb");
        }

        if (_lastRecvTsDepth > 0)
        {
            _logger.Log("render", 0, renderTs, "depth");
        }

        /* =========================
         * TELEMETRY
         * ========================= */
        if (_telemetryUI != null && _lastRecvTsRgb > 0)
        {
            var data = new TelemetryData
            {
                recvTs = _lastRecvTsRgb,
                renderTs = renderTs,
                isNewFrame = _newRgbFrame
            };

            _telemetryUI.UpdateTelemetry(data);
            _newRgbFrame = false;
        }

        /* =========================
         * Pose
         * ========================= */
        if (_timer > 0.02f)
        {
            SendPose();
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

        var q = transform.rotation;

        msg.type = "input";
        msg.rotation = new Vector4(q.x, q.y, q.z, q.w);

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
    
    private Texture2D ConvertToTexture2D(Texture tex, ref Texture2D reusable)
    {
        if (reusable == null || reusable.width != tex.width || reusable.height != tex.height)
        {
            reusable = new Texture2D(tex.width, tex.height, TextureFormat.RGBA32, false);
        }

        var rt = RenderTexture.GetTemporary(
            tex.width,
            tex.height,
            0,
            RenderTextureFormat.ARGB32
        );

        Graphics.Blit(tex, rt);

        var prev = RenderTexture.active;
        RenderTexture.active = rt;

        reusable.ReadPixels(new Rect(0, 0, tex.width, tex.height), 0, 0);
        reusable.Apply();

        RenderTexture.active = prev;
        RenderTexture.ReleaseTemporary(rt);

        return reusable;
    }
}