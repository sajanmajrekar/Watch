import os
import io
import httpx
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

print("Downloading reference image...")
# Ensure Catbox link resolves by adding proper headers or using a different host
headers = {"User-Agent": "Mozilla/5.0"}
try:
    img_resp = httpx.get("https://files.catbox.moe/kixp6y.jpg", timeout=30.0, headers=headers)
    image_bytes = img_resp.content
    print(f"Downloaded {len(image_bytes)} bytes")
except Exception as e:
    print(f"Failed to download reference: {e}")
    exit(1)

print("Sending to Google Nano Banana 2 API...")

full_prompt = "Cinematic macro photography of this EXACT watch. Ensure 100% visibility."

try:
    result = client.models.generate_images(
        model='nano-banana-2',
        prompt=full_prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="16:9",
            person_generation="DONT_ALLOW"
        )
    )
    
    if result and result.generated_images:
        print("SUCCESS! Generated an image.")
    else:
        print("FAILED: No images returned.")
        
except Exception as e:
    print(f"API ERROR: {e}")
