using System;
using UnityEngine;
using UnityEngine.UI;

public class DepthTextureVisualizer : MonoBehaviour
{
    [SerializeField] private WebRTCClient _webRTCClient;
    [SerializeField] private RawImage _depthHeatmapImage;

    private void Awake()
    {
        if (_webRTCClient == null)
            throw new Exception($"WebRTC Client is null");
    }

    private void Update()
    {
        if (_depthHeatmapImage.texture == null)
        {
            _depthHeatmapImage.texture = _webRTCClient.DepthImage;
            _depthHeatmapImage.material.SetTexture("_BaseMap", _webRTCClient.DepthImage);
        }
    }
}
