import os
import io
import base64
import httpx
from PIL import Image

api_key = os.environ.get("GEMINI_API_KEY")
model = "gemini-2.5-flash-image" # Switching to flash image
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

prompt = "A high fashion cinematic shot of a watch."

# Just a dummy tiny image pixel for testing the multimodal payload
dummy_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

request_body = {
    "contents": [{
        "parts": [
            {"text": prompt},
            {
                "inlineData": {
                    "mimeType": "image/png",
                    "data": dummy_image_b64
                }
            }
        ]
    }],
    "generationConfig": {
        "responseModalities": ["TEXT", "IMAGE"],
        "imageConfig": {
            "aspectRatio": "3:4",
            "imageSize": "1K"
        }
    }
}

try:
    with httpx.Client(timeout=30.0) as client:
        print(f"Sending request to {url}...")
        resp = client.post(url, json=request_body)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
