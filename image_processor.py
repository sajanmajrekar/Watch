import os
import io
import time as _time
import json as _json
import base64
import httpx
from dotenv import load_dotenv
load_dotenv()
from PIL import Image
import subprocess
from google import genai
from google.genai import types

def _build_img2img_wrapper(azaan_prompt, concept=None):
    """
    Wraps the Azaan concept with the Image-to-Image execution instructions.
    """
    safe_zone = (concept or {}).get('safe_zone_side', 'LEFT')
    
    return (
        f"CRITICAL WATCH VISIBILITY RULES:\n"
        f"- THE ENTIRE WATCH MUST BE 100% VISIBLE FROM TOP TO BOTTOM — DO NOT CROP OR CUT ANY PART OF THE WATCH.\n"
        f"- PRESERVE EVERY DETAIL ON THE WATCH DIAL EXACTLY — logos, text, hands, indices, subdials. The dial must be pixel-perfect.\n"
        f"- The watch must ONLY occupy 25-30% of the vertical height of the image.\n"
        f"- Leave massive empty space above the watch (at least 35% height) and below the watch (at least 35% height).\n\n"
        f"Cinematic macro photography of this EXACT watch. "
        f"{azaan_prompt}\n\n"
        f"Environment Integration:\n"
        f"- The watch in the reference image MUST be placed physically into the scene described above.\n"
        f"- Generate realistic contact shadows beneath the watch based on the lighting direction.\n"
        f"- Ensure the watch's metal and glass realistically reflect the colors and lights of the new environment.\n\n"
        f"Composition Specs:\n"
        f"- 16:9 wide banner background aspect ratio.\n"
        f"- Headline Safe Zone = 40% clean space/gradient on the {safe_zone} side. Keep this area free of distracting details.\n"
        f"- Watch placed prominently but very small in the frame vertically.\n\n"
        f"ABSOLUTE NEGATIVE (CRITICAL):\n"
        f"NO TEXT, NO LETTERS, NO NUMBERS, NO LOGOS, NO WATERMARKS anywhere in the generated image.\n"
        f"Do not alter the branding or text on the watch dial itself, preserve it exactly as in the reference image.\n"
    )

