"""
visual_fetcher.py
-----------------
MODULE 3 — Background Video & B-Roll Fetcher

Fetches HD stock footage from Pexels API (free, no cost) for each scene.
Each scene gets its OWN clip based on its unique visual_keyword.
This guarantees visual variety and prevents the "repetitive stock footage" YPP rejection.

To swap providers: Replace pexels_ functions with Pixabay, Coverr, or a custom generator.
The output contract (list of local video file paths) stays the same.
"""

import os
import json
import random
import hashlib
import requests
from pathlib import Path
from engine.config import require, get

# ─── Constants ────────────────────────────────────────────────────────────────

PEXELS_VIDEO_API = "https://api.pexels.com/videos/search"

# YouTube Shorts is 9:16 vertical. We prefer landscape source clips (1920x1080)
# and will rotate/crop them in the compositor. Avoid vertical clips (they crop badly).
PREFERRED_MIN_WIDTH  = 1920
PREFERRED_MIN_HEIGHT = 1080
PREFERRED_ORIENTATION = "landscape"  # Pexels filter

# Fallback: If no good clip found, use a clean tech-themed gradient animation
# (rendered in video_compositor.py) instead of a blank screen
FALLBACK_CLIP_TYPE = "gradient_animation"

# Cache folder: avoid re-downloading the same clip for the same keyword
CLIP_CACHE_DIR = os.path.join(get("OUTPUT_DIR", "output"), "clip_cache")


# ─── Core Functions ────────────────────────────────────────────────────────────

