"""
thumbnail_generator.py — automatic, non-"AI art" YouTube thumbnails.
=====================================================================

THE REQUEST THIS ANSWERS
"add thumbnail section also to the app and automate it along with the
automatic video posting" — thumbnails that look "engaging, well reachable,
related" and specifically NOT "too open AI created".

WHY THIS DOESN'T USE AN IMAGE-GENERATION MODEL AT ALL
That second requirement is the whole design driver here. An AI-generated
background image is exactly what gives a thumbnail that slightly-too-glossy,
slightly-off "AI art" look the request is trying to avoid — and this project
already has real footage for every video, found by visual_fetcher.py
specifically because it's real and on-subject. So a thumbnail here is:

    a REAL frame grabbed straight out of the video you already rendered
    (a real photo of the actual named player/ground/team, exactly what the
    video itself is about)
      + a dark gradient scrim so text stays readable over any photo
      + one short, bold, all-caps headline (the video's own title),
        in the same clean sans-serif this project already uses for
        captions (Montserrat ExtraBold) — no filters, no stylization,
        no synthetic imagery anywhere in the pipeline.

That "real photo + bold caption" look is the actual house style of nearly
every successful sports/facts Shorts channel on YouTube today — it reads as
made-by-a-person because it is: nothing in this file invents pixels, it only
arranges real ones.

WHICH FRAME GETS USED
CHANGED after a real channel review showed most thumbnails looking near-
identical: "stat" scenes are drawn by engine/styles/sports_visual.py as a
DESIGNED CARD, not a photo — same background gradient, same layout, every
single time (only the number/words on it change). Almost every video in
this persona's archetypes has a stat scene, so picking it FIRST, every
time, meant most of the channel's thumbnails were the same teal card with
different text — exactly the "thumbnails look the same" complaint. A real,
specific photo/clip varies naturally from video to video and is a better
answer to "engaging, well reachable, related" than a repeated template.
New priority, in order:
  1. Any scene with a REAL fetched photo/clip (_visual_source is wikimedia/
     pexels/cache/pixabay — see orchestrator.py, which folds this onto each
     storyboard scene right after the visual-fetch step). A named-subject
     Wikimedia photo is preferred first within this group when more than
     one qualifies, since that is the most specific, least generic shot
     available — a real photo of the actual player/ground/moment.
  2. The "stat" scene, if this video has one and no real photo qualified —
     scene_kind == "stat" is, by design (see archetypes.py /
     script_generator.py), the single biggest, most quotable number or
     record in the whole video, and still a perfectly good fallback.
  3. The opening hook (scene_number == 1), regardless of its visual source.
  4. Whichever scene actually has footage, as a last resort.
A frame partway through that scene (not its very first instant, which is
often mid-transition/fade) is grabbed directly from the final rendered
video with ffmpeg, so what's captured is always a clean, fully-loaded shot.

REQUIRES: ffmpeg (already a hard dependency of this whole project) and PIL
(already used by video_compositor.py / styles/sports_visual.py). No new
dependency, no new API key, no extra cost.

OUTPUT: a single 1080x1920 JPEG (matching the Short's own 9:16 frame — see
video_compositor.py's VIDEO_WIDTH/VIDEO_HEIGHT) under YouTube's 2MB
thumbnail upload limit.

A NOTE ON WHERE THIS ACTUALLY SHOWS UP
YouTube Shorts are usually browsed in the vertical Shorts feed, which shows
the video's own first frame regardless of a custom thumbnail — this is a
YouTube product behaviour, not something any app can configure around. The
custom thumbnail generated here DOES show up everywhere else a Short can
appear: search results, suggested/related videos, the channel's own video
grid, and any embed or share link. It is still worth having for all of
those places, just not a guaranteed override of the Shorts-feed view itself.

SEPARATELY: setting a custom thumbnail on YouTube (via this module's output
+ engine/publisher.py's set_thumbnail()) requires the channel's Google
account to be phone-verified at youtube.com/verify. This is a one-time,
free, two-minute step on YouTube's side — not a limitation of this app —
but it has to happen before thumbnails will actually take effect; see
set_thumbnail()'s own docstring for what happens if it hasn't.
"""
import os
import re
import subprocess

