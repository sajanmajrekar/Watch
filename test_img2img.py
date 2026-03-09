import os
import traceback
from image_processor import generate_integrated_image

def run():
    # create a dummy image
    dummy_img = "dummy.jpg"
    with open(dummy_img, "wb") as f:
        f.write(b"dummy image content")
        
    try:
        res = generate_integrated_image("Cinematic shot of a watch on a wooden table", dummy_img, "test_out.jpg")
        print("Result:", res)
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    run()
