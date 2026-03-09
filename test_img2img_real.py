import os
import traceback
from image_processor import generate_integrated_image

def run():
    # Use a known public image URL of a watch
    test_url = "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?auto=format&fit=crop&q=80&w=1000&ixlib=rb-4.0.3"
    
    try:
        res = generate_integrated_image("Cinematic macro shot of this exact same watch on a vibrant wooden podium", test_url, "output/test_out.jpg")
        print("Result:", res)
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    run()
