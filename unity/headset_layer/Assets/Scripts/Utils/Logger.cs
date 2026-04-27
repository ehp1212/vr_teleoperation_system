using System;
using System.IO;
using UnityEngine;

namespace Utils
{
    public class Logger
    {
        private StreamWriter _writer;
        private long _sessionId;
    
        public  Logger(string fileName = "unity_log.json1")
        {
            _sessionId = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            _writer = new StreamWriter(fileName, false);
        }

        public void Log(string stage, int frameId, double ts, string stream)
        {
            var json = JsonUtility.ToJson(new LogEntry
            {
                session = _sessionId,
                stage = stage,
                frame_id = frameId,
                ts = ts,
                stream = stream
            });
        
            _writer.WriteLine(json);
            _writer.Flush();
        }
    }

    public class LogEntry
    {
        public long session;
        public string stage;
        public int frame_id;
        public double ts;
        public string stream;
    }
}