def pad_and_upload_watch_image(source_image_path, target_width=2560, target_height=1440):
    """
    Takes the tightly-cropped watch image, shrinks it to 25% height, places it on a
    16:9 dark canvas with a radial blend to hide white backgrounds, and uploads it.
    """
    try:
        print(f"Padding watch image {source_image_path} for ultra-wide generation...")
        watch_img = Image.open(source_image_path).convert("RGBA")
        
        # We want the watch photo to be at most 25% of the total height to survive the 4:1 crop
        max_watch_height = int(target_height * 0.25)
        scale_factor = max_watch_height / watch_img.height
        new_w = int(watch_img.width * scale_factor)
        
        watch_resized = watch_img.resize((new_w, max_watch_height), Image.Resampling.LANCZOS)
        
        # Calculate bounding box of non-white pixels roughly (if it has a solid white BG)
        # To avoid jarring white squares on the dark canvas, we can create a radial gradient mask
        # over the resized watch image to blend its edges into transparent.
        import numpy as np
        
        # Create radial alpha mask for blending
        w, h = new_w, max_watch_height
        y, x = np.ogrid[:h, :w]
        center_x, center_y = w / 2, h / 2
        # Max radius that fits within the image bounds, slightly padded
        max_radius = min(center_x, center_y) * 1.2
        
        dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        
        # Create a smooth alpha falloff
        alpha_mask = np.clip((max_radius - dist_from_center) / (max_radius * 0.3), 0, 1) * 255
        
        # Apply the mask to the watch image if it doesn't already have transparency
        # First check if the image has a transparent background (e.g., cutout)
        extrema = watch_resized.getextrema()
        if len(extrema) == 4 and extrema[3][0] < 255:
            # It already has transparency, so we don't need the radial mask
            pass 
        else:
            # Replace the alpha channel with our radial mask to soften edges
            mask_img = Image.fromarray(alpha_mask.astype(np.uint8), mode='L')
            watch_resized.putalpha(mask_img)

        # Create a dark 16:9 canvas (hex #1a1a1a) to blend with luxury prompts
        canvas = Image.new("RGBA", (target_width, target_height), color="#1a1a1a")
        
        # Paste the watch in the center
        paste_x = (target_width - new_w) // 2
        paste_y = (target_height - max_watch_height) // 2
        canvas.paste(watch_resized, (paste_x, paste_y), watch_resized)
        
        # Convert to RGB to save as JPG
        final_canvas = canvas.convert("RGB")
        padded_path = source_image_path.replace(".jpg", "_padded.jpg")
        final_canvas.save(padded_path, quality=95)
        
        print(f"Uploading padded image to Catbox.moe...")
        command = [
            "curl", "-s", "--max-time", "30",
            "-F", "reqtype=fileupload",
            "-F", f"fileToUpload=@{padded_path}",
            "https://catbox.moe/user/api.php"
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=45)
        catbox_url = result.stdout.strip()
        
        if catbox_url.startswith("http"):
            print(f"Successfully uploaded padding reference: {catbox_url}")
            return catbox_url
        else:
            print(f"Catbox returned invalid response: '{catbox_url[:100]}'. Skipping KIE engines.")
            return None
    except Exception as e:
        print(f"Error padding and uploading watch image: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_img2img_flux2(prompt, source_image_url, output_path, concept=None):
    """
    Generates image using Flux 2 Pro flex-image-to-image via kie.ai API.
    Uses KIE_FLUX_KEY (separate key for Flux 2 engine).
    Async: createTask → poll recordInfo → download image.
    """
    kie_key = os.environ.get("KIE_FLUX_KEY")
    if not kie_key:
        print("KIE_FLUX_KEY not set, skipping Flux 2 Pro.")
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {kie_key}",
            "Content-Type": "application/json"
        }
        
        full_prompt = _build_img2img_wrapper(prompt, concept)
        
        payload = {
            "model": "flux-2/flex-image-to-image",
            "input": {
                "input_urls": [source_image_url],
                "prompt": full_prompt,
                "aspect_ratio": "16:9",
                "resolution": "2K",
                "image_prompt_weight": 0.99,
                "strength": 0.35
            }
        }
        
        print("Creating Flux 2 Pro img2img task via kie.ai...")
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://api.kie.ai/api/v1/jobs/createTask",
                headers=headers,
                json=payload
            )
            
            if resp.status_code != 200:
                print(f"Flux 2 Pro createTask failed: {resp.status_code} - {resp.text[:200]}")
                return None
            
            result = resp.json()
            if result.get("code") not in [0, 200]:
                print(f"Flux 2 Pro API Error: {result.get('msg', str(result))}")
                return None
            data = result.get("data") or {}
            task_id = data.get("taskId")
            if not task_id:
                return None
            
            print(f"Flux 2 Pro task created: {task_id}. Polling...")
            
            for i in range(30):
                _time.sleep(3)
                poll_resp = client.get(
                    f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}",
                    headers=headers
                )
                
                if poll_resp.status_code != 200:
                    continue
                
                poll_data = poll_resp.json().get("data", {})
                state = poll_data.get("state", "")
                
                if state == "success":
                    result_json_str = poll_data.get("resultJson", "")
                    if result_json_str:
                        result_json = _json.loads(result_json_str) if isinstance(result_json_str, str) else result_json_str
                        image_urls = result_json.get("resultUrls", [])
                        if image_urls:
                            img_resp = client.get(image_urls[0], timeout=30.0)
                            if img_resp.status_code == 200:
                                img = Image.open(io.BytesIO(img_resp.content))
                                img.save(output_path)
                                return output_path
                    return None
                elif state == "failed":
                    print(f"Flux 2 Pro task failed.")
                    return None
            
            print("Flux 2 Pro timed out.")
            return None
    except Exception as e:
        print(f"Flux 2 Pro error: {e}")
        return None

