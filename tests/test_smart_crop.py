import os
from llm import get_smart_crop_center
from image_processor import crop_and_resize

def run():
    test_img = "output/test_out.jpg"
    if not os.path.exists(test_img):
        files = [f for f in os.listdir("output") if f.endswith("raw_t1.jpg") or f.endswith("raw_t2.jpg")]
        if files:
            test_img = os.path.join("output", files[-1])
        else:
            print("No generated image found to test crop.")
            return
            
    try:
        print(f"Testing Vision AI smart crop on: {test_img}")
        
        # 1. Get the exact center from Gemini 2.5 Flash
        focus_x_pct, focus_y_pct = get_smart_crop_center(test_img)
        print(f"Gemini Flash says watch is at X: {focus_x_pct * 100}%, Y: {focus_y_pct * 100}%")
        
        # 2. Perform the extreme horizontal crop (4877x1214) to test vertical clipping rules
        out_wide = "output/test_smart_wide_crop.jpg"
        res1 = crop_and_resize(test_img, 4877, 1214, out_wide, focus_x_pct, focus_y_pct)
        print("Wide Crop Result:", res1)
        
        # 3. Perform the mobile crop (600x548)
        out_mobile = "output/test_smart_mobile_crop.jpg"
        res2 = crop_and_resize(test_img, 600, 548, out_mobile, focus_x_pct, focus_y_pct)
        print("Mobile Crop Result:", res2)
        
    except Exception as e:
        print("Error during crop test:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
