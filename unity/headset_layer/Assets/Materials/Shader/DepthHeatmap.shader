Shader "URP/DepthHeatmap"
{
    Properties
    {
        [MainTexture] _BaseMap("Depth Texture", 2D) = "white" {}
        _MinDepth("Min Depth", Float) = 0.0
        _MaxDepth("Max Depth", Float) = 1.0
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" }

        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS   : POSITION;
                float2 uv           : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS   : SV_POSITION;
                float2 uv           : TEXCOORD0;
            };

            TEXTURE2D(_BaseMap);
            SAMPLER(sampler_BaseMap);

            CBUFFER_START(UnityPerMaterial)
                float _MinDepth;
                float _MaxDepth;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.uv = input.uv;
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                // [1] 현재 픽셀의 뎁스값 샘플링
                float depth = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv).r;
                
                // 만약 데이터가 0~1로 압축되어 들어온다면 실제 거리로 복원 (필요시 주석 해제)
                depth *= 5.0; 

                // [2] 기준 색상 정의 (포트폴리오에 맞게 커스텀 가능)
                half3 colorZero  = half3(1, 0, 0); // 0m: 검정 (가장 가까움, 선택사항)
                half3 colorOne   = half3(1, 0, 0); // 1m: 빨강
                half3 colorThree = half3(0, 0, 1); // 3m: 파랑
                half3 colorFive  = half3(0, 1, 0); // 5m: 녹색 (가장 먼 경계)

                half3 finalColor;

                // [3] 중첩 lerp를 이용한 부드러운 보간 로직

                // 0m ~ 1m (r)
                float t1 = saturate((depth - 0.0) / (1.0 - 0.0));
                finalColor = lerp(colorZero, colorOne, t1);

                // 1m ~ 3m (r -> b)
                float t2 = saturate((depth - 1.0) / (3.0 - 1.0));
                finalColor = lerp(finalColor, colorThree, t2);

                // 3m ~ 5m (b -> g)
                float t3 = saturate((depth - 3.0) / (5.0 - 3.0));
                finalColor = lerp(finalColor, colorFive, t3); 

                // further than 5
                // green 
                return half4(finalColor, 1.0);
            }
            ENDHLSL
        }
    }
}