using System;
using UnityEngine;

public class PoseMessage
{
    public string type;

    public Vector4 rotation;
    public Vector2 control;
}

public class AnswerMessage
{
    public string type;
    public string sdp;
    public string from;
}

public class IceMessage
{
    public string type;
    public string candidate;
    public string sdpMid;
    public int? sdpMLineIndex;
    public string from;
}

public class RoleMessage
{
    public string role;
}

public class ReadyMessage
{
    public string type;
    public string from;
}

public class Message
{
    public string type;
    public string sdp;

    public string candidate;
    public string sdpMid;
    public int sdpMLineIndex;
}

[Serializable]
public class MapItemData
{
    public string @class;
    public float x;
    public float y;
    public float z;
    public double last_seen;

    public override string ToString()
    {
        return $"[Class] : {@class}, [Position]: {x}, {y}, {z}], [Last Seen: {last_seen}]";
    }
}

[Serializable]
public class MapUpdateMessage
{
    public string type;
    public MapItemData data;
}