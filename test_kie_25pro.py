import os
import httpx

kie_key = os.environ.get("KIE_CHAT_KEY")
image_url = "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?auto=format&fit=crop&q=80&w=1000&ixlib=rb-4.0.3"

payload = {
    "model": "gemini-2.5-pro",
    "messages": [
        {
            "role": "user", 
            "content": [
                {"type": "text", "text": "What is in this image? Just give one sentence."},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }
    ],
    "stream": False
}
headers = {
    "Authorization": "Bearer " + kie_key,
    "Content-Type": "application/json"
}

print("Testing gemini-2.5-pro on kie.ai...")
with httpx.Client(timeout=30.0) as client:
    try:
        resp = client.post("https://api.kie.ai/v1/chat/completions", headers=headers, json=payload)
        print("STATUS:", resp.status_code)
        print("TEXT:", resp.text)
    except Exception as e:
        print("EXCEPTION:", repr(e))
