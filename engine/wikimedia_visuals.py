"""
wikimedia_visuals.py — real, reliably-licensed photos for scenes Pexels
cannot cover: named players, historical moments, stadiums, team photos.
==============================================================================

WHY THIS EXISTS
Pexels is real stock footage, but it has almost nothing of a NAMED, REAL
subject — there is no Pexels clip of Sachin Tendulkar's 1983-era India, or
of the actual Eden Gardens. For a channel that is largely player stories,
team histories and World Cup moments, that gap matters a lot more than it
did for the original project's generic tech/science topics.

Wikimedia Commons (commons.wikimedia.org) is Wikipedia's own free media
library: tens of millions of images, all either public domain or under a
license (CC-BY, CC-BY-SA) that explicitly permits reuse, searchable with a
plain, keyless, no-signup REST API. That combination — real, on-subject,
and legally clean — is exactly what a factual sports channel needs for
anything Pexels cannot supply.

NO API KEY, NO SIGNUP
This is one of the few genuinely free-forever sources in this whole
project: the MediaWiki API has no authentication requirement for read-only
search and file access, and no published hard rate limit for this kind of
light, occasional use (the project's own etiquette guide asks only for a
descriptive User-Agent, which this module sets).

HOW A RESULT BECOMES A SCENE
Exactly the same contract as backup_visuals.py: download the best matching
image, then hand it to visual_kenburns.image_to_clip() to become a short
.mp4 with a Ken Burns pan/zoom, so visual_fetcher.py can treat it exactly
like a downloaded Pexels clip — nothing downstream needs to know a scene's
visual started life as a still photo from an entirely different source.

SAFETY: this module only ever fetches and re-encodes an image that a
public Wikimedia search already surfaced under its own listed license. It
does not edit, caption, or misattribute the image; the on-screen result is
a plain background clip, the same as any other visual source in this
pipeline.
"""
import os
import requests

from engine.visual_kenburns import image_to_clip

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
TIMEOUT_SECONDS = 20
USER_AGENT = "CricketShortsStudio/1.0 (educational short-form video project; no contact configured)"

# Commons is full of icons, logos, maps and diagrams that search relevance
# alone won't filter out — reject filenames that are almost never a usable
# photographic background.
_REJECT_MARKERS = ("icon", "logo", "flag of", ".svg", "diagram", "map of", "coa_")


def available() -> bool:
    """Always True — no API key needed. Kept as a function (rather than a
    bare constant) so every provider in the visual_fetcher chain has the
    same `available()` shape, whether or not it actually needs a key."""
    return True


