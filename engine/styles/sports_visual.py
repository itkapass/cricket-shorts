"""
sports_visual.py — background-clip builder for the 'sports_visual' render
style (the default style for this cricket/sports build).

THREE KINDS OF SCENE, ONE STYLE MODULE
  1. Ordinary scenes — real footage or a real photo. clip_path was filled in
     by visual_fetcher.py's provider chain (Pexels video -> Wikimedia Commons
     photo -> Pixabay photo/video -> AI-generated image -> gradient), and by
     the time it reaches here EVERY source has already been turned into an
     .mp4 (a still photo becomes a short Ken-Burns video at fetch time — see
     visual_kenburns.py — so nothing downstream needs to know whether a given
     scene started as a video or a photograph). This reuses
     engine.styles.stock_footage's own loader + crop + subtle zoom unchanged.
  2. "stat" scenes — a designed data-callout card (big number, short label)
     for the records/stats archetype's punch line.
  3. "quiz" scenes — the end-of-video engagement-question card this whole
     channel is built around (see engine/engagement.py). A distinct look
     (a large "?" motif) so the ask-a-question moment visually reads as a
     different beat from the rest of the video, not just more narration.

A scene is routed to (2) or (3) by `scene.get("scene_kind")`, which
script_generator.py sets when it writes the storyboard's stat/quiz scenes.
Anything else (the normal case) falls straight through to stock_footage's
existing, already-proven background builder.

Public entry point matches every other style module:
    build_background_clip(scene, duration, video_w, video_h) -> moviepy clip
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from moviepy.editor import VideoClip

from engine.styles import stock_footage

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

# A cool, "floodlit stadium at night" palette — distinct from quote_card's
# warm paper look and from the plain dark gradients other styles use, so a
# stat/quiz card reads as its own kind of moment rather than a plain caption
# screen with no design behind it.
STAT_TOP, STAT_BOT = (8, 20, 28), (10, 46, 44)
QUIZ_TOP, QUIZ_BOT = (10, 12, 30), (28, 16, 54)

_FONT_CANDIDATES = [
    "assets/fonts/Montserrat-Variable.ttf",
]


def _font(size: int, bold: bool = True):
    for path in _FONT_CANDIDATES:
        try:
            f = ImageFont.truetype(path, size)
            try:
                names = f.get_variation_names()
                target = b"ExtraBold" if bold and b"ExtraBold" in names else None
                if target:
                    f.set_variation_by_name(target)
            except Exception:
                pass
            return f
        except Exception:
            continue
    return ImageFont.load_default()


def _gradient(w, h, top, bot):
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def _vignette(img_rgba, w, h, strength=90):
    v = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(v)
    vd.ellipse([-w * 0.3, -h * 0.2, w * 1.3, h * 1.1], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(220))
    dark = Image.new("RGBA", (w, h), (0, 0, 0, strength))
    mask = Image.eval(v, lambda p: 255 - p)
    img_rgba.paste(dark, (0, 0), mask)
    return img_rgba


def _stadium_lines(draw, w, h, seed, color):
    """A few thin diagonal 'floodlight beam' streaks, procedural, cheap —
    same spirit as quote_card's leaf-shadow cluster: a design signature
    that costs nothing to license because nothing is a photo or a font
    asset, just drawn shapes."""
    rnd = random.Random(seed)
    for _ in range(4):
        x0 = rnd.uniform(-w * 0.2, w * 0.6)
        draw.polygon(
            [(x0, -20), (x0 + w * 0.18, -20), (x0 - w * 0.3, h + 20), (x0 - w * 0.5, h + 20)],
            fill=color,
        )


def _stat_card_frame(w, h, seed):
    base = _gradient(w, h, STAT_TOP, STAT_BOT).convert("RGBA")
    beams = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(beams)
    _stadium_lines(bd, w, h, seed, (255, 255, 255, 10))
    beams = beams.filter(ImageFilter.GaussianBlur(8))
    base.alpha_composite(beams)
    base = _vignette(base, w, h, strength=110)

    draw = ImageDraw.Draw(base)
    # A thin top-and-bottom rule frames the card area where captions will
    # sit (captions render around 62% down — see video_compositor.py).
    ink = (140, 255, 230, 160)
    pad = int(w * 0.08)
    draw.line([(pad, int(h * 0.30)), (w - pad, int(h * 0.30))], fill=ink, width=2)
    draw.line([(pad, int(h * 0.78)), (w - pad, int(h * 0.78))], fill=ink, width=2)
    label_font = _font(int(w * 0.045))
    draw.text((w // 2, int(h * 0.24)), "STAT", font=label_font, fill=(140, 255, 230, 200), anchor="mm")
    return base.convert("RGB")


def _quiz_card_frame(w, h, seed):
    base = _gradient(w, h, QUIZ_TOP, QUIZ_BOT).convert("RGBA")
    beams = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(beams)
    _stadium_lines(bd, w, h, seed, (255, 255, 255, 8))
    beams = beams.filter(ImageFilter.GaussianBlur(8))
    base.alpha_composite(beams)

    # A single huge, heavily-blurred "?" watermark behind the captions —
    # the visual signature for "this is the question moment", legible even
    # though the real text is the separately-rendered caption cards.
    qfont = _font(int(h * 0.34))
    qlayer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    qd = ImageDraw.Draw(qlayer)
    qd.text((w // 2, int(h * 0.30)), "?", font=qfont, fill=(255, 255, 255, 40), anchor="mm")
    base.alpha_composite(qlayer)
    base = _vignette(base, w, h, strength=100)

    draw = ImageDraw.Draw(base)
    label_font = _font(int(w * 0.048))
    draw.text((w // 2, int(h * 0.12)), "YOUR TURN", font=label_font, fill=(255, 210, 90, 230), anchor="mm")
    return base.convert("RGB")


def build_background_clip(scene: dict, duration: float, video_w: int, video_h: int):
    kind = (scene.get("scene_kind") or "").lower()
    seed = (scene.get("scene_number", 1) or 1) * 71 + 11

    if kind == "stat":
        still = np.array(_stat_card_frame(video_w, video_h, seed))

        def make_frame(t):
            return still

        return VideoClip(make_frame, duration=duration)

    if kind == "quiz":
        still = np.array(_quiz_card_frame(video_w, video_h, seed))

        def make_frame(t):
            return still

        return VideoClip(make_frame, duration=duration)

    # The ordinary case: real footage or a photo-turned-clip, already
    # resolved by visual_fetcher.py. stock_footage already knows how to
    # load it, crop it to 9:16, apply a subtle Ken Burns zoom, and fall
    # back to a plain gradient if clip_path is missing — nothing about
    # that needs reimplementing here.
    return stock_footage.build_background_clip(scene, duration, video_w, video_h)
