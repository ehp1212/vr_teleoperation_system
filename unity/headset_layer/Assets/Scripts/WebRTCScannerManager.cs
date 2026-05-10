using System;
using System.Collections.Generic;
using UnityEngine;

public class WebRTCScannerManager : MonoBehaviour
{
    [SerializeField] private BarcodeScanner[] scanners;
    [SerializeField] private WebRTCClient _webRTCClient;

    private Dictionary<string, long> _latestFrameIds = new();
    
    private long _lastSyncedFrameId = -1;
    private long _lastbridgeTimestamp = -1;

    private void Start()
    {
        foreach (var scanner in scanners)
        {
            _latestFrameIds[scanner.streamName] = -1;
            scanner.SetLogger(_webRTCClient.Logger); 
            scanner.OnFrameUpdated += HandleFrameUpdated;
        }
    }

    private void Update()
    {
        foreach (var scanner in scanners)
        {
            scanner.Scan();
        }
    }

    private void HandleFrameUpdated(string streamName, long frameId, long timestamp, long latency)
    {
        _latestFrameIds[streamName] = frameId;
        
        _webRTCClient.UpdateBarcodeTelemetry(streamName, timestamp);
        CheckSync();
    }

    private void CheckSync()
    {
        long targetFrameId = -1;
        var isSynced = true;

        foreach (var kvp in _latestFrameIds)
        {
            long currentId = kvp.Value;

            if (currentId == -1) 
            {
                return;
            }

            if (targetFrameId == -1)
            {
                targetFrameId = currentId;
            }
            
            else if (targetFrameId != currentId)
            {
                isSynced = false;
                break;
            }
        }

        if (isSynced && targetFrameId > _lastSyncedFrameId)
        {
            _lastSyncedFrameId = targetFrameId;
            
            // Log frame received
            var t4 = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() & 0xFFFFFFFF;
            _webRTCClient.FrameSyncLog("recv_sync_done", targetFrameId, t4, "manager");
        }
    }

    private void OnDestroy()
    {
        foreach (var scanner in scanners)
        {
            scanner.OnFrameUpdated -= HandleFrameUpdated;
        }
    }
}