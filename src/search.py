import os
import sys

# Ensure UTF-8 console output across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import re
import json
import logging
import datetime
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional, Tuple
import requests

try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

# Configure logger
logger = logging.getLogger("VeriTrace.Search")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

PRIORITY_SOCIAL_DOMAINS = [
    "instagram.com",
    "x.com",
    "twitter.com",
    "facebook.com",
    "linkedin.com",
    "reddit.com",
    "pinterest.com",
    "tumblr.com",
    "tiktok.com",
    "threads.net",
    "youtube.com",
]


def upload_to_ephemeral_host(image_path: str) -> str:
    # upload image to public temporary host so reverse image engines can fetch it
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Local image not found: {image_path}")

    filename = os.path.basename(image_path)
    logger.info(f"Uploading {filename} to ephemeral host for reverse search...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # Strategy 1: Freeimage.host public upload API (returns direct hotlinkable iili.io image URL)
    try:
        logger.info("Attempting upload to freeimage.host...")
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://freeimage.host/api/1/upload",
                headers=headers,
                data={"key": "6d207e02198a847aa98d0a2a901485a5", "action": "upload", "format": "json"},
                files={"source": (filename, f, "image/jpeg")},
                timeout=25,
            )
        if resp.status_code == 200:
            data = resp.json()
            image_url = data.get("image", {}).get("url")
            if image_url:
                logger.info(f"Ephemeral upload successful (Freeimage): {image_url}")
                return image_url
    except Exception as e:
        logger.warning(f"Freeimage upload failed: {e}")

    # Strategy 2: Litterbox (Catbox ephemeral service, 1 hour retention, no signup needed)
    try:
        logger.info("Attempting upload to Litterbox (catbox.moe)...")
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                headers=headers,
                data={"reqtype": "fileupload", "time": "1h"},
                files={"fileToUpload": (filename, f, "image/jpeg")},
                timeout=20,
            )
        if resp.status_code == 200 and resp.text.startswith("http"):
            url = resp.text.strip()
            logger.info(f"Ephemeral upload successful (Litterbox): {url}")
            return url
    except Exception as e:
        logger.warning(f"Litterbox upload failed: {e}")

    # Strategy 3: Tmpfiles.org fallback
    try:
        logger.info("Attempting upload to tmpfiles.org...")
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                headers=headers,
                files={"file": (filename, f, "image/jpeg")},
                timeout=20,
            )
        if resp.status_code == 200:
            data = resp.json()
            raw_url = data.get("data", {}).get("url")
            if raw_url:
                direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                logger.info(f"Ephemeral upload successful (Tmpfiles): {direct_url}")
                return direct_url
    except Exception as e:
        logger.warning(f"Tmpfiles upload failed: {e}")
        logger.warning(f"Freeimage upload failed: {e}")

    raise RuntimeError("All ephemeral image upload providers failed. Please check internet connection.")


