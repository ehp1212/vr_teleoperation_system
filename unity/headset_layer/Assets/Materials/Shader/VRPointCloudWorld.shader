Shader "Custom/VRPointCloudWorld"
{
    Properties
    {
        [MainTexture] _DepthMap("Depth Map", 2D) = "white" {}
        _ColorMap("Color Map", 2D) = "white" {}
        _PointSize("Point Size", Float) = 0.02
        
        _FocalLengthPx("Focal Length Pixels", Vector) = (0, 0, 0, 0)
        _PrincipalPoint("Principal Point (cx, cy)", Vector) = (0, 0, 0, 0)
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
        
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes 
            { 
                uint vertexID : SV_VertexID; 
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings 
            { 
                float4 positionCS : SV_POSITION; 
                float3 color : TEXCOORD0; 
                float pSize : PSIZE; 
                UNITY_VERTEX_OUTPUT_STEREO
            };

            TEXTURE2D(_DepthMap); SAMPLER(sampler_DepthMap);
            TEXTURE2D(_ColorMap); SAMPLER(sampler_ColorMap);

            float4 _DepthMap_TexelSize; // x: 1/w, y: 1/h, z: w, w: h
            float _PointSize;
            float2 _FocalLengthPx;
            float2 _PrincipalPoint;
            
            float4x4 _LocalToWorld; // C#에서 넘겨준 행렬
            
            Varyings vert(Attributes input)
            {   
                Varyings output;
                
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
                
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
                output.pSize = _PointSize * 10;

                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                return half4(input.color, 1.0);
            }
            ENDHLSL
        }
    }
}