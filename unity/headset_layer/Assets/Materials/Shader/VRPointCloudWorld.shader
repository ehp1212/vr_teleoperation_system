Shader "Custom/VRPointCloudWorld"
{
    Properties
    {
        [MainTexture] _DepthMap("Depth Map", 2D) = "white" {}
        _ColorMap("Color Map", 2D) = "white" {}
        _PointSize("Point Size", Float) = 0.02
        
        // C#에서 계산해서 넘겨주는 값들
        _FocalLengthPx("Focal Length Pixels", Vector) = (0, 0, 0, 0)
        _PrincipalPoint("Principal Point (cx, cy)", Vector) = (0, 0, 0, 0)
    }

    SubShader
    {
        // URP 환경 설정 및 포인트 크기 제어(PSIZE)를 위한 태그
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
        
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            
            // URP 필수 라이브러리
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes 
            { 
                uint vertexID : SV_VertexID; 
            };

            struct Varyings 
            { 
                float4 positionCS : SV_POSITION; 
                float3 color : TEXCOORD0; 
                float pSize : PSIZE; 
            };

            // 텍스처 및 샘플러 선언 (URP 표준 매크로)
            TEXTURE2D(_DepthMap); SAMPLER(sampler_DepthMap);
            TEXTURE2D(_ColorMap); SAMPLER(sampler_ColorMap);

            // C#에서 넘어오는 변수들
            float4 _DepthMap_TexelSize; // x: 1/w, y: 1/h, z: w, w: h
            float _PointSize;
            float2 _FocalLengthPx;
            float2 _PrincipalPoint;
            
            float4x4 _LocalToWorld; // C#에서 넘겨준 행렬
            
            Varyings vert(Attributes input)
            {   
                Varyings output;
                
                uint width = (uint)_DepthMap_TexelSize.z;
                uint height = (uint)_DepthMap_TexelSize.w;

                uint row = input.vertexID / width;
                uint col = input.vertexID % width;
                
                float2 pixelCoord = float2(col, (height - 1) - row); 
                float2 normalizedUV = pixelCoord * _DepthMap_TexelSize.xy;

                float depth = SAMPLE_TEXTURE2D_LOD(_DepthMap, sampler_DepthMap, normalizedUV, 0).r;

                float x = (pixelCoord.x - _PrincipalPoint.x) * depth / _FocalLengthPx.x;
                float y = (pixelCoord.y - _PrincipalPoint.y) * depth / _FocalLengthPx.y; 
                
                float3 posOS = float3(x, y, depth); 

                float4 posWS = mul(_LocalToWorld, float4(posOS, 1.0));
                output.positionCS = TransformWorldToHClip(posWS.xyz);
                
                output.color = SAMPLE_TEXTURE2D_LOD(_ColorMap, sampler_ColorMap, normalizedUV, 0).rgb;
                output.pSize = _PointSize;

                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                return half4(input.color, 1.0);
            }
            ENDHLSL
        }
    }
}