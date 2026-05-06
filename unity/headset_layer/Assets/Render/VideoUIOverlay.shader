Shader "Custom/VideoUIOverlay"
{
    Properties
    {
        _MainTex ("Video Texture (Background)", 2D) = "white" {}
        _OverlayTex ("UI Overlay Texture (Foreground)", 2D) = "transparent" {}
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            struct appdata_t {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
            };

            struct v2f {
                float2 uv : TEXCOORD0;
                float4 vertex : SV_POSITION;
            };

            sampler2D _MainTex;
            sampler2D _OverlayTex;

            v2f vert (appdata_t v)
            {
                v2f o;
                o.vertex = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv; 
                return o;
            }

            fixed4 frag (v2f i) : SV_Target
            {
                // 1. 영상 픽셀 색상을 가져옵니다.
                fixed4 videoColor = tex2D(_MainTex, i.uv);
                
                // 2. UI 오버레이 픽셀 색상(과 투명도)을 가져옵니다.
                fixed4 overlayColor = tex2D(_OverlayTex, i.uv);
                
                // 3. UI의 알파(투명도) 값을 기준으로 두 색상을 섞습니다(Lerp).
                // 알파가 0이면 영상 표시, 1이면 UI 표시
                fixed3 finalColor = lerp(videoColor.rgb, overlayColor.rgb, overlayColor.a);
                
                return fixed4(finalColor, 1.0);
            }
            ENDCG
        }
    }
}