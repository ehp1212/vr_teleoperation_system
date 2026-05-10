using System.Collections.Generic;
using UnityEngine;

public class TextureSwitcher : MonoBehaviour
{
    public int CurrentIndex;
    
    public List<Transform> Textures;

    private float _timer;
    
    // Update is called once per frame
    void Update()
    {
        _timer += Time.deltaTime;
        if (_timer > 5f)
        {
            foreach (var texture in Textures)
            {
                texture.gameObject.SetActive(false);
            }
            
            CurrentIndex++;
            if (CurrentIndex >= Textures.Count)
                CurrentIndex = 0;
            
            Textures[CurrentIndex].gameObject.SetActive(true);
            _timer = 0f;
        }
    }
}
