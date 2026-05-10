using System;
using System.IO;
using UnityEngine;

namespace Utils
{
    /*
     * [Unity Pipeline Profiling Definitions]
     * -----------------------------------------------------------------------------
     * T0 (Python Side) : Birth time of the frame (embedded in barcode).
     * * T1 (recv_request)    : Requesting pixel data from GPU texture (AsyncGPUReadback).
     * Identifies the exact moment Unity's rendering engine
     * received the WebRTC frame.
     * * T2 (recv_arrival)    : GPU-to-CPU memory transfer (DMA) completed.
     * Measures the hardware/driver overhead of data moving to CPU.
     * * T3 (recv_decode_done): Barcode scanning & FrameID/T0 recovery finished.
     * Measures the computational cost of the decoding logic.
     * * T4 (recv_sync_done)  : All required streams (RGB/Depth) matched at the Sync Barrier.
     * Identifies "waiting time" caused by network jitter or
     * unbalanced stream delivery.
     * -----------------------------------------------------------------------------
     */
    public class Logger
    {
        private StreamWriter _writer;
        private long _sessionId;
    
        public  Logger(string fileName = "unity_log.json1")
        {
            _sessionId = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            _writer = new StreamWriter(fileName, false);
        }

        public void Log(string stage, long frameId, long unityTime, string stream, long bridge_ts)
        {
            var json = JsonUtility.ToJson(new LogEntry
            {
                session = _sessionId,
                stage = stage,
                frame_id = frameId,
                unityTime = unityTime,
                stream = stream,
                bridgeTime = bridge_ts
            });
        
            _writer.WriteLine(json);
            _writer.Flush();
        }
    }

    public class LogEntry
    {
        public long session;
        public string stage;
        public long frame_id;
        
        /// <summary>
        /// Unity Timestamp
        /// </summary>
        public long unityTime; 
        public string stream;

        /// <summary>
        /// Bridge Timestamp 
        /// </summary>
        public long bridgeTime;
    }
}