def generate_img2img_nano_banana(prompt, source_image_url, output_path, concept=None):
    """
    Generates image using Nano Banana Pro img2img — PRIMARY engine.
    Uses KIE_API_KEY.
    """
    print("🎯 Nano Banana Pro (PRIMARY) — generating image...")
    kie_key = os.environ.get("KIE_API_KEY")
    if not kie_key:
        print("KIE_API_KEY not set, skipping Nano Banana Pro.")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {kie_key}",
            "Content-Type": "application/json"
        }
        
        full_prompt = _build_img2img_wrapper(prompt, concept)
        
        payload = {
            "model": "nano-banana-2",
            "input": {
                "input_urls": [source_image_url],
                "prompt": full_prompt,
                "aspect_ratio": "16:9",
                "resolution": "2K",
                "image_prompt_weight": 1.0
            }
        }
        
        print("Creating Nano Banana Pro img2img task via kie.ai...")
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://api.kie.ai/api/v1/jobs/createTask",
                headers=headers,
                json=payload
            )
            
            if resp.status_code != 200:
                print(f"Nano Banana Pro createTask failed: {resp.status_code} - {resp.text[:200]}")
                return None
            
            result = resp.json()
            if result.get("code") not in [0, 200]:
                print(f"Nano Banana Pro API Error: {result.get('msg', str(result))}")
                return None
            data = result.get("data") or {}
            task_id = data.get("taskId")
            if not task_id:
                return None
            
            print(f"Nano Banana Pro task created: {task_id}. Polling...")
            
            for i in range(30):
                _time.sleep(3)
                poll_resp = client.get(
                    f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}",
                    headers=headers
                )
                
                if poll_resp.status_code != 200:
                    continue
                
                poll_data = poll_resp.json().get("data", {})
                state = poll_data.get("state", "")
                
                if state == "success":
                    result_json_str = poll_data.get("resultJson", "")
                    if result_json_str:
                        result_json = _json.loads(result_json_str) if isinstance(result_json_str, str) else result_json_str
                        image_urls = result_json.get("resultUrls", [])
                        if image_urls:
                            img_resp = client.get(image_urls[0], timeout=30.0)
                            if img_resp.status_code == 200:
                                img = Image.open(io.BytesIO(img_resp.content))
                                img.save(output_path)
                                return output_path
                    return None
                elif state == "failed":
                    print(f"Nano Banana Pro task failed.")
                    return None
            
            return None
    except Exception as e:
        print(f"Nano Banana Pro error: {e}")
        return None

# Models to try for Gemini image generation (primary → fallback)
GEMINI_IMAGE_MODELS = ['gemini-2.5-flash-image']

