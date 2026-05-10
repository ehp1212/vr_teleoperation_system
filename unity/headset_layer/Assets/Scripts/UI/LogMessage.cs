using System;
using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace UI
{
    public class LogMessage : MonoBehaviour
    {
        [SerializeField] private TMP_Text _tmpText;
        private Image _image;

        private void Start()
        {
            _image = GetComponent<Image>();
        }

        public void SetText(string text)
        {
            _tmpText.text = text;
        }

        public void SetColor(Color targetColor)
        {
            _image ??= GetComponent<Image>();
            _image.color = targetColor;
        }
    }
}
