import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Headers to avoid being blocked by image CDNs
_DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/*,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

_PAGE_HEADERS = {
    "User-Agent": _DOWNLOAD_HEADERS["User-Agent"],
}


def _download_image(image_url, output_filename):
    try:
        response = requests.get(image_url, headers=_DOWNLOAD_HEADERS, timeout=15)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        if "image" not in content_type:
            print(f"  Skipping - not an image response ({content_type or 'unknown content type'})")
            return None, None

        img_data = response.content
        if len(img_data) < 1024:
            print(f"  Skipping - too small ({len(img_data)} bytes)")
            return None, None

        with open(output_filename, "wb") as handler:
            handler.write(img_data)

        print(f"  Downloaded {len(img_data):,} bytes -> {output_filename}")
        return output_filename, image_url
    except requests.exceptions.Timeout:
        print("  Skipping - download timed out")
        return None, None
    except Exception as e:
        print(f"  Skipping - download error: {e}")
        return None, None


def _score_candidate(image_url, alt_text, search_query):
    url_lower = image_url.lower()
    alt_lower = (alt_text or "").lower()
    query_tokens = [token.lower() for token in search_query.split() if len(token) > 2]

    score = 0

    for token in query_tokens:
        if token in url_lower:
            score += 3
        if token in alt_lower:
            score += 4

    bonus_terms = ["watch", "fossil", "dial", "product", "hero", "front"]
    for term in bonus_terms:
        if term in url_lower:
            score += 2
        if term in alt_lower:
            score += 2

    penalty_terms = ["logo", "icon", "avatar", "banner", "facebook", "instagram", "linkedin", "youtube"]
    for term in penalty_terms:
        if term in url_lower:
            score -= 5
        if term in alt_lower:
            score -= 5

    return score


def _download_from_search_results(results, output_filename):
    if not results:
        return None, None

    for i, result in enumerate(results):
        image_url = result.get("image")
        if not image_url:
            continue

        print(f"  Trying image {i+1}: {image_url[:80]}...")
        downloaded_path, downloaded_url = _download_image(image_url, output_filename)
        if downloaded_path:
            return downloaded_path, downloaded_url

    return None, None


def _extract_page_candidates(source_page_url, search_query):
    print(f"Trying on-page image fallback from: {source_page_url}")

    response = requests.get(source_page_url, headers=_PAGE_HEADERS, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    candidates = []
    seen_urls = set()

    for selector, attr in [
        ('meta[property="og:image"]', "content"),
        ('meta[name="twitter:image"]', "content"),
        ('meta[property="og:image:url"]', "content"),
    ]:
        for tag in soup.select(selector):
            image_url = tag.get(attr)
            if not image_url:
                continue
            absolute_url = urljoin(source_page_url, image_url)
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)
            candidates.append(
                {
                    "image": absolute_url,
                    "score": _score_candidate(absolute_url, "", search_query) + 10,
                }
            )

    for img in soup.find_all("img"):
        image_url = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-lazy-src")
            or img.get("data-original")
        )
        if not image_url:
            continue

        absolute_url = urljoin(source_page_url, image_url)
        if absolute_url in seen_urls:
            continue

        alt_text = img.get("alt", "")
        score = _score_candidate(absolute_url, alt_text, search_query)
        if score < 0:
            continue

        seen_urls.add(absolute_url)
        candidates.append({"image": absolute_url, "score": score})

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:10]


def search_and_download_watch_image(search_query, output_filename="sourced_watch.jpg", source_page_url=None):
    """
    Searches for an image of the watch and downloads the first good result.
    Uses DuckDuckGo first, then falls back to images found on the source page.
    """
    print(f"Searching for watch image: {search_query}")

    for attempt in range(3):
        try:
            try:
                from ddgs import DDGS
            except ImportError:
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
                max_results=5,
            )

            downloaded_path, downloaded_url = _download_from_search_results(results, output_filename)
            if downloaded_path:
                return downloaded_path, downloaded_url

            print("DuckDuckGo returned no usable images.")
            break
        except Exception as e:
            print(f"DuckDuckGo search attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                wait_time = (attempt + 1) * 3
                print(f"  Retrying in {wait_time}s...")
                time.sleep(wait_time)

    if source_page_url:
        try:
            page_candidates = _extract_page_candidates(source_page_url, search_query)
            downloaded_path, downloaded_url = _download_from_search_results(page_candidates, output_filename)
            if downloaded_path:
                return downloaded_path, downloaded_url
            print("On-page image fallback found no usable images.")
        except Exception as e:
            print(f"On-page image fallback failed: {e}")

    print("All image search attempts exhausted. Try again in a minute or provide a direct image URL.")
    return None, None