def _search_image_titles(query: str, limit: int = 8) -> list:
    """Full-text searches Commons for files matching `query`, returns
    candidate file titles (e.g. 'File:Sachin Tendulkar 2011.jpg')."""
    params = {
        "action": "query", "format": "json", "list": "search",
        "srsearch": f"{query} filetype:bitmap",
        "srnamespace": 6,  # File: namespace
        "srlimit": limit,
    }
    resp = requests.get(COMMONS_API, params=params, timeout=TIMEOUT_SECONDS,
                        headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    hits = resp.json().get("query", {}).get("search", [])
    return [h["title"] for h in hits]


def _image_info(titles: list) -> list:
    """Resolves file titles to direct download URLs + dimensions in one
    batched call (the MediaWiki API allows up to 50 titles per request)."""
    if not titles:
        return []
    params = {
        "action": "query", "format": "json", "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "titles": "|".join(titles[:50]),
    }
    resp = requests.get(COMMONS_API, params=params, timeout=TIMEOUT_SECONDS,
                        headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", {})
    out = []
    for page in pages.values():
        info = (page.get("imageinfo") or [None])[0]
        if not info or not info.get("url"):
            continue
        title = (page.get("title") or "").lower()
        if any(m in title for m in _REJECT_MARKERS):
            continue
        out.append({
            "title": page.get("title"), "url": info["url"],
            "width": info.get("width", 0), "height": info.get("height", 0),
            # FIXED: `extmetadata` was already being REQUESTED on the line
            # above and then silently discarded, so the licence arrived in
            # every response and was never read — this module filtered on
            # filename and image size only. Commons is overwhelmingly free
            # media, but it also carries fair-use files, trademarked logos,
            # non-commercial-only uploads and files pending deletion, and
            # "overwhelmingly" is not something a monetised channel can rely
            # on. engine/image_license.py now reads this.
            "extmetadata": info.get("extmetadata") or {},
        })
    return out


def fetch_photo_for_scene(query: str, duration_needed: float, job_id: str,
                          scene_number: int, output_dir: str,
                          exclude_titles: set = None) -> dict | None:
    """Searches Commons, downloads the best real photo for `query`, and
    converts it into a short .mp4. Returns the same shape visual_fetcher's
    other providers use, or None if nothing usable was found — callers move
    on to the next provider in the chain on None, exactly like every other
    best-effort visual source in this project.

    `exclude_titles` — file titles (e.g. 'File:Sachin Tendulkar 2011.jpg')
    already used by OTHER recent videos (see engine/visual_usage.py). Commons
    search is fully deterministic — the same query always returns the same
    top hit first — so without this, two unrelated videos that happen to
    search similar text get the exact same photo every time. We skip any
    excluded title and fall through to the next real candidate instead; only
    if literally every candidate is excluded do we return None, same as a
    genuinely empty search.
    """
    query = (query or "").strip()
    if not query:
        return None

    # Part 1E: some subjects must never be SEARCHED for, not merely filtered
    # out of the results — a correctly-licensed photograph of a film poster
    # is still a picture of a film poster.
    try:
        from engine import image_license
        if image_license.is_banned_subject(query):
            return None
    except ImportError:
        image_license = None

    try:
        titles = _search_image_titles(query)
        candidates = _image_info(titles)
    except Exception as e:
        print(f"[wikimedia_visuals] ⚠ Search failed for '{query}': {e}")
        return None

    # THE LICENCE GATE. Runs before an image can become a scene, which is
    # what Part 1E requires ("this filter runs before an image is ever placed
    # in a video"). An unrecognised or missing licence fails.
    if image_license is not None:
        before = len(candidates)
        candidates = image_license.filter_candidates(candidates)
        if not candidates:
            print(f"[wikimedia_visuals] No freely-licensed image for '{query}' "
                  f"({before} candidate(s) all failed the licence check). "
                  f"Falling through to the next visual provider.")
            return None

    # Prefer a reasonably large image — Commons has plenty of thumbnail-only
    # uploads that would look soft once cropped to a 1080-wide frame.
    candidates = [c for c in candidates if c["width"] >= 700 or c["height"] >= 700] or candidates
    if not candidates:
        print(f"[wikimedia_visuals] No usable Commons image found for '{query}'.")
        return None

    if exclude_titles:
        fresh = [c for c in candidates if c["title"] not in exclude_titles]
        if fresh:
            candidates = fresh
        else:
            print(f"[wikimedia_visuals] All {len(candidates)} candidate(s) for "
                  f"'{query}' were already used in a recent video — reusing the "
                  f"top one anyway rather than returning nothing.")

    best = candidates[0]
    os.makedirs(output_dir, exist_ok=True)
    img_ext = os.path.splitext(best["url"])[1] or ".jpg"
    img_path = os.path.join(output_dir, f"{job_id}_s{scene_number}_wiki{img_ext}")
    mp4_path = os.path.join(output_dir, f"{job_id}_s{scene_number}_wiki.mp4")

    try:
        r = requests.get(best["url"], timeout=30, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        with open(img_path, "wb") as f:
            f.write(r.content)
    except Exception as e:
        print(f"[wikimedia_visuals] ⚠ Download failed for '{best['title']}': {e}")
        return None

    ok = image_to_clip(img_path, mp4_path, duration_needed, scene_number=scene_number, motion_seed=1)
    try:
        os.remove(img_path)
    except OSError:
        pass
    if not ok:
        return None

    print(f"[wikimedia_visuals] ✓ Used real photo for '{query}': {best['title']}")
    return {
        "clip_path": mp4_path, "source": "wikimedia",
        "keyword_used": query, "pexels_video_id": None,
        "visual_identifier": best["title"],
    }
