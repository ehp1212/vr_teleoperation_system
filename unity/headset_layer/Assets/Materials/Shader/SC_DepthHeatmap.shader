Shader "URP/SC_DepthHeatmap"
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
                float depth = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv).r;
                depth *= 5.0; 

                half3 colorZero  = half3(1, 0, 0); 
                half3 colorOne   = half3(1, 0, 0); 
                half3 colorThree = half3(0, 0, 1); 
                half3 colorFive  = half3(0, 1, 0); 

                half3 finalColor;

                // 0m ~ 0.5m (r)
                float t1 = saturate((depth - 0.0) / (0.2 - 0.0));
                finalColor = lerp(colorZero, colorOne, t1);

                // 1m ~ 3m (r -> b)
                float t2 = saturate((depth - 0.2) / (3.0 - 0.2));
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