"""
cf_ai_visuals.py — free AI-generated image, tried when NO real photo or
footage could be found anywhere (Pexels, Wikimedia, Pixabay all empty).
==============================================================================

WHY CLOUDFLARE WORKERS AI, ALONGSIDE THE EXISTING HUGGING FACE BACKUP
engine/backup_visuals.py already does this job using Hugging Face's free
serverless inference. This module adds a SECOND free AI-image option
(Cloudflare Workers AI's own hosted FLUX.1-schnell) ahead of it, because:
  - Cloudflare's free allocation is a clear, published number — 10,000
    "Neurons" per day, shared across every model you call — rather than an
    unpublished, load-dependent limit. FLUX.1-schnell costs roughly
    4.8 neurons per 512x512 tile plus ~9.6 per diffusion step, so even a
    handful of generations a day costs a small fraction of the daily
    allowance: comfortably enough headroom for this channel's actual needs
    (an AI image is the LAST resort, reached only when three real-media
    sources already failed for a scene).
  - It needs only a free Cloudflare account (no card) plus an Account ID
    and an API token scoped to Workers AI — both visible in the dashboard,
    nothing to install.

THIS IS A LAST-RESORT FALLBACK, NOT A REPLACEMENT FOR REAL PHOTOS
Exactly the same honesty rule as every other fallback in this project:
every image made this way is tagged source="ai_generated_cf" (distinct
from Hugging Face's own "ai_generated" tag) so it is never confused with
real footage or a real archival photo anywhere it's displayed or logged.

Silent no-op if CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN are not set —
visual_fetcher simply moves on to the existing Hugging Face fallback, then
the flat gradient, exactly as before this file existed.
"""
import base64
import json
import os
import requests

from engine.config import get
from engine.visual_kenburns import image_to_clip

CF_MODEL = "@cf/black-forest-labs/flux-1-schnell"
TIMEOUT_SECONDS = 45


def available() -> bool:
    return bool(get("CLOUDFLARE_ACCOUNT_ID") and get("CLOUDFLARE_API_TOKEN"))


def _build_prompt(visual_keyword: str, scene_text: str) -> str:
    base = (visual_keyword or "").strip() or (scene_text or "").strip()[:100]
    return (
        f"{base}, realistic sports photography, natural stadium lighting, "
        f"documentary photojournalism style, no text, no watermark, no logos, no captions"
    )


def generate_for_scene(visual_keyword: str, scene_text: str, duration_needed: float,
                       job_id: str, scene_number: int, output_dir: str) -> dict | None:
    account_id = get("CLOUDFLARE_ACCOUNT_ID")
    token = get("CLOUDFLARE_API_TOKEN")
    if not account_id or not token:
        return None

    prompt = _build_prompt(visual_keyword, scene_text)
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{CF_MODEL}"

    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"prompt": prompt, "steps": 6},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        print(f"[cf_ai_visuals] ⚠ Request failed ({e}).")
        return None

    if not resp.ok:
        print(f"[cf_ai_visuals] ⚠ Cloudflare returned {resp.status_code}: {resp.text[:200]}")
        return None

    try:
        data = resp.json()
        b64_image = data.get("result", {}).get("image")
        if not b64_image:
            print(f"[cf_ai_visuals] ⚠ No image in response: {json.dumps(data)[:200]}")
            return None
        img_bytes = base64.b64decode(b64_image)
    except Exception as e:
        print(f"[cf_ai_visuals] ⚠ Could not decode image response ({e}).")
        return None

    os.makedirs(output_dir, exist_ok=True)
    img_path = os.path.join(output_dir, f"{job_id}_s{scene_number}_cfai.png")
    mp4_path = os.path.join(output_dir, f"{job_id}_s{scene_number}_cfai.mp4")
    try:
        with open(img_path, "wb") as f:
            f.write(img_bytes)
    except Exception as e:
        print(f"[cf_ai_visuals] ⚠ Could not save generated image ({e}).")
        return None

    ok = image_to_clip(img_path, mp4_path, duration_needed, scene_number=scene_number, motion_seed=3)
    try:
        os.remove(img_path)
    except OSError:
        pass
    if not ok:
        return None

    print(f"[cf_ai_visuals] ✓ Generated an on-topic AI image for: {visual_keyword or scene_text[:40]}")
    return {
        "clip_path": mp4_path, "source": "ai_generated_cf",
        "keyword_used": visual_keyword or "ai_generated", "pexels_video_id": None,
    }