def generate_img2img_gemini(prompt, source_image_path, output_path, concept=None):
    """
    Generates image using Gemini's native image generation via REST API.
    Uses the source watch image + Azaan Kale prompt to generate an integrated scene.
    Tries multiple model names for resilience.
    source_image_path should be a local file path.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set, skipping Gemini image generation.")
        return None
    
    try:
        full_prompt = _build_img2img_wrapper(prompt, concept)
        
        print(f"Reading source image from: {source_image_path}")
        with open(source_image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        
        for model_name in GEMINI_IMAGE_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": full_prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": image_b64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"],
                    "imageConfig": {
                        "aspectRatio": "16:9",
                        "imageSize": "2K"
                    }
                }
            }
            
            for attempt in range(2):
                try:
                    print(f"Generating image with Gemini REST API ({model_name}, attempt {attempt+1}/2)...")
                    with httpx.Client(timeout=60.0) as client:
                        response = client.post(url, json=payload)
                        
                        if response.status_code == 200:
                            data = response.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    inline_data = part.get("inlineData", {})
                                    if inline_data and inline_data.get("mimeType", "").startswith("image/"):
                                        img_bytes = base64.b64decode(inline_data.get("data", ""))
                                        img = Image.open(io.BytesIO(img_bytes))
                                        img = img.convert("RGB")
                                        img.save(output_path, quality=95)
                                        print(f"Gemini image saved to {output_path} via {model_name}")
                                        return output_path
                        else:
                            print(f"{model_name} error: {response.text[:200]}")
                except Exception as e:
                    print(f"Gemini {model_name} attempt {attempt+1} failed: {e}")
                    if attempt < 1:
                        _time.sleep(3)
        
        print("All Gemini image generation attempts exhausted.")
        return None
    except Exception as e:
        print(f"Gemini image generation error: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_integrated_image(prompt, source_image_url, output_path="generated_banner.jpg", concept=None, local_source_path=None):
    """
    Tri-engine img2img generation (priority order):
    1. Nano Banana Pro via kie.ai (PRIMARY — uses KIE_API_KEY)
    2. Flux 2 Pro via kie.ai (backup — uses KIE_FLUX_KEY)
    3. Gemini native image generation (last resort — uses GEMINI_API_KEY)
    """
    # 1. Nano Banana Pro (PRIMARY)
    if source_image_url:
        result = generate_img2img_nano_banana(prompt, source_image_url, output_path, concept)
        if result:
            return result
    
    # 2. Flux 2 Pro (BACKUP)
    if source_image_url:
        result = generate_img2img_flux2(prompt, source_image_url, output_path, concept)
        if result:
            return result
    
    # 3. Gemini (LAST RESORT)
    if local_source_path and os.path.exists(local_source_path):
        result = generate_img2img_gemini(prompt, local_source_path, output_path, concept)
        if result:
            return result
    
    print("All img2img generation engines failed.")
    return None

def scale_and_pad(image_path, target_width, target_height, output_path, focus_x_pct=0.5, focus_y_pct=0.5):
    """
    For ultra-wide banners (like 4:1): Because we perfectly sized the watch to be <=25%
    of the 16:9 canvas height BEFORE generating, it easily survives a massive vertical crop!
    Therefore, we NEVER need to pad it with blurred blocks. We just zoom the generated
    image to fill the entire target width, and crop off the top and bottom. 
    """
    try:
        from PIL import ImageFilter
        import numpy as np
        
        # We simply pass it through the normal crop_and_resize algorithm.
        # This will scale width to match the 4:1 aspect width, and vertically crop the center,
        # perfectly framing our miniature watch without ANY synthetic padding!
        return crop_and_resize(image_path, target_width, target_height, output_path, focus_x_pct, focus_y_pct)

    except Exception as e:
        print(f"Error in scale_and_pad (zoom_and_crop): {e}")
        import traceback
        traceback.print_exc()
        return None

def _blend_seams(canvas, paste_x, img_width, canvas_width, canvas_height, img_array):
    """Applies a smooth gradient blend at the seam between the image and padding."""
    import numpy as np
    canvas_array = np.array(canvas)
    blend_width = min(40, img_width // 4)  # 40px gradient or less
    
    # Left seam
    if paste_x > 0 and blend_width > 0:
        for i in range(blend_width):
            alpha = i / blend_width
            x = paste_x + i
            if 0 <= x < canvas_width:
                canvas_array[:, x, :] = (
                    canvas_array[:, x, :] * alpha + 
                    canvas_array[:, max(0, paste_x - 1), :] * (1 - alpha)
                ).astype(np.uint8)
    
    # Right seam
    right_edge = paste_x + img_width
    if right_edge < canvas_width and blend_width > 0:
        for i in range(blend_width):
            alpha = i / blend_width
            x = right_edge - 1 - i
            if 0 <= x < canvas_width:
                canvas_array[:, x, :] = (
                    canvas_array[:, x, :] * alpha + 
                    canvas_array[:, min(canvas_width - 1, right_edge), :] * (1 - alpha)
                ).astype(np.uint8)
    
    canvas.paste(Image.fromarray(canvas_array), (0, 0))

def crop_and_resize(image_path, target_width, target_height, output_path, focus_x_pct=0.5, focus_y_pct=0.5):
    """Crops and resizes an image, centering on the exact X and Y percentages given by Vision AI.
    Used for thumbnail/square crops where vertical cropping is acceptable."""
    try:
        image = Image.open(image_path).convert("RGB")
        target_aspect = target_width / target_height
        image_aspect = image.width / image.height

        if image_aspect > target_aspect:
            # Image is wider than target.
            new_width = int(target_aspect * image.height)
            
            focus_point_x = int(image.width * focus_x_pct)
            left = focus_point_x - (new_width // 2)
            right = left + new_width
            
            if right > image.width:
                right = image.width
                left = image.width - new_width
            if left < 0:
                left = 0
                right = new_width
                
            crop_box = (left, 0, right, image.height)
        else:
            # Image is taller than target
            new_height = int(image.width / target_aspect)
            
            focus_point_y = int(image.height * focus_y_pct)
            top = focus_point_y - (new_height // 2)
            bottom = top + new_height
            
            if bottom > image.height:
                bottom = image.height
                top = image.height - new_height
            if top < 0:
                top = 0
                bottom = new_height
                
            crop_box = (0, top, image.width, bottom)

        cropped_image = image.crop(crop_box)
        final_image = cropped_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        final_image.save(output_path, quality=95)
        return output_path
    except Exception as e:
        print(f"Error cropping: {e}")
        return None
