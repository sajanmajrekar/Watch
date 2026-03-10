import os
import httpx
from dotenv import load_dotenv
load_dotenv()

def list_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set")
        return
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url)
            if response.status_code == 200:
                models = response.json().get('models', [])
                print("Available Models:")
                for m in models:
                    print(f"- {m['name']} (Supported Actions: {m.get('supportedGenerationMethods', [])})")
            else:
                print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
