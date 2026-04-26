using UnityEngine;
using TMPro;

namespace Utils
{
    public struct TelemetryData
    {
        public double recvTs;
        public double renderTs;
        public bool isNewFrame;
    }
    
    public class TelemetryUI : MonoBehaviour
    {
        [SerializeField] private TextMeshProUGUI _text;

        private double _lastRecvTs;
        private double _lastRenderTs;

        private int _frameCount;
        private float _timeAccum;
        private float _fps;

        private double _latencyMs;

        // =========================
        // 외부에서 데이터 받기
        // =========================
        public void UpdateTelemetry(TelemetryData data)
        {
            _lastRecvTs = data.recvTs;
            _lastRenderTs = data.renderTs;

            if (data.isNewFrame)
                _frameCount++;

            // latency 계산
            _latencyMs = (_lastRenderTs - _lastRecvTs) * 1000.0;
        }
        
        // =========================
        // 매 프레임 UI 업데이트
        // =========================
        void Update()
        {
            _timeAccum += Time.deltaTime;

            if (_timeAccum > 1.0f)
            {
                _fps = _frameCount / _timeAccum;

                _frameCount = 0;
                _timeAccum = 0f;
            }

            if (_text != null)
            {
                _text.text =
                    $"Latency: {_latencyMs:F1} ms\n" +
                    $"FPS: {_fps:F1}";
            }
        }
    }
}