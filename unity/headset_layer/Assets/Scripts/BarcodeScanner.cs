using System;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.UI;
using Logger = Utils.Logger;

[Serializable] 
public class BarcodeScanner
{
    public string streamName; 
    public RawImage displayImage;   

    /// <summary>
    /// Callback parameters: (StreamName, FrameID, PythonTimestampMs, LatencyMs)
    /// </summary>
    public Action<string, long, long, long> OnFrameUpdated; 

    private long lastProcessedFrameId = -1;
    private bool isReadingPixels;
    private Logger _logger;

    public void Scan()
    {
        if (displayImage == null || displayImage.texture == null || isReadingPixels) return;

        var gpuTexture = displayImage.texture;
        var width = 128;
        var height = 8;
        
        var startX = 0;
        var startY = gpuTexture.height - height;

        isReadingPixels = true;
        
        var t1 = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() & 0xFFFFFFFF;
        
        AsyncGPUReadback.Request(gpuTexture, 0, startX, width, startY, height, 0, 1, request =>
        {
            isReadingPixels = false;

            if (request.hasError)
            {
                Debug.LogError($"[Sync] failed GPU Readback on {streamName}");
                return;
            }
            var t2 = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() & 0xFFFFFFFF;
            
            var pixels = request.GetData<Color32>();
            long currentFrameId = 0;
            long pythonTimestampMs = 0;

            for (var i = 0; i < 32; i++)
            {
                var x = (i * 4) + 2;

                // Frame ID
                var y_id = 6; 
                var index_id = (y_id * width) + x;
                if (pixels[index_id].r > 128)
                {
                    currentFrameId |= (1L << i);
                }

                // Timestamp
                var y_ts = 2; 
                var index_ts = (y_ts * width) + x;
                if (pixels[index_ts].r > 128)
                {
                    pythonTimestampMs |= (1L << i);
                }
            }
            
            // Skip broken frame
            if (currentFrameId == 4294967295 || currentFrameId == 0) 
                return;
            
            var t3 = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() & 0xFFFFFFFF; 
            
            _logger.Log("recv_request", currentFrameId, t1, streamName, pythonTimestampMs);
            _logger.Log("recv_arrival", currentFrameId, t2, streamName, pythonTimestampMs);
            _logger.Log("recv_decode_done", currentFrameId, t3, streamName, pythonTimestampMs);
            
            if (currentFrameId == lastProcessedFrameId) return;
            lastProcessedFrameId = currentFrameId;

            // ==========================================
            // Network Latency
            // ==========================================
            var unityTimeMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() & 0xFFFFFFFF;
            
            var latencyMs = unityTimeMs - pythonTimestampMs;
            if (latencyMs < 0) latencyMs += 0xFFFFFFFF; 

            // Invoke
            OnFrameUpdated?.Invoke(streamName, currentFrameId, pythonTimestampMs, latencyMs);
        });
    }

    public void SetLogger(Logger logger)
    {
        _logger = logger;
    }
}