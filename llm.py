import os
import json
import base64
import time
import httpx
from dotenv import load_dotenv
load_dotenv()
from google import genai
from pydantic import BaseModel
from google.genai import types

# ─── SCHEMAS ───────────────────────────────────────────────────────────────────

class WatchInfoPayload(BaseModel):
    selected_watch: str
    search_query: str
    watch_description: str

class AzaanKaleConceptPayload(BaseModel):
    creative_direction: str
    visual_treatment: str
    framing_composition: str
    ai_prompt: str
    why_it_works: str

class ReviewPayload(BaseModel):
    review_score: int
    feedback: str
    corrected_prompt: str

class CropCoordinatesPayload(BaseModel):
    x_percent: float
    y_percent: float

# ─── API CLIENTS ───────────────────────────────────────────────────────────────

def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable not set. "
            "Please add it to .env in the project root and restart."
        )
    return genai.Client(api_key=api_key)

# ─── LAYER 1 — AZAAN KALE PERSONA (IMAGE-TO-IMAGE) ─────────────────────────

AZAAN_KALE_PERSONA = """
You are Azaan Kale — an Oscar-winning cinematographer and luxury campaign creative director specializing in watches, jewelry, and premium product key visuals.

Mission
Create world-class luxury blog banner background direction. We are using a direct Image-to-Image AI pipeline. The AI will receive the original watch image and your text prompt, and it will redraw the entire scene with the watch perfectly integrated into the new environment.

Your goal is to design a beautiful, integrated environment where the watch naturally belongs. It should feel like a real $200K luxury photoshoot.

Non-Negotiable Luxury Standards
Designed negative space (headline safe zone) is mandatory.
Premium highlight roll-off: bright areas must fade softly, never clip harshly.
Clean lighting, low noise, high-end photography vibe.
"Luxury" is restraint: use minimal props. A wooden podium, a marble slab, a leather desk pad, or abstract geometric pedestals are all great. Do NOT use messy or cluttered scenes.
THE ENTIRE WATCH MUST ALWAYS BE 100% VISIBLE — from crown to bracelet clasp, top lug to bottom lug. NEVER crop or cut any part of the watch.
The watch MUST occupy AT MOST 30% of the vertical frame height, leaving massive empty padding above and below. This is critical for 4:1 banner cropping.
PRESERVE THE EXACT WATCH DIAL, LOGOS, AND HANDS. Do not allow the AI to hallucinate or misspell the branding.

Output Format
Return 5 sections:
Creative Direction
Visual Treatment
Framing/Composition
Technical AI Prompt (ready-to-copy prompt for an image-to-image generator)
Why it Works (1-2 lines)
"""

def extract_watch_info(blog_text):
    print("Extracting watch info from blog text...")
    client = get_client()

    prompt = (
        "You are an expert horologist. Read the following blog post text and:\n"
        "1. Identify all the watch models mentioned in the text.\n"
        "2. Pick ONE standout watch to be the hero of a blog banner.\n"
        "3. Provide a 'search_query' that can be used to find a high-quality, front-facing, isolated image of this specific watch model online.\n"
        "4. Provide a 'watch_description' summarizing what this watch is famous for and its general aesthetic.\n\n"
        "Blog text:\n" + blog_text[:15000]
    )

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=WatchInfoPayload,
                    temperature=0.7,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"AI extraction attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                time.sleep((attempt + 1) * 2)
    return None


