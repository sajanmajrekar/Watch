import os
import io
import time
from PIL import Image
from dotenv import load_dotenv
import httpx
import base64

load_dotenv()

kie_key = os.environ.get("KIE_API_KEY")

headers = {
    "Authorization": f"Bearer {kie_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "nano-banana-2",
    "input": {
        "input_urls": ["https://files.catbox.moe/kixp6y.jpg"], # sample
        "prompt": "Cinematic macro photography of this EXACT watch. Ensure 100% visibility.",
        "aspect_ratio": "16:9",
        "resolution": "2K",
        "image_prompt_weight": 1.0, # testing weight
    }
}

resp = httpx.post(
    "https://api.kie.ai/api/v1/jobs/createTask",
    headers=headers,
    json=payload
)

print("Task created:", resp.json())
task_id = resp.json().get("data", {}).get("taskId")

if task_id:
    print(f"Polling {task_id}...")
    for i in range(20):
        time.sleep(3)
        poll_resp = httpx.get(
            f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}",
            headers=headers
        )
        data = poll_resp.json().get("data", {})
        state = data.get("state")
        print(f"State: {state}")
        if state == "success":
            print(data.get("resultJson"))
            break
        elif state == "failed":
            print("Failed")
            break
