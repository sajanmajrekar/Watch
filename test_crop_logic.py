import os
from PIL import Image
from image_processor import crop_and_resize

def run():
    # Use the test img2img output if it exists, otherwise find another generated image
    test_img = "output/test_out.jpg"
    if not os.path.exists(test_img):
        files = [f for f in os.listdir("output") if f.endswith("raw_t1.jpg") or f.endswith("raw_t2.jpg")]
        if files:
            test_img = os.path.join("output", files[-1])
        else:
            print("No generated image found to test crop.")
            return
            
    try:
        print(f"Testing new crop logic on: {test_img}")
        out_path = "output/test_mobile_crop.jpg"
        # 600x548 is the mobile ratio
        res = crop_and_resize(test_img, 600, 548, out_path)
        print("Crop Result:", res)
        
        # Verify it exists
        if os.path.exists(out_path):
            img = Image.open(out_path)
            print(f"Output dimensions: {img.width}x{img.height}")
    except Exception as e:
        print("Error during crop test:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
