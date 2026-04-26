using UnityEngine;
using TMPro;

namespace Utils
{
    public struct TelemetryData
    {
        public double renderTs;
        public double latencyMs;
        public double frameGapMs;
        public bool isNewFrame;
    }
    
    public class TelemetryUI : MonoBehaviour
    {
        [SerializeField] private TextMeshProUGUI _text;
        [SerializeField] private float _uiUpdateInterval = 0.2f;

        private int _frameCount;
        private float _fpsTimeAccum;
        private float _uiTimeAccum;
        private float _fps;
        
        private double _currentLatency;
        private double _currentFrameGap;

        public void UpdateTelemetry(TelemetryData data)
        {
            if (data.isNewFrame)
            {
                _frameCount++;
                _currentLatency = data.latencyMs;
                _currentFrameGap = data.frameGapMs;
            }
        }

        void Update()
        {
            var deltaTime = Time.deltaTime;
            _fpsTimeAccum += deltaTime;
            _uiTimeAccum += deltaTime;

            if (_fpsTimeAccum >= 1.0f)
            {
                _fps = _frameCount / _fpsTimeAccum;
                _frameCount = 0;
                _fpsTimeAccum = 0f;
            }

            if (_uiTimeAccum >= _uiUpdateInterval)
            {
                UpdateUIText();
                _uiTimeAccum = 0f;
            }
        }

        private void UpdateUIText()
        {
            if (_text == null) return;

            var latencyColor = _currentLatency > 150 ? "red" : "white";
            var gapColor = _currentFrameGap > 50 ? "yellow" : "white";

            _text.text = 
                $"<b>Rendering FPS:</b> {_fps:F1}\n" +
                $"<b>Display Latency:</b> <color={latencyColor}>{_currentLatency:F1} ms</color>\n" +
                $"<b>Frame Gap:</b> <color={gapColor}>{_currentFrameGap:F1} ms</color>";
        }
    }
}