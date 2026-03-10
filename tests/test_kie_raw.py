import os
import httpx

kie_key = os.environ.get("KIE_CHAT_KEY")
payload = {
    "model": "gemini-3-pro",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": False
}
headers = {
    "Authorization": "Bearer " + kie_key,
    "Content-Type": "application/json"
}

with httpx.Client(timeout=120.0) as client:
    try:
        resp = client.post("https://api.kie.ai/gemini-3-pro/v1/chat/completions", headers=headers, json=payload)
        print("STATUS:", resp.status_code)
        print("TEXT:", resp.text)
    except Exception as e:
        print("EXCEPTION:", repr(e))
