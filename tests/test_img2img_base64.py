import os
import io
import time as _time
import json as _json
import base64
import httpx

kie_key = os.environ.get("KIE_API_KEY")

real_img = "output/demo_source.jpg"
if not os.path.exists(real_img):
    files = [f for f in os.listdir("output") if f.endswith("source.jpg")]
    real_img = os.path.join("output", files[0])

with open(real_img, "rb") as f:
    b64_image = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "model": "flux-2/flex-image-to-image",
    "input": {
        "input_urls": [b64_image],
        "prompt": "Test prompt",
        "aspect_ratio": "16:9",
        "resolution": "2K"
    }
}

headers = {
    "Authorization": f"Bearer {kie_key}",
    "Content-Type": "application/json"
}
with httpx.Client(timeout=30.0) as client:
    resp = client.post(
        "https://api.kie.ai/api/v1/jobs/createTask",
        headers=headers,
        json=payload
    )
    print("Raw B64:", resp.json())

# also test base64:// prefix
payload["input"]["input_urls"] = ["base64://" + b64_image]
with httpx.Client(timeout=30.0) as client:
    resp = client.post(
        "https://api.kie.ai/api/v1/jobs/createTask",
        headers=headers,
        json=payload
    )
    print("Prefix base64://:", resp.json())

