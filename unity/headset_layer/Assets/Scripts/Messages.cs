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