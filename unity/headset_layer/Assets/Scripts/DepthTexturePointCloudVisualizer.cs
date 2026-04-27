using UnityEngine;
using UnityEngine.UI;

public class DepthTexturePointCloudVisualizer : MonoBehaviour
{
    [Header("Data Sources")]
    [SerializeField] private RawImage depthSource; 
    [SerializeField] private RawImage colorSource; 
    
    [Header("Rendering")]
    [SerializeField] private Material pcMaterial;
    [SerializeField, Range(0.001f, 0.2f)] private float pointSize = 0.02f;

    private int vertexCount;

    void Update()
    {
        if (depthSource == null || colorSource == null || 
            depthSource.texture == null || colorSource.texture == null) 
            return;

        var w = depthSource.texture.width;
        var h = depthSource.texture.height;
        
        vertexCount = w * h;
        
        var focalLength = 18.14756f;
        var hAperture = 20.955f;
        var vAperture = 15.2908f;

        var fx = (focalLength * w) / hAperture;
        var fy = (focalLength * h) / vAperture;

        var cx = w / 2.0f;
        var cy = h / 2.0f;

        // 4. 셰이더 프로퍼티 전달
        pcMaterial.SetVector("_FocalLengthPx", new Vector2(fx, fy));
        pcMaterial.SetVector("_PrincipalPoint", new Vector2(cx, cy));
        pcMaterial.SetVector("_DepthMap_TexelSize", new Vector4(1f / w, 1f / h, w, h));
        pcMaterial.SetFloat("_PointSize", pointSize);
    
        pcMaterial.SetTexture("_DepthMap", depthSource.texture);
        pcMaterial.SetTexture("_ColorMap", colorSource.texture);
    }

    // 실제 화면에 그리는 시점
    void OnRenderObject()
    {
        if (vertexCount <= 0 || pcMaterial == null) return;
        
        var localToWorldMatrix = transform.localToWorldMatrix;
        pcMaterial.SetMatrix("_LocalToWorld", localToWorldMatrix);
        
        pcMaterial.SetPass(0);
        Graphics.DrawProceduralNow(MeshTopology.Points, vertexCount, 1);
    }
}