def art_director_concept(watch_image_path, watch_info):
    print("Azaan Kale — crafting image-to-image luxury concept...")

    client = get_client()

    try:
        with open(watch_image_path, "rb") as f:
            image_bytes = f.read()

        watch_desc = watch_info.get('watch_description', '')

        prompt_text = AZAAN_KALE_PERSONA + """

You are Azaan Kale. Create a luxury 16:9 blog banner concept for an Image-to-Image AI generation pipeline. 

Inputs:
Watch Summary: """ + watch_desc + """
Watch Image: attached.

Task:
Design a realistic, highly integrated physical environment for this watch. The AI will use the attached image as an init_image and redraw the scene based on your prompt.

Environment Ideas (You can choose):
- Wooden podium or carved stone pedestal
- Leather desk pad with a premium pen or folio
- Minimalist marble slab or frosted glass tabletop
- Vibrant abstract environments if they match the watch's vibe, but they must have a physical surface the watch can cast shadow on.

Composition Requirements
Aspect ratio: 16:9
1. Analyze the attached reference image. Determine if the watch is currently positioned more on the LEFT, RIGHT, or CENTER.
2. The watch MUST remain exactly in that same position in your prompt. DO NOT move the watch from its original placement, or the image will degrade.
3. Designate the Headline Safe Zone (clean space, low detail) on the OPPOSITE side of the watch. 

Output Requirements
Return the 5-part brief and include ONE final Technical AI Prompt that explicitly contains:
"Cinematic macro shot of this exact same watch resting on..." (describe the surface/environment)
"16:9 banner format"
"Watch positioned on the [LEFT/RIGHT/CENTER], horizontal safe zone on the opposite side." 
"CRITICAL: The watch must only take up 25-30% of the vertical height of the image. Leave massive empty headroom above and below the watch so it can be extreme-cropped into a 4:1 ultra-wide banner."
"THE ENTIRE WATCH MUST BE 100% VISIBLE FROM TOP TO BOTTOM AND LEFT TO RIGHT. DO NOT CROP, CUT, OR CLIP ANY PART OF THE WATCH — including the crown, lugs, bracelet links, and clasp. Show the complete watch with generous space around it."
"NO TEXT, NO LOGOS, NO WATERMARKS in the background."
"MAINTAIN 100% PERFECT ACCURACY ON THE WATCH DIAL, KEEPING ALL LOGOS, TEXT, HANDS, AND MARKERS EXACTLY AS IN THE REFERENCE IMAGE."
"""

        # Try gemini-2.5-pro first, fallback to gemini-2.5-flash
        models_to_try = ['gemini-2.5-pro', 'gemini-2.5-flash']
        
        for model_name in models_to_try:
            for attempt in range(2):
                try:
                    print(f"Trying {model_name} (attempt {attempt+1}/2)...")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), prompt_text],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=AzaanKaleConceptPayload,
                            temperature=0.7,
                        ),
                    )
                    print(f"Azaan Kale concept generated via {model_name}.")
                    return json.loads(response.text)
                except Exception as e:
                    print(f"{model_name} attempt {attempt+1} failed: {e}")
                    if attempt < 1:
                        time.sleep(3)
        
        print("All concept generation attempts exhausted.")
        return None
    except Exception as e:
        print("Error during Art Director concepting: " + str(e))
        return None


def art_director_review(composite_image_path, concept_payload):
    print("Azaan Kale — reviewing newly generated image...")

    client = get_client()

    try:
        with open(composite_image_path, "rb") as f:
            image_bytes = f.read()

        cd = concept_payload.get('creative_direction', '')
        prev_prompt = concept_payload.get('ai_prompt', '')

        prompt_text = AZAAN_KALE_PERSONA + """

Azaan, here is the final image-to-image banner generated based on your concept:
Creative Direction: """ + cd + """
Previous prompt used: """ + prev_prompt + """

Look at the image. Did the AI execute your vision?
1. Score 1-10 on luxury integration. Does the watch look like it physically belongs in the scene with realistic shadows and lighting? Is the dial text readable or at least decently preserved without massive hallucination?
2. If score < 9, output a corrected prompt that fixes the top issues (e.g. "make the lighting match the watch better", "fix the chaotic background").
"""

        # Try gemini-2.5-pro first, fallback to gemini-2.5-flash
        models_to_try = ['gemini-2.5-pro', 'gemini-2.5-flash']
        
        for model_name in models_to_try:
            for attempt in range(2):
                try:
                    print(f"Review: Trying {model_name} (attempt {attempt+1}/2)...")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), prompt_text],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ReviewPayload,
                            temperature=0.7,
                        ),
                    )
                    result = json.loads(response.text)
                    print(f"Azaan Kale review via {model_name}: {result.get('review_score', '?')}/10")
                    return result
                except Exception as e:
                    print(f"Review {model_name} attempt {attempt+1} failed: {e}")
                    if attempt < 1:
                        time.sleep(3)
        
        print("All review attempts exhausted.")
        return None
    except Exception as e:
        print(f"Error during Art Director review: {e}")
        return None

def get_smart_crop_center(image_path):
    print("Gemini Flash — visually analyzing output for perfect mobile cropping coordinates...")
    client = get_client()
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        prompt_text = "Analyze this image and find the main watch. Return the exact center coordinates of the watch face as percentages (x_percent, y_percent) between 0.0 and 1.0, where 0,0 is top-left and 1.0,1.0 is bottom-right."

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), prompt_text],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CropCoordinatesPayload,
                temperature=0.0,
            ),
        )
        
        result = json.loads(response.text)
        x_pct = result.get('x_percent', 0.5)
        y_pct = result.get('y_percent', 0.5)
        print(f"Smart Crop center detected at: X={x_pct}, Y={y_pct}")
        return x_pct, y_pct
    except Exception as e:
        print("Error during smart crop analysis: " + str(e))
        return 0.5, 0.5
