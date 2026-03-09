import os
import traceback
from llm import art_director_concept

def run():
    # create a dummy image
    dummy_img = "dummy.jpg"
    with open(dummy_img, "wb") as f:
        f.write(b"dummy image content")
        
    watch_info = {
        "selected_watch": "Rolex Submariner",
        "watch_description": "A classic dive watch",
        "search_query": "Rolex Submariner"
    }
    
    try:
        res = art_director_concept(dummy_img, watch_info)
        print("Result:", res)
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    run()
