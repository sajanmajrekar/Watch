import requests
import time
import os

# Headers to avoid being blocked by image CDNs
_DOWNLOAD_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/*,*/*;q=0.8',
    'Referer': 'https://www.google.com/',
}

def search_and_download_watch_image(search_query, output_filename="sourced_watch.jpg"):
    """
    Searches for an image of the watch and downloads the first good result.
    Uses DuckDuckGo with retry logic for rate limits.
    """
    print(f"Searching for watch image: {search_query}")
    
    # Try DuckDuckGo with retries
    for attempt in range(3):
        try:
            from duckduckgo_search import DDGS
            results = DDGS().images(
                keywords=search_query,
                region="wt-wt",
                safesearch="off",
                size="Large",
                color="color",
                type_image="photo",
                layout="Square",
                license_image=None,
                max_results=5
            )
            
            if not results:
                print(f"DuckDuckGo returned no images for: '{search_query}'")
                break

            for i, result in enumerate(results):
                image_url = result.get('image')
                print(f"  Trying image {i+1}/5: {image_url[:80]}...")
                
                try:
                    img_data = requests.get(image_url, headers=_DOWNLOAD_HEADERS, timeout=15).content
                    if len(img_data) < 100:
                        print(f"  Skipping — too small ({len(img_data)} bytes)")
                        continue
                    with open(output_filename, 'wb') as handler:
                        handler.write(img_data)
                    print(f"  ✅ Downloaded {len(img_data):,} bytes → {output_filename}")
                    return output_filename, image_url
                except requests.exceptions.Timeout:
                    print(f"  Skipping — download timed out")
                    continue
                except Exception as e:
                    print(f"  Skipping — download error: {e}")
                    continue
                    
            print("Failed to download any of the found images.")
            return None, None
                
        except Exception as e:
            print(f"DuckDuckGo search attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                wait_time = (attempt + 1) * 3
                print(f"  Retrying in {wait_time}s...")
                time.sleep(wait_time)
            continue
    
    print("All image search attempts exhausted. Try again in a minute or provide a direct image URL.")
    return None, None

