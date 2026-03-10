import os
import traceback
from llm import art_director_concept

def run():
    real_img = "output/demo_source.jpg"
    if not os.path.exists(real_img):
        files = [f for f in os.listdir("output") if f.endswith("source.jpg")]
        if files:
            real_img = os.path.join("output", files[0])
            
    watch_info = {
        "selected_watch": "Test Watch",
        "watch_description": "A luxury timepiece",
        "search_query": "luxury watch"
    }
    
    try:
        print("Running art_director_concept...")
        res = art_director_concept(real_img, watch_info)
        print("Concept Result:", res)
    except Exception as e:
        print("UNCAUGHT EXCEPTION:")
        traceback.print_exc()

if __name__ == "__main__":
    run()