from PIL import Image, ImageDraw, ImageFont, ImageFilter

THUMB_WIDTH, THUMB_HEIGHT = 1080, 1920  # matches video_compositor.py's own frame size

FONT_PATH = "assets/fonts/Montserrat-Variable.ttf"

# The same teal accent sports_visual.py already uses for its "STAT" card —
# reusing it here (instead of inventing a new color) is what makes a
# thumbnail and its own video feel like one consistent channel, not two
# unrelated styles bolted together.
ACCENT_COLOR = (140, 255, 230)
WHITE = (255, 255, 255)

MAX_JPEG_BYTES = 2 * 1024 * 1024  # YouTube's thumbnail upload limit


def _font(size: int, bold: bool = True):
    try:
        f = ImageFont.truetype(FONT_PATH, size)
        try:
            names = f.get_variation_names()
            target = b"ExtraBold" if bold and b"ExtraBold" in names else None
            if target:
                f.set_variation_by_name(target)
        except Exception:
            pass
        return f
    except Exception:
        return ImageFont.load_default()


# Real-photo/clip sources, as folded onto each scene by orchestrator.py's
# `sb_scene["_visual_source"] = rendered_scene.get("source")` line — every
# OTHER value ("designed_card", "ai_generated", FALLBACK_CLIP_TYPE, or
# simply missing on styles that skip visual-fetch entirely) is NOT a real,
# distinctive photo and should not outrank one. "wikimedia" goes first
# within this set because a named-subject Wikimedia match is the most
# specific, least generic shot this pipeline can produce.
_REAL_PHOTO_SOURCES_BY_PRIORITY = ("wikimedia", "pexels", "cache", "pixabay_video", "pixabay_photo")


def _pick_source_scene(storyboard: dict) -> dict | None:
    scenes = [s for s in (storyboard.get("scenes") or []) if s.get("time_end") is not None]
    if not scenes:
        return None

    normal = [s for s in scenes if (s.get("scene_kind") or "").lower() not in ("stat", "quiz")]

    # 1. A real, specific photo/clip beats a repeated template — see the
    #    module docstring's "WHICH FRAME GETS USED" for why this moved to
    #    the top. Scan in source-priority order so a named Wikimedia photo
    #    wins over a generic Pexels/Pixabay keyword match when both exist.
    for source in _REAL_PHOTO_SOURCES_BY_PRIORITY:
        for s in normal:
            if (s.get("_visual_source") or "") == source:
                return s

    # 2. No real photo anywhere in this video — the designed stat card is
    #    still a good, legible, on-brand fallback.
    stat = [s for s in scenes if (s.get("scene_kind") or "").lower() == "stat"]
    if stat:
        return stat[0]

    # 3. The opening hook, whatever its visual source.
    hook = [s for s in normal if s.get("scene_number") == 1]
    if hook:
        return hook[0]
    if normal:
        return normal[0]

    return scenes[0]


def _extract_frame(video_path: str, scene: dict, out_path: str) -> bool:
    """Grabs one still frame from partway through `scene`'s time range in the
    final rendered video. Partway through (35%), not the very first instant,
    which is often still mid-transition/fade from the previous scene."""
    start = float(scene.get("time_start") or 0)
    end = float(scene.get("time_end") or (start + 3))
    duration = max(end - start, 0.5)
    at = start + duration * 0.35

    result = subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{at:.2f}", "-i", video_path,
         "-frames:v", "1", "-q:v", "2", out_path],
        capture_output=True, timeout=60,
    )
    return result.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
               max_width: int, max_lines: int = 3) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines[:max_lines]


def _headline_text(storyboard: dict) -> str:
    title = (storyboard.get("video_title") or "").strip()
    # Strip the "#Shorts" tag publisher.py appends at upload time — it reads
    # as noise on a thumbnail, the "#Shorts" badge is already shown by
    # YouTube's own UI on every Short regardless.
    title = re.sub(r"#shorts\b", "", title, flags=re.IGNORECASE).strip(" -|#")
    return title.upper()


