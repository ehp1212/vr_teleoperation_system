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
            
            // [추가됨] VR Single Pass Instancing 지원을 위한 선언
            #pragma multi_compile_instancing

            #include "UnityCG.cginc"

            struct appdata_t {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
                
                // [추가됨] 버텍스 입력에 인스턴스 ID 추가
                UNITY_VERTEX_INPUT_INSTANCE_ID 
            };

            struct v2f {
                float2 uv : TEXCOORD0;
                float4 vertex : SV_POSITION;
                
                // [추가됨] 버텍스 출력에 양안(Stereo) 정보 추가
                UNITY_VERTEX_OUTPUT_STEREO 
            };

            sampler2D _MainTex;
            sampler2D _OverlayTex;

            v2f vert (appdata_t v)
            {
                v2f o;
                
                // [추가됨] 인스턴스 ID 초기화 (양쪽 눈 그리기 준비)
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                o.vertex = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv; 
                return o;
            }

            fixed4 frag (v2f i) : SV_Target
            {
                // [추가됨] 프래그먼트 쉐이더에서도 스테레오 아이 인덱스 설정 (선택적이지만 안전함을 위해 추가)
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);

                // 1. 영상 픽셀 색상을 가져옵니다.
                fixed4 videoColor = tex2D(_MainTex, i.uv);
                
                // 2. UI 오버레이 픽셀 색상(과 투명도)을 가져옵니다.
                fixed4 overlayColor = tex2D(_OverlayTex, i.uv);
                
                // 3. UI의 알파(투명도) 값을 기준으로 두 색상을 섞습니다(Lerp).
                fixed3 finalColor = lerp(videoColor.rgb, overlayColor.rgb, overlayColor.a);
                
                return fixed4(finalColor, 1.0);
            }
            ENDCG
        }
    }
}