"""
visual_kenburns.py — turns a still photo into a short 9:16 video clip.
=======================================================================

WHY THIS EXISTS
This channel leans much harder on real photos than the original project
did: a 1983 World Cup team photo, a portrait of a retired player, a
stadium exterior — Pexels' stock-footage library has almost none of this,
but Wikimedia Commons and Pixabay have real, reliably-licensed photos for
exactly this kind of thing. Turning a photo into a moving clip is what the
user asked for directly: "a photo drag from left to right or zoomed in and
out... will make a video if the background voice speaks."

Every provider in visual_fetcher.py's chain (Wikimedia, Pixabay, the AI
image fallback) calls this ONE function so the motion styling and output
contract are identical regardless of where the photo came from. The output
is a plain .mp4 at the exact target size, so everything downstream
(stock_footage.py's own loader, which sports_visual.py reuses) treats it
exactly like a downloaded Pexels clip — no separate code path needed
anywhere else in the render pipeline.

FOUR MOTIONS, PICKED DETERMINISTICALLY PER SCENE
zoom-in, zoom-out, pan-left-to-right, pan-right-to-left — chosen from the
scene number so the SAME scene always gets the same motion on a re-render,
but different scenes in one video get visibly different treatment (the
"drag" vs "zoom" variety the user asked for) instead of every photo in a
video doing the identical move.
"""
import os
import subprocess

# Output spec matches video_compositor.VIDEO_WIDTH/HEIGHT exactly. Kept as
# plain constants here (rather than importing video_compositor) to avoid a
# circular import — this module is used by visual_fetcher, which runs
# before video_compositor is ever touched.
OUT_W, OUT_H = 1080, 1920

MOTIONS = ("zoom_in", "zoom_out", "pan_left", "pan_right")


def _motion_for_scene(scene_number: int, seed: int = 0) -> str:
    return MOTIONS[(int(scene_number or 1) + seed) % len(MOTIONS)]


def _zoompan_filter(motion: str, hold_seconds: float, fps: int = 30) -> str:
    """Builds the ffmpeg zoompan expression for one of the four motions.

    The source is pre-scaled up (oversize_factor) and cropped to a fixed
    working canvas before zoompan runs — zoompan reads its input frame by
    frame, so feeding it a huge source image directly is slow; scaling once
    up front keeps the whole conversion fast enough to run per-scene inside
    a render job on a free CI runner.
    """
    frames = max(int(hold_seconds * fps), fps)

    if motion == "zoom_in":
        z = f"min(zoom+0.0018,1.18)"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == "zoom_out":
        z = f"if(eq(on,1),1.18,max(zoom-0.0018,1.0))"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == "pan_left":
        # Fixed zoom, camera window slides from the right edge to the left.
        z = "1.16"
        x = f"if(eq(on,1),iw-iw/zoom,max(x-{max(1, int(1400 / frames))},0))"
        y = "ih/2-(ih/zoom/2)"
    else:  # pan_right
        z = "1.16"
        x = f"if(eq(on,1),0,min(x+{max(1, int(1400 / frames))},iw-iw/zoom))"
        y = "ih/2-(ih/zoom/2)"

    return (
        f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={OUT_W}x{OUT_H}:fps={fps}"
    )


def image_to_clip(image_path: str, output_mp4_path: str, hold_seconds: float,
                  scene_number: int = 1, motion_seed: int = 0) -> bool:
    """Converts one still image into a `hold_seconds`-long 1080x1920 .mp4
    with a Ken Burns pan or zoom. Returns True on success, False on any
    failure (never raises — every caller in the provider chain treats a
    failed conversion as 'try the next source', never as a hard error).
    """
    if not image_path or not os.path.exists(image_path):
        return False

    motion = _motion_for_scene(scene_number, motion_seed)
    hold = max(float(hold_seconds) + 0.6, 1.5)
    zoompan = _zoompan_filter(motion, hold)

    # Oversize the source first (scale to cover a canvas somewhat larger
    # than the output, then crop to exactly that canvas) so zoompan always
    # has real room to pan/zoom into regardless of the source photo's own
    # aspect ratio — a portrait player photo and a wide stadium photo both
    # need to end up filling a 9:16 frame with no letterboxing.
    oversize_w, oversize_h = int(OUT_W * 2.0), int(OUT_H * 2.0)
    vf = (
        f"scale={oversize_w}:{oversize_h}:force_original_aspect_ratio=increase,"
        f"crop={oversize_w}:{oversize_h},"
        f"{zoompan},format=yuv420p"
    )

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-t", str(hold),
             "-vf", vf, "-r", "30", "-pix_fmt", "yuv420p", output_mp4_path],
            check=True, capture_output=True, timeout=45,
        )
        return os.path.exists(output_mp4_path) and os.path.getsize(output_mp4_path) > 2000
    except Exception as e:
        print(f"[visual_kenburns] ⚠ Could not convert {image_path} to video ({e}).")
        return False