def generate_thumbnail(video_path: str, storyboard: dict, job_id: str, output_dir: str) -> str | None:
    """Builds a thumbnail for this video and returns its local file path, or
    None on any failure — best-effort, same contract as every other
    optional enrichment step in this pipeline (a missed thumbnail should
    cost nothing but the thumbnail; the video itself must still publish
    with YouTube's own auto-generated one).
    """
    scene = _pick_source_scene(storyboard)
    if not scene:
        print(f"[thumbnail_generator] ⚠ No timed scene available for {job_id}; skipping thumbnail.")
        return None

    os.makedirs(output_dir, exist_ok=True)
    raw_frame_path = os.path.join(output_dir, f"{job_id}_thumb_raw.jpg")
    thumb_path = os.path.join(output_dir, f"{job_id}_thumb.jpg")

    if not _extract_frame(video_path, scene, raw_frame_path):
        print(f"[thumbnail_generator] ⚠ Frame extraction failed for {job_id}; skipping thumbnail.")
        return None

    try:
        img = Image.open(raw_frame_path).convert("RGB")
        if img.size != (THUMB_WIDTH, THUMB_HEIGHT):
            img = img.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)
        img = img.convert("RGBA")

        # Dark gradient scrim across the bottom ~40% — keeps bold white text
        # legible no matter what the real photo behind it looks like,
        # without touching (or hiding) the rest of the frame.
        scrim = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0, 0))
        sd = ImageDraw.Draw(scrim)
        scrim_top = int(THUMB_HEIGHT * 0.58)
        for y in range(scrim_top, THUMB_HEIGHT):
            t = (y - scrim_top) / max(THUMB_HEIGHT - scrim_top, 1)
            alpha = int(210 * t)
            sd.line([(0, y), (THUMB_WIDTH, y)], fill=(0, 0, 0, alpha))
        img.alpha_composite(scrim)

        draw = ImageDraw.Draw(img)
        headline = _headline_text(storyboard) or "WATCH TILL THE END"
        font = _font(int(THUMB_WIDTH * 0.095))
        max_text_width = int(THUMB_WIDTH * 0.86)
        lines = _wrap_text(draw, headline, font, max_text_width, max_lines=3)
        if not lines:
            lines = [headline[:24]]

        # A single number/stat token (if the headline has one) is drawn in
        # the house teal accent instead of plain white — the same cheap,
        # consistent visual trick sports_visual.py's own stat card uses, so
        # the thumbnail and the video it belongs to read as one channel.
        number_pattern = re.compile(r"\d[\d,]*\+?")

        line_height = int(font.size * 1.18)
        total_h = line_height * len(lines)
        y = THUMB_HEIGHT - int(THUMB_HEIGHT * 0.06) - total_h

        for line in lines:
            x = (THUMB_WIDTH - draw.textlength(line, font=font)) / 2
            match = number_pattern.search(line)
            if match:
                before, token, after = line[:match.start()], match.group(), line[match.end():]
                cursor_x = x
                for part, color in ((before, WHITE), (token, ACCENT_COLOR), (after, WHITE)):
                    if not part:
                        continue
                    draw.text((cursor_x, y), part, font=font, fill=color,
                              stroke_width=6, stroke_fill=(0, 0, 0))
                    cursor_x += draw.textlength(part, font=font)
            else:
                draw.text((x, y), line, font=font, fill=WHITE,
                          stroke_width=6, stroke_fill=(0, 0, 0))
            y += line_height

        img = img.convert("RGB")
        quality = 90
        img.save(thumb_path, "JPEG", quality=quality)
        while os.path.getsize(thumb_path) > MAX_JPEG_BYTES and quality > 40:
            quality -= 10
            img.save(thumb_path, "JPEG", quality=quality)

        print(f"[thumbnail_generator] ✓ Thumbnail built for {job_id}: {thumb_path}")
        return thumb_path
    except Exception as e:
        print(f"[thumbnail_generator] ⚠ Thumbnail composition failed for {job_id} ({e}); "
              f"the video is unaffected, it will just publish with YouTube's default thumbnail.")
        return None
    finally:
        try:
            if os.path.exists(raw_frame_path):
                os.remove(raw_frame_path)
        except OSError:
            pass