def fetch_clip_for_scene(
    visual_keyword: str,
    duration_needed: float,
    job_id: str = "job",
    scene_number: int = 1,
    exclude_video_ids: set = None,
    scene_text: str = "",
    cross_video_exclude_ids: set = None,
) -> dict:
    """
    Fetches the best matching video clip for a scene's visual keyword.

    Args:
        visual_keyword: Pexels search term (e.g., "silicon wafer semiconductor cleanroom")
        duration_needed: How many seconds this scene needs (clip will be looped if shorter)
        job_id:         Unique job identifier for file naming
        scene_number:   Scene index (for logging)
        exclude_video_ids: Pexels video IDs already used elsewhere in THIS video — skipped
            even if they're the top match again. FIXED: two different (but similarly-worded)
            scenes could each independently search for something like "safety goggles
            engineer" and "protective goggles water testing" — different cache keys, same
            underlying Pexels video, so the old exact-keyword-text dedup never caught it.
            The same unrelated stock clip of a person in goggles showed up twice in one
            real generated video for exactly this reason. This checks the actual video ID
            Pexels assigns, not the search text used to find it.
        cross_video_exclude_ids: Pexels video IDs already used in OTHER recent videos
            (see engine/visual_usage.py). This fixes the other half of the "repeated
            England clip" bug that lived in THIS file: the on-disk cache below is keyed
            only by the exact keyword text, so two different videos whose scripts
            happened to produce the same (or a near-identical) search phrase got served
            the exact same cached .mp4, forever, with no way to tell. A small sidecar
            .json next to each cached clip now remembers which Pexels video ID it
            actually is, so a cache hit on this exclusion list is treated as a miss and a
            fresh search runs instead, exactly as if nothing had been cached for this
            keyword.

    Returns:
        {
            "clip_path": "/path/to/downloaded.mp4",
            "source": "pexels" | "cache" | "fallback",
            "duration": 15.3,
            "keyword_used": "silicon wafer semiconductor cleanroom",
            "pexels_video_id": 1234567 | None,
            "visual_identifier": "1234567" | None,   # for cross-video dedup bookkeeping
        }
    """
    cfg = require(["PEXELS_API_KEY"])
    os.makedirs(CLIP_CACHE_DIR, exist_ok=True)
    exclude_video_ids = exclude_video_ids or set()
    cross_video_exclude_ids = cross_video_exclude_ids or set()
    all_exclude_ids = exclude_video_ids | cross_video_exclude_ids

    # Check cache first (hash the keyword to get a stable filename).
    cache_key = hashlib.md5(visual_keyword.encode()).hexdigest()[:12]
    cached_path = os.path.join(CLIP_CACHE_DIR, f"{cache_key}.mp4")
    meta_path = os.path.join(CLIP_CACHE_DIR, f"{cache_key}.json")

    if os.path.exists(cached_path):
        cached_video_id = None
        if os.path.exists(meta_path):
            try:
                with open(meta_path) as f:
                    cached_video_id = (json.load(f) or {}).get("pexels_video_id")
            except Exception:
                cached_video_id = None

        if cached_video_id is None or str(cached_video_id) not in cross_video_exclude_ids:
            # Either a cache entry from before this fix (no id recorded — assume
            # fine, same as the old behaviour), or a real id that is not on the
            # cross-video exclusion list. Deliberate exact-keyword reuse is fine.
            print(f"[visual_fetcher] Scene {scene_number}: Using cached clip for '{visual_keyword}'")
            return {
                "clip_path": cached_path, "source": "cache",
                "keyword_used": visual_keyword, "pexels_video_id": cached_video_id,
                "visual_identifier": str(cached_video_id) if cached_video_id is not None else None,
            }
        print(f"[visual_fetcher] Scene {scene_number}: Cached clip for '{visual_keyword}' "
              f"(pexels id={cached_video_id}) was already used in another recent video — "
              f"searching for a fresh one instead.")

    # ── Search Pexels API ─────────────────────────────────────────────────────
    print(f"[visual_fetcher] Scene {scene_number}: Searching Pexels for '{visual_keyword}'...")

    headers = {"Authorization": cfg["PEXELS_API_KEY"]}
    params = {
        "query":       visual_keyword,
        "per_page":    10,
        "orientation": PREFERRED_ORIENTATION,
        "size":        "large",  # HD+
    }

    try:
        resp = requests.get(PEXELS_VIDEO_API, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[visual_fetcher] \u26a0 Pexels API error: {e}. Using fallback.")
        return _get_fallback(job_id, scene_number, visual_keyword, scene_text, duration_needed)

    videos = data.get("videos", [])
    clip = _select_best_clip(videos, duration_needed, all_exclude_ids, scene_text, visual_keyword)

    if not clip:
        print(f"[visual_fetcher] \u26a0 No usable results for '{visual_keyword}'. Trying broader query...")
        simple_query = " ".join(visual_keyword.split()[:2])
        params["query"] = simple_query
        try:
            resp = requests.get(PEXELS_VIDEO_API, headers=headers, params=params, timeout=15)
            data = resp.json()
            videos = data.get("videos", [])
            clip = _select_best_clip(videos, duration_needed, all_exclude_ids, scene_text, visual_keyword)
        except Exception:
            pass

    if not clip:
        print(f"[visual_fetcher] \u26a0 Still no usable results. Using fallback.")
        return _get_fallback(job_id, scene_number, visual_keyword, scene_text, duration_needed)

    # ── Download Clip ─────────────────────────────────────────────────────────
    video_url = clip["url"]
    print(f"[visual_fetcher] \u2713 Downloading: {clip['width']}x{clip['height']}px @ {clip['fps']}fps "
          f"(pexels id={clip['video_id']})")

    try:
        vid_resp = requests.get(video_url, stream=True, timeout=60)
        vid_resp.raise_for_status()
        with open(cached_path, "wb") as f:
            for chunk in vid_resp.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
        print(f"[visual_fetcher] \u2713 Saved to cache: {cached_path}")
        try:
            with open(meta_path, "w") as f:
                json.dump({"pexels_video_id": clip["video_id"], "keyword": visual_keyword}, f)
        except Exception:
            pass  # bookkeeping only — never block a successful download over this
    except Exception as e:
        print(f"[visual_fetcher] \u26a0 Download failed: {e}. Using fallback.")
        return _get_fallback(job_id, scene_number, visual_keyword, scene_text, duration_needed)

    return {
        "clip_path": cached_path, "source": "pexels",
        "keyword_used": visual_keyword, "pexels_video_id": clip["video_id"],
        "visual_identifier": str(clip["video_id"]),
    }


def fetch_all_scene_clips(scenes_with_times: list, job_id: str) -> list:
    """
    Fetches a unique clip for every scene in the storyboard.
    Returns scenes list with clip_path added to each scene.
    """
    enriched_scenes = []
    used_keywords = set()
    used_video_ids = set()  # see fetch_clip_for_scene's exclude_video_ids docstring

    for scene in scenes_with_times:
        keyword = scene["visual_keyword"]

        # If two scenes have the same keyword, add a modifier to vary the clip
        if keyword in used_keywords:
            modifiers = ["close up", "wide shot", "aerial view", "time lapse", "abstract"]
            keyword = f"{keyword} {random.choice(modifiers)}"

        used_keywords.add(scene["visual_keyword"])

        duration_needed = scene.get("time_end", 10) - scene.get("time_start", 0)
        duration_needed = max(duration_needed, 3.0)  # minimum 3 seconds

        clip_info = fetch_clip_for_scene(
            visual_keyword=keyword,
            duration_needed=duration_needed,
            job_id=job_id,
            scene_number=scene["scene_number"],
            exclude_video_ids=used_video_ids,
            scene_text=scene.get("voice_text", ""),
        )
        if clip_info.get("pexels_video_id"):
            used_video_ids.add(clip_info["pexels_video_id"])

        enriched_scenes.append({**scene, **clip_info})

    return enriched_scenes


# ─── Multi-provider chain for the 'sports_visual' style ───────────────────────
#
# WHY A SEPARATE FUNCTION rather than changing fetch_all_scene_clips above:
# that function (and fetch_clip_for_scene, which it calls) is the original,
# already-proven Pexels-only path, and it hard-requires PEXELS_API_KEY via
# require() — exactly right for someone who only wants the original
# behaviour. This channel leans much more heavily on real NAMED subjects
# (players, teams, historic moments) that Pexels' generic stock library
# mostly doesn't have, and it should work even for someone who skips Pexels
# entirely (Wikimedia needs no key at all). So the sports_visual style gets
# its own richer chain instead of bending the original function to cover
# both cases and risking a regression in the one that was already working.
#
# ORDER, AND WHY:
#   1. Wikimedia Commons, using scene["wiki_subject"] if the storyboard set
#      one — a real, named photo beats anything generic, and this needs no
#      API key at all.
#   2. Pexels, using scene["visual_keyword"] — real stock footage for the
#      generic, non-named scenes (skipped cleanly if PEXELS_API_KEY isn't set).
#   3. Pixabay — a second real-media attempt (skipped cleanly if unset).
#   4. Wikimedia again, this time using the generic visual_keyword rather
#      than a specific subject — worth trying even without a named subject,
#      and it costs nothing.
#   5. Cloudflare Workers AI — a free generated image (skipped if unset).
#   6. Hugging Face — the ORIGINAL project's free generated-image fallback,
#      kept as a further attempt (skipped if unset).
#   7. Flat gradient — the one fallback that always exists, same as before.
#
# "stat" and "quiz" scenes (script_generator sets scene_kind for these) are
# skipped entirely here — engine.styles.sports_visual draws a designed card
# for them instead of a photo/clip, so fetching one would only waste a
# provider call for a background that's never used.

def pexels_available() -> bool:
    return bool(get("PEXELS_API_KEY"))


def fetch_all_scene_clips_sports(scenes_with_times: list, job_id: str,
                                 output_dir: str = None,
                                 cross_video_exclusions: dict = None) -> list:
    """`cross_video_exclusions` — the dict returned by engine.visual_usage.load_all(db):
    {"pexels": {...ids}, "wikimedia": {...titles}, "pixabay": {...ids}}. Pass None (the
    default) to render exactly as before this feature existed — every provider treats
    a missing/empty set as "nothing to exclude", so this is purely additive.
    """
    output_dir = output_dir or CLIP_CACHE_DIR
    os.makedirs(output_dir, exist_ok=True)
    cross_video_exclusions = cross_video_exclusions or {}

    enriched_scenes = []
    used_keywords = set()
    used_video_ids = set()

    for scene in scenes_with_times:
        scene_number = scene.get("scene_number", 1)

        if (scene.get("scene_kind") or "").lower() in ("stat", "quiz"):
            enriched_scenes.append({**scene, "clip_path": None, "source": "designed_card",
                                    "keyword_used": scene.get("scene_kind"), "pexels_video_id": None})
            continue

        keyword = (scene.get("visual_keyword") or "").strip()
        wiki_subject = (scene.get("wiki_subject") or "").strip()
        duration_needed = max(scene.get("time_end", 10) - scene.get("time_start", 0), 3.0)

        if keyword in used_keywords:
            modifiers = ["close up", "wide shot", "archive photo", "highlight moment"]
            keyword = f"{keyword} {random.choice(modifiers)}"
        used_keywords.add(scene.get("visual_keyword") or "")

        clip_info = _fetch_sports_visual_chain(
            wiki_subject=wiki_subject, keyword=keyword, scene_text=scene.get("voice_text", ""),
            duration_needed=duration_needed, job_id=job_id, scene_number=scene_number,
            exclude_video_ids=used_video_ids, output_dir=output_dir,
            cross_video_exclusions=cross_video_exclusions,
        )
        if clip_info.get("pexels_video_id"):
            used_video_ids.add(clip_info["pexels_video_id"])

        enriched_scenes.append({**scene, **clip_info})

    return enriched_scenes


def _fetch_sports_visual_chain(wiki_subject: str, keyword: str, scene_text: str,
                               duration_needed: float, job_id: str, scene_number: int,
                               exclude_video_ids: set, output_dir: str,
                               cross_video_exclusions: dict = None) -> dict:
    cross_video_exclusions = cross_video_exclusions or {}
    cross_wiki = cross_video_exclusions.get("wikimedia") or set()
    cross_pexels = cross_video_exclusions.get("pexels") or set()
    cross_pixabay = cross_video_exclusions.get("pixabay") or set()

    # 1. Wikimedia with the specific named subject, if the storyboard gave one.
    if wiki_subject:
        try:
            from engine import wikimedia_visuals
            result = wikimedia_visuals.fetch_photo_for_scene(
                wiki_subject, duration_needed, job_id, scene_number, output_dir,
                exclude_titles=cross_wiki)
            if result:
                return result
        except Exception as e:
            print(f"[visual_fetcher] ⚠ Wikimedia (subject) failed: {e}")

    # 2. Pexels, generic keyword — only attempted if a key is configured.
    if keyword and pexels_available():
        try:
            result = fetch_clip_for_scene(
                visual_keyword=keyword, duration_needed=duration_needed, job_id=job_id,
                scene_number=scene_number, exclude_video_ids=exclude_video_ids, scene_text=scene_text,
                cross_video_exclude_ids=cross_pexels,
            )
            # fetch_clip_for_scene already falls through to Hugging Face/gradient
            # internally on a bad search, so a real clip_path here means real
            # Pexels footage; anything else, try the next provider instead of
            # accepting its internal gradient fallback early.
            if result.get("source") == "pexels":
                return result
        except Exception as e:
            print(f"[visual_fetcher] ⚠ Pexels failed: {e}")

    # 3. Pixabay (photo or video) — skipped cleanly if PIXABAY_API_KEY unset.
    try:
        from engine import pixabay_visuals
        if pixabay_visuals.available() and keyword:
            result = pixabay_visuals.fetch_for_scene(keyword, duration_needed, job_id, scene_number,
                                                      output_dir, exclude_ids=cross_pixabay)
            if result:
                return result
    except Exception as e:
        print(f"[visual_fetcher] ⚠ Pixabay failed: {e}")

    # 4. Wikimedia again with the generic keyword — free, worth trying even
    #    without a named subject, and before resorting to synthetic images.
    if keyword:
        try:
            from engine import wikimedia_visuals
            result = wikimedia_visuals.fetch_photo_for_scene(
                keyword, duration_needed, job_id, scene_number, output_dir,
                exclude_titles=cross_wiki)
            if result:
                return result
        except Exception as e:
            print(f"[visual_fetcher] ⚠ Wikimedia (keyword) failed: {e}")

    # 5. Cloudflare Workers AI generated image — skipped cleanly if unset.
    try:
        from engine import cf_ai_visuals
        if cf_ai_visuals.available():
            result = cf_ai_visuals.generate_for_scene(
                keyword, scene_text, duration_needed, job_id, scene_number, output_dir)
            if result:
                return result
    except Exception as e:
        print(f"[visual_fetcher] ⚠ Cloudflare AI image failed: {e}")

    # 6. Hugging Face generated image — the original project's AI fallback.
    try:
        from engine import backup_visuals
        if backup_visuals.available():
            gen_path = os.path.join(output_dir, f"{job_id}_s{scene_number}_hf.mp4")
            if backup_visuals.generate_scene_visual(keyword, scene_text, duration_needed, gen_path):
                return {"clip_path": gen_path, "source": "ai_generated",
                        "keyword_used": keyword or "ai_generated", "pexels_video_id": None}
    except Exception as e:
        print(f"[visual_fetcher] ⚠ Hugging Face image failed: {e}")

    # 7. Always-available fallback — a designed gradient, exactly like the
    #    original project's behaviour when nothing else is found.
    return {"clip_path": None, "source": FALLBACK_CLIP_TYPE, "keyword_used": keyword or "fallback",
            "pexels_video_id": None}


# ─── Internal Helpers ──────────────────────────────────────────────────────────

def rank_candidates_with_ai(scene_text: str, keyword: str, candidates: list) -> list:
    """Re-orders Pexels candidates by how well they actually match the scene.

    WHY THIS EXISTS: reviewing real generated output turned up a person in
    swimming goggles standing in for "keep these beasts cool", and a Spanish
    emergency-stop button standing in for a line about supercomputers. Pexels
    returns whatever its text search matches, and the old code then picked at
    RANDOM from the results that were big enough. Random selection from a
    loosely-matched set is how you get a video about data centres showing a
    derelict warehouse.

    Pexels returns rich metadata per video (the uploader's own description,
    tags, dimensions). Handing that metadata plus the narration line to the
    model that wrote the script and asking which clip actually fits is one
    cheap text call — no image analysis, no extra API, well inside the free
    tier — and it is the difference between b-roll that illustrates the line
    and b-roll that merely shares a keyword with it.

    Fails open: any error and the original order is returned unchanged, so a
    model outage costs relevance, not the render.
    """
    if len(candidates) < 2:
        return candidates
    try:
        from engine.script_generator import rank_visual_candidates
        order = rank_visual_candidates(scene_text, keyword, candidates)
        if order:
            ranked = [candidates[i] for i in order if 0 <= i < len(candidates)]
            missing = [c for i, c in enumerate(candidates) if i not in order]
            return ranked + missing
    except Exception as e:
        print(f"[visual_fetcher] \u26a0 AI ranking unavailable ({e}); using search order.")
    return candidates


def _select_best_clip(videos: list, duration_needed: float, exclude_video_ids: set = None,
                      scene_text: str = "", keyword_used: str = "") -> dict | None:
    """Selects the best video file from Pexels results, skipping any whose
    parent video ID is already in exclude_video_ids.

    Compares as strings so callers can freely mix this-video ids (ints, as
    the Pexels API returns them) with cross-video ids loaded back out of the
    visual_usage table (stored, and therefore returned, as strings) in one
    set without either kind silently failing to match the other.
    """
    exclude_ids_str = {str(x) for x in (exclude_video_ids or set())}
    candidates = []

    for video in videos:
        if str(video.get("id")) in exclude_ids_str:
            continue
        # The uploader's own words about the clip. This is the only signal
        # available for judging relevance without downloading and analysing
        # the footage, so it is carried through to the AI ranking step.
        blurb = (video.get("alt") or video.get("url", "").rstrip("/").split("/")[-1].replace("-", " "))
        for file in video.get("video_files", []):
            w = file.get("width", 0)
            h = file.get("height", 0)
            if w >= PREFERRED_MIN_WIDTH and h >= PREFERRED_MIN_HEIGHT:
                candidates.append({
                    "url": file["link"], "width": w, "height": h,
                    "fps": file.get("fps", 25), "duration": video.get("duration", 0),
                    "video_id": video.get("id"), "description": blurb,
                })

    if not candidates:
        # Loosen requirements — accept any reasonable resolution (still excluding repeats)
        for video in videos:
            if str(video.get("id")) in exclude_ids_str:
                continue
            for file in video.get("video_files", []):
                if file.get("width", 0) >= 1280:
                    candidates.append({
                        "url": file["link"], "width": file["width"],
                        "height": file.get("height", 720), "fps": file.get("fps", 25),
                        "duration": video.get("duration", 0), "video_id": video.get("id"),
                    })

    if not candidates:
        return None

    # Deduplicate to one file per source video before ranking — otherwise the
    # same clip appears five times (once per resolution) and crowds out the
    # alternatives the ranker is supposed to be choosing between.
    by_video, order = {}, []
    for c in candidates:
        vid = c["video_id"]
        if vid not in by_video:
            by_video[vid] = c
            order.append(vid)
        elif c["width"] > by_video[vid]["width"]:
            by_video[vid] = c
    unique = [by_video[v] for v in order]

    long_enough = [c for c in unique if c["duration"] >= duration_needed]
    pool = long_enough or unique

    # AI ranking is NOT called here any more.
    #
    # It used to run once per scene, which meant a 5-scene video spent 5 Gemini
    # calls on b-roll selection alone — on a 20-calls-per-day free tier that
    # single line was over a third of the entire daily budget, and it is why
    # generation started dying with 429 RESOURCE_EXHAUSTED partway through a
    # batch. Ranking now happens once for the whole video in rank_all_scenes().
    #
    # Falling back to search order is a small quality loss and a large budget
    # win: Pexels' own relevance ordering is decent, and a video that renders
    # with slightly worse b-roll beats a video that does not render at all.
    return pool[0] if pool else None


def _get_fallback(job_id: str, scene_number: int, visual_keyword: str = "",
                  scene_text: str = "", duration_needed: float = 6.0) -> dict:
    """Returns a fallback indicator when no Pexels clip is found.

    Tries the free Hugging Face image-generation backup FIRST (see
    engine/backup_visuals.py) — an on-topic AI image beats a generic flat
    gradient. Only drops to the gradient if that also isn't configured or
    also fails; either way this function never raises, matching the
    contract every caller above already expects.
    """
    try:
        from engine import backup_visuals
        if backup_visuals.available():
            os.makedirs(CLIP_CACHE_DIR, exist_ok=True)
            gen_path = os.path.join(CLIP_CACHE_DIR, f"{job_id}_s{scene_number}_ai.mp4")
            if backup_visuals.generate_scene_visual(visual_keyword, scene_text,
                                                     duration_needed, gen_path):
                return {
                    "clip_path": gen_path, "source": "ai_generated",
                    "keyword_used": visual_keyword or "ai_generated",
                    "pexels_video_id": None,
                }
    except Exception as e:
        print(f"[visual_fetcher] \u26a0 AI-generated visual backup failed ({e}). "
              f"Using the gradient fallback instead.")

    return {
        "clip_path":    None,
        "source":       FALLBACK_CLIP_TYPE,
        "keyword_used": "fallback",
        "pexels_video_id": None,
    }


# ─── Test / Debug ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    result = fetch_clip_for_scene(
        visual_keyword="silicon wafer semiconductor cleanroom",
        duration_needed=8.5,
        job_id="test001",
        scene_number=1
    )
    print(result)
