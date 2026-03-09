import os
import httpx

kie_key = os.environ.get("KIE_API_KEY")
image_url = "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?auto=format&fit=crop&q=80&w=1000&ixlib=rb-4.0.3"

# Testing various fidelity parameters
payload = {
    "model": "flux-2/flex-image-to-image",
    "input": {
        "input_urls": [image_url],
        "prompt": "Test prompt",
        "aspect_ratio": "16:9",
        "resolution": "2K",
        "strength": 0.45, 
        "image_prompt_weight": 0.9
    }
}
headers = {
    "Authorization": f"Bearer {kie_key}",
    "Content-Type": "application/json"
}

with httpx.Client(timeout=30.0) as client:
    resp = client.post("https://api.kie.ai/api/v1/jobs/createTask", headers=headers, json=payload)
    print("RESPONSE:", resp.json())