def extract_domain(url: str) -> str:
    """Extract registered domain name from URL (e.g., 'instagram.com')."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def calculate_match_confidence(rank: int, is_social: bool, total_results: int) -> float:
    """
    Derive a confidence score based on result rank and social domain priority.
    """
    # Base rank factor decreases as rank index increases
    rank_penalty = min(rank * 0.07, 0.45)
    base_score = 0.85 - rank_penalty

    if is_social:
        confidence = min(base_score + 0.14, 0.98)
    else:
        confidence = max(min(base_score - 0.10, 0.75), 0.30)

    return round(float(confidence), 2)


def search_reverse_image(
    image_url_or_path: str,
    api_key: Optional[str] = None,
    debug_dir: str = "records/debug",
) -> Dict[str, Any]:
    # query serpapi reverse search and rank results with social domain priority
    key = api_key or os.getenv("SERPAPI_KEY")
    if not key or key == "your_serpapi_api_key_here":
        raise ValueError(
            "SerpApi key is missing! Set SERPAPI_KEY in your .env file. "
            "Get a free 100 search/mo key at https://serpapi.com"
        )

    # If a local file path was provided, upload it to an ephemeral host first
    if os.path.exists(image_url_or_path):
        public_image_url = upload_to_ephemeral_host(image_url_or_path)
    else:
        public_image_url = image_url_or_path

    logger.info(f"Querying SerpApi 'google_reverse_image' with public image URL: {public_image_url}")

    params = {
        "engine": "google_reverse_image",
        "image_url": public_image_url,
        "api_key": key,
    }

    raw_response = None
    try:
        if GoogleSearch is not None:
            search = GoogleSearch(params)
            raw_response = search.get_dict()
        else:
            res = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
            res.raise_for_status()
            raw_response = res.json()
    except Exception as e:
        logger.error(f"SerpApi request failed: {e}")
        raise RuntimeError(f"SerpApi reverse image search call failed: {e}")

    # Check if legacy google_reverse_image returned 0 results or migration error
    has_image_results = bool(raw_response.get("image_results"))
    is_empty_or_notice = ("error" in raw_response and "hasn't returned any results" in str(raw_response["error"]).lower())

    if not has_image_results or is_empty_or_notice:
        logger.info("google_reverse_image returned 0 results; querying Google Lens engine...")
        try:
            lens_params = {
                "engine": "google_lens",
                "url": public_image_url,
                "api_key": key,
            }
            if GoogleSearch is not None:
                lens_resp = GoogleSearch(lens_params).get_dict()
            else:
                l_res = requests.get("https://serpapi.com/search.json", params=lens_params, timeout=30)
                lens_resp = l_res.json()
            if lens_resp.get("visual_matches") or lens_resp.get("image_results"):
                raw_response = lens_resp
                logger.info("Google Lens returned matches!")
        except Exception as lens_err:
            logger.warning(f"Google Lens fallback attempt returned: {lens_err}")

    # Persist raw response for auditability and debugging
    os.makedirs(debug_dir, exist_ok=True)
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    debug_path = os.path.join(debug_dir, f"serpapi_raw_{timestamp_str}.json")
    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump(raw_response, f, indent=2)
    logger.info(f"Logged raw SerpApi response to {debug_path}")

    # Check for SerpApi-level errors
    if "error" in raw_response:
        error_msg = str(raw_response["error"])
        if "hasn't returned any results" in error_msg.lower() or "no results" in error_msg.lower():
            logger.info(f"SerpApi notice: {error_msg} (zero indexed matches found)")
        else:
            logger.error(f"SerpApi returned error message: {error_msg}")
            raise RuntimeError(f"SerpApi error: {error_msg}")

    # Parse candidate matches from response
    candidates: List[Dict[str, Any]] = []

    # 1. Inspect image_results
    image_results = raw_response.get("image_results", [])
    for idx, item in enumerate(image_results):
        link = item.get("link") or item.get("source_url") or ""
        title = item.get("title") or item.get("snippet") or "Untitled Result"
        snippet = item.get("snippet") or item.get("title") or ""
        source = item.get("source") or extract_domain(link)
        domain = extract_domain(link)

        is_social = any(s_domain in domain for s_domain in PRIORITY_SOCIAL_DOMAINS)
        confidence = calculate_match_confidence(idx, is_social, len(image_results))

        candidates.append({
            "rank": idx + 1,
            "url": link,
            "domain": domain,
            "source": source,
            "title": title,
            "snippet": snippet,
            "thumbnail": item.get("thumbnail"),
            "is_social": is_social,
            "confidence": confidence,
            "match_type": "social_media_profile" if is_social else "web_page_index",
        })

    # 2. Inspect visual_matches / inline_images if image_results was empty
    if not candidates:
        visual_matches = raw_response.get("visual_matches", []) or raw_response.get("inline_images", [])
        for idx, item in enumerate(visual_matches):
            link = item.get("link") or item.get("source_url") or ""
            title = item.get("title") or item.get("source") or "Visual Match"
            source = item.get("source") or extract_domain(link)
            domain = extract_domain(link)

            is_social = any(s_domain in domain for s_domain in PRIORITY_SOCIAL_DOMAINS)
            confidence = calculate_match_confidence(idx, is_social, len(visual_matches))

            candidates.append({
                "rank": idx + 1,
                "url": link,
                "domain": domain,
                "source": source,
                "title": title,
                "snippet": item.get("snippet", ""),
                "thumbnail": item.get("thumbnail"),
                "is_social": is_social,
                "confidence": confidence,
                "match_type": "social_media_profile" if is_social else "visual_web_index",
            })

    # Rank candidate list: prioritize social matches, then sort by confidence descending
    ranked_candidates = sorted(
        candidates,
        key=lambda c: (1 if c["is_social"] else 0, c["confidence"]),
        reverse=True,
    )

    if ranked_candidates:
        top_match = ranked_candidates[0]
        logger.info(
            f"Top match found: [{top_match['domain']}] {top_match['url']} "
            f"(Confidence: {top_match['confidence']}, Social: {top_match['is_social']})"
        )
    else:
        logger.warning("SerpApi returned zero image matches for the provided photo.")
        top_match = {
            "rank": 0,
            "url": "https://unknown.unindexed",
            "domain": "unindexed.web",
            "source": "Unindexed Media",
            "title": "No Public Reverse Index Found",
            "snippet": "SerpApi found no public indexed image records for this query.",
            "thumbnail": None,
            "is_social": False,
            "confidence": 0.10,
            "match_type": "no_match_found",
        }

    return {
        "top_match": top_match,
        "candidates": ranked_candidates,
        "total_results": len(candidates),
        "public_image_url": public_image_url,
        "raw_debug_file": debug_path,
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    import sys
    load_dotenv()
    if len(sys.argv) > 1:
        res = search_reverse_image(sys.argv[1])
        print(f"Top Match: {res['top_match']}")
    else:
        print("Usage: python src/search.py <image_path_or_url>")
