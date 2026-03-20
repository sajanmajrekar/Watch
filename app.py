import os
import sys
import json
from dotenv import load_dotenv
load_dotenv()
import time
from threading import Thread
from queue import Queue
from flask import Flask, request, jsonify, render_template, Response, send_from_directory
from services.scraper import scrape_blog_content
from services.llm import extract_watch_info, art_director_concept, art_director_review
from services.image_search import search_and_download_watch_image
from services.image_processor import generate_integrated_image, crop_and_resize, scale_and_pad

app = Flask(__name__)
OUTPUT_DIR = "/tmp/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Global dictionary to hold job status and message queues
jobs = {}

# In Vercel, serverless functions have short lifetimes and cannot hold
# long-running background threads or in-memory job state.
# For safety, we avoid running the generation pipeline in Vercel.
def running_on_vercel():
    return os.getenv("VERCEL") == "1"

@app.errorhandler(Exception)
def handle_exceptions(e):
    import traceback
    tb = traceback.format_exc()
    print("--- Exception caught in Flask ---")
    print(tb)
    return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

def generate_banner_task(job_id, url):
    q = jobs[job_id]['queue']
    
    def emit(status, data=None):
        q.put({"status": status, "data": data})
        
    try:
        emit("scraping", "Scraping blog post...")
        blog_text = scrape_blog_content(url)
        if not blog_text:
            emit("error", "Failed to scrape blog content.")
            return
            
        emit("extracting", "AI is analyzing text to find watches...")
        watch_info = extract_watch_info(blog_text)
        if not watch_info:
            emit("error", "AI failed to extract watch info.")
            return

        if watch_info.get("error"):
            details = watch_info.get("details")
            emit("error", f"{watch_info.get('error')}. {details}" if details else watch_info.get("error"))
            return

        emit("sourcing", f"Sourcing image for {watch_info.get('selected_watch')}...")
        sourced_image_path, sourced_image_url = search_and_download_watch_image(
            watch_info.get('search_query'),
            output_filename=os.path.join(OUTPUT_DIR, f"{job_id}_source.jpg"),
            source_page_url=url,
        )
        if not sourced_image_path or not sourced_image_url:
            emit("error", "Failed to source watch image.")
            return

        emit("concepting", "Master Azaan Kale is establishing the creative direction...")
        concept = art_director_concept(sourced_image_path, watch_info)
        if not concept:
            emit("error", "Art Director failed to create a concept.")
            return
            

        from services.image_processor import generate_integrated_image, crop_and_resize, pad_and_upload_watch_image

        emit("compositing", "Pre-processing watch image for Ultra-Wide generation layout...")
        padded_watch_url = pad_and_upload_watch_image(sourced_image_path)
        if not padded_watch_url:
            emit("compositing", "Public upload failed. Falling back to local Gemini generation only.")

        # ─── QC RETRY LOOP (up to 3 attempts) ─────────────────────────────
        MAX_ATTEMPTS = 3
        best_score = 0
        best_attempt = None
        current_prompt = concept.get('ai_prompt')
        attempt_failures = []
        
        for attempt in range(1, MAX_ATTEMPTS + 1):
            emit("processing", f"Image-to-Image Engine: Generating integrated environment (Take {attempt}/{MAX_ATTEMPTS})...")
            
            raw_generated_path = os.path.join(OUTPUT_DIR, f"{job_id}_raw_t{attempt}.jpg")
            generated_img = generate_integrated_image(current_prompt, padded_watch_url, output_path=raw_generated_path, concept=concept, local_source_path=sourced_image_path)
            
            if not generated_img:
                attempt_failures.append(f"Take {attempt}: image generation failed")
                emit("processing", f"Take {attempt} failed to generate. Retrying...")
                continue

            emit("processing", f"Formatting image for blog layout (Take {attempt})...")
            
            from services.llm import get_smart_crop_center
            emit("processing", "Gemini Flash is locating watch coordinates for perfect mobile crop...")
            focus_x_pct, focus_y_pct = get_smart_crop_center(generated_img)
            
            s1 = scale_and_pad(generated_img, 4877, 1214, os.path.join(OUTPUT_DIR, f"{job_id}_4877x1214_t{attempt}.jpg"), focus_x_pct=focus_x_pct, focus_y_pct=focus_y_pct)
            s2 = crop_and_resize(generated_img, 600, 548, os.path.join(OUTPUT_DIR, f"{job_id}_600x548_t{attempt}.jpg"), focus_x_pct=focus_x_pct, focus_y_pct=focus_y_pct)
            
            if not s1 or not s2:
                attempt_failures.append(f"Take {attempt}: post-processing/cropping failed")
                continue

            if not best_attempt:
                best_attempt = {
                    "s1": s1, "s2": s2,
                    "score": 0, "feedback": "Generated successfully, but AI review was unavailable."
                }

            emit("reviewing", f"Azaan Kale is QC'ing Take {attempt}...")
            review = art_director_review(s1, concept)
            
            if not review:
                attempt_failures.append(f"Take {attempt}: art director review returned no result")
                emit("reviewing", f"Take {attempt}: review unavailable. Keeping generated image as fallback.")
                continue

            if review.get("error"):
                attempt_failures.append(f"Take {attempt}: {review.get('error')} - {review.get('details', 'no details')}")
                emit("reviewing", f"Take {attempt}: review failed. Keeping generated image as fallback.")
                continue
            
            score = review.get('review_score', 0)
            feedback = review.get('feedback', '')
            emit("reviewing", f"Take {attempt}: Azaan scored it {score}/10 — \"{feedback[:80]}...\"")
            
            if score >= best_score:
                best_score = score
                best_attempt = {
                    "s1": s1, "s2": s2,
                    "score": score, "feedback": feedback
                }
            
            # If 9+ we're happy, stop retrying
            if score >= 9:
                break
            
            # Otherwise, use the dynamically corrected prompt from Azaan's review
            current_prompt = review.get('corrected_prompt', concept.get('ai_prompt') + f". Fix: {feedback}")
        
        if not best_attempt:
            details = " | ".join(attempt_failures[-3:]) if attempt_failures else "Unknown failure"
            emit("error", f"All takes failed to produce a usable image. {details}")
            return
        
        # Copy best attempt files to final names
        import shutil
        size1_path = os.path.join(OUTPUT_DIR, f"{job_id}_4877x1214.jpg")
        size2_path = os.path.join(OUTPUT_DIR, f"{job_id}_600x548.jpg")
        shutil.copy2(best_attempt["s1"], size1_path)
        shutil.copy2(best_attempt["s2"], size2_path)

        emit("complete", {
            "image1": f"/output/{job_id}_4877x1214.jpg",
            "image2": f"/output/{job_id}_600x548.jpg",
            "source_image": f"/output/{job_id}_source.jpg",
            "creative_direction": concept.get('creative_direction'),
            "visual_treatment": concept.get('visual_treatment'),
            "framing_composition": concept.get('framing_composition'),
            "ai_prompt": concept.get('ai_prompt'),
            "why_it_works": concept.get('why_it_works'),
            "score": best_attempt["score"],
            "feedback": best_attempt["feedback"],
            "watch_name": watch_info.get('selected_watch'),
            "attempts": attempt
        })

    except Exception as e:
        emit("error", str(e))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    if running_on_vercel():
        return jsonify({
            "error": "Generation is not supported in Vercel serverless functions.",
            "details": "This endpoint requires background processing and file writes, which are not supported in the Vercel serverless environment. Run locally instead."
        }), 501

    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400
        
    job_id = str(int(time.time()))
    jobs[job_id] = {"queue": Queue()}
    
    thread = Thread(target=generate_banner_task, args=(job_id, url))
    thread.start()
    
    return jsonify({"job_id": job_id})

@app.route("/stream/<job_id>")
def stream(job_id):
    if running_on_vercel():
        return jsonify({
            "error": "Streaming not supported in serverless deployment.",
            "details": "Use the local server to stream progress updates." 
        }), 501

    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
        
    def generate_events():
        q = jobs[job_id]['queue']
        while True:
            msg = q.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg["status"] in ["complete", "error"]:
                break
                
    return Response(generate_events(), mimetype="text/event-stream")

@app.route("/output/<filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Watch Banner Generator — Startup Check")
    print("="*50)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    kie_key = os.environ.get("KIE_API_KEY")
    print(f"  GEMINI_API_KEY: {'✅ SET (' + gemini_key[:8] + '...)' if gemini_key else '❌ MISSING — add to .env'}")
    print(f"  KIE_API_KEY:    {'✅ SET (' + kie_key[:8] + '...)' if kie_key else '⚠️  MISSING (optional, Gemini is primary)'}")
    print("="*50 + "\n")
    if not gemini_key:
        print("⚠️  No GEMINI_API_KEY — the pipeline will NOT work.")
        print("   Paste your key into .env and restart.\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
