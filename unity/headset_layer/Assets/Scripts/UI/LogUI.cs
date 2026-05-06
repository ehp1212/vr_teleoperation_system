using System.Collections;
using System.Collections.Generic;
using UI;
using UnityEngine;
using UnityEngine.Pool;

public class LogUI : MonoBehaviour
{
    [Header("System")]
    [SerializeField] private WebRTCClient _webRTCClient;
    
    [Header("Message Pool")]
    [SerializeField] private Transform _logContainer;
    [SerializeField] private LogMessage _logMessagePrefab;
    [SerializeField] private float _logLifetime = 10f; 

    [Header("Visuals")]
    [SerializeField] private Gradient _logColorGradient; 

    private ObjectPool<LogMessage> _logPool;
    private List<LogMessage> _activeLogs = new List<LogMessage>();

    private void Start()
    {
        _logPool = new ObjectPool<LogMessage>(
            createFunc: () => Instantiate(_logMessagePrefab, _logContainer),
            actionOnGet: (log) => 
            {
                log.gameObject.SetActive(true);
                log.transform.SetAsLastSibling();
            },
            actionOnRelease: (log) => log.gameObject.SetActive(false),
            actionOnDestroy: (log) => Destroy(log.gameObject),
            defaultCapacity: 10,
            maxSize: 50
        );

        _webRTCClient.MapUpdateEvent.AddListener(LogMapUpdate);
    }

    private void LogMapUpdate(MapUpdateMessage data)
    {
        var logger = _logPool.Get();
        _activeLogs.Add(logger);

        var c = data.data.@class;
        var position = new Vector3(data.data.x, data.data.y, data.data.z);
        logger.SetText($"[Added] {c} - ({position})");

        UpdateLogColors();
        StartCoroutine(ReleaseLogRoutine(logger));
    }

    private IEnumerator ReleaseLogRoutine(LogMessage log)
    {
        yield return new WaitForSeconds(_logLifetime);

        if (_activeLogs.Contains(log))
        {
            _activeLogs.Remove(log);
            _logPool.Release(log);
            
            UpdateLogColors(); 
        }
    }

    private void UpdateLogColors()
    {
        if (_activeLogs.Count == 0) return;

        for (int i = 0; i < _activeLogs.Count; i++)
        {
            float t = _activeLogs.Count > 1 ? (float)i / (_activeLogs.Count - 1) : 1f;

            var targetColor = _logColorGradient.Evaluate(t);
            _activeLogs[i].SetColor(targetColor);
        }
    }

    private void OnDestroy()
    {
        if (_webRTCClient != null)
            _webRTCClient.MapUpdateEvent.RemoveListener(LogMapUpdate);
    }
}