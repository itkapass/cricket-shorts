"""
pixabay_visuals.py — a second free real-media source, tried after Pexels
and Wikimedia have both come up empty for a scene.
==============================================================================

WHY A THIRD SOURCE
Pexels and Wikimedia cover most scenes between them (generic sports b-roll
from Pexels, named real-world subjects from Wikimedia), but neither is
exhaustive. Pixabay's free API adds a second large stock library — photos
AND video — as one more real-media attempt before this pipeline gives up
and falls to an AI-generated image. More real footage tried before
synthetic footage is generated is a straightforward quality win, at zero
extra cost.

FREE TIER
Pixabay's API is free for any use with attribution-not-required content,
needs only a free account + API key (pixabay.com/api/docs — sign up, copy
the key, no card), and its documented rate limit is a generous 100 requests
per 60 seconds, 5,000/day — far more than this pipeline will ever need for
a handful of scenes per video.

Silent no-op if PIXABAY_API_KEY is not set, matching every other optional
provider in this project (Groq, Hugging Face, etc.) — nothing breaks for
someone who skips this key, Pexels/Wikimedia/the gradient fallback still
work exactly as before.
"""
import os
import requests

from engine.config import get
from engine.visual_kenburns import image_to_clip

PIXABAY_VIDEO_API = "https://pixabay.com/api/videos/"
PIXABAY_PHOTO_API = "https://pixabay.com/api/"
TIMEOUT_SECONDS = 20


def available() -> bool:
    return bool(get("PIXABAY_API_KEY"))


def fetch_for_scene(query: str, duration_needed: float, job_id: str,
                    scene_number: int, output_dir: str,
                    exclude_ids: set = None) -> dict | None:
    """Tries a Pixabay VIDEO first (same look-and-feel as the Pexels path),
    then a Pixabay PHOTO turned into a Ken-Burns clip. Returns None if
    Pixabay has nothing usable either — the caller moves on to an
    AI-generated image next.

    `exclude_ids` — Pixabay hit ids already used by OTHER recent videos (see
    engine/visual_usage.py). Pixabay search is deterministic by relevance, so
    without this the same query always hands back the same top hit; we now
    walk past any excluded id to the next hit instead of always taking the
    first one, and only fall back to reusing the top hit if every candidate
    is excluded.
    """
    api_key = get("PIXABAY_API_KEY")
    if not api_key or not (query or "").strip():
        return None

    os.makedirs(output_dir, exist_ok=True)

    video = _try_video(query, api_key, exclude_ids)
    if video:
        dest = os.path.join(output_dir, f"{job_id}_s{scene_number}_pixabay.mp4")
        try:
            r = requests.get(video["url"], stream=True, timeout=45)
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
            print(f"[pixabay_visuals] ✓ Used Pixabay video for '{query}'")
            return {"clip_path": dest, "source": "pixabay_video",
                    "keyword_used": query, "pexels_video_id": None,
                    "visual_identifier": f"video:{video['id']}"}
        except Exception as e:
            print(f"[pixabay_visuals] ⚠ Video download failed: {e}")

    photo = _try_photo(query, api_key, exclude_ids)
    if photo:
        img_path = os.path.join(output_dir, f"{job_id}_s{scene_number}_pixabay.jpg")
        mp4_path = os.path.join(output_dir, f"{job_id}_s{scene_number}_pixabay_img.mp4")
        try:
            r = requests.get(photo["url"], timeout=30)
            r.raise_for_status()
            with open(img_path, "wb") as f:
                f.write(r.content)
            if image_to_clip(img_path, mp4_path, duration_needed, scene_number=scene_number, motion_seed=2):
                print(f"[pixabay_visuals] ✓ Used Pixabay photo for '{query}'")
                return {"clip_path": mp4_path, "source": "pixabay_photo",
                        "keyword_used": query, "pexels_video_id": None,
                        "visual_identifier": f"photo:{photo['id']}"}
        except Exception as e:
            print(f"[pixabay_visuals] ⚠ Photo fetch failed: {e}")
        finally:
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except OSError:
                    pass

    return None


def _try_video(query: str, api_key: str, exclude_ids: set = None) -> dict | None:
    try:
        resp = requests.get(PIXABAY_VIDEO_API, params={
            "key": api_key, "q": query, "per_page": 6, "safesearch": "true",
        }, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        fallback = None
        for hit in hits:
            files = hit.get("videos", {})
            best = files.get("large") or files.get("medium") or files.get("small")
            if not (best and best.get("url")):
                continue
            result = {"url": best["url"], "id": hit.get("id")}
            if fallback is None:
                fallback = result
            if not exclude_ids or str(hit.get("id")) not in exclude_ids:
                return result
        # Every candidate was already used elsewhere — reuse the top one
        # rather than giving up and falling to a weaker provider.
        return fallback
    except Exception as e:
        print(f"[pixabay_visuals] ⚠ Video search failed: {e}")
    return None


def _try_photo(query: str, api_key: str, exclude_ids: set = None) -> dict | None:
    try:
        resp = requests.get(PIXABAY_PHOTO_API, params={
            "key": api_key, "q": query, "per_page": 6, "safesearch": "true",
            "image_type": "photo", "orientation": "horizontal",
        }, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        fallback = None
        for hit in hits:
            url = hit.get("largeImageURL") or hit.get("webformatURL")
            if not url:
                continue
            result = {"url": url, "id": hit.get("id")}
            if fallback is None:
                fallback = result
            if not exclude_ids or str(hit.get("id")) not in exclude_ids:
                return result
        return fallback
    except Exception as e:
        print(f"[pixabay_visuals] ⚠ Photo search failed: {e}")
    return None
