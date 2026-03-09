import os
from llm import kie_chat
try:
    print("Testing kie_chat...")
    res = kie_chat([{"role": "user", "content": "hello"}])
    print("Success:", res)
except Exception as e:
    print("Exception:", e)
