using System;
using UnityEngine;

namespace Utils
{
    public static class MetadataDecoder
    {
        public static void Decode(Texture2D tex, out int frameId, out double timestamp)
        {
            var pixels = tex.GetPixels32();
            var header = new byte[12];

            for (var i = 0; i < 12; i++)
            {
                header[i] = pixels[i].r;
            }
        
            frameId = BitConverter.ToInt32(header, 0);
            timestamp = BitConverter.ToDouble(header, 4);
        }
    }
}