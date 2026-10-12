"""
quality_gates.py — automated QC on the rendered file, before a human sees it.
=============================================================================

WHY
You said it yourself: a human cannot judge a video from its storyboard, so
review has to happen on the finished render. But reviewing every render by hand
is the bottleneck that kills daily publishing. The answer is not to skip review
(that is what auto-approve does, and it is how channels get flagged) — it is to
make sure the only videos that reach you are ones worth your time.

These gates catch the failures that are mechanical and objective. They do NOT
try to judge whether a video is funny or interesting. That is the part a human
is actually needed for, and pretending an automated check can do it would be
the worst version of this feature.

WHAT EACH GATE CATCHES, AND WHY IT EXISTS
  black_frames    — the exact bug found in the earlier build: a ~2 second cut
                    to solid black mid-sentence. It was invisible in code and
                    only found by watching output frame-by-frame. Now checked
                    on every render, automatically, forever.
  audio_silence   — a render where TTS failed produces a perfect-looking video
                    with no voice. Publishing that is worse than publishing
                    nothing.
  audio_level     — too quiet gets skipped, too loud clips. YouTube normalises
                    to about -14 LUFS, so anything wildly off gets squashed.
  duration        — Shorts must be under 3 minutes; under ~15s barely gets
                    distribution. Both ends are hard failures worth catching.
  caption_overflow— captions running off the frame edge, checked from the
                    storyboard rather than pixels.
  frozen_video    — every frame identical means the render loop broke and you
                    have a still image with audio.
  resolution      — anything not 1080x1920 will be letterboxed by YouTube.

VERDICTS
  pass    — send to human review
  warn    — send to human review, flagged, with the reason shown in the queue
  reject  — do not show a human, do not publish, log why
"""
import json
import os
import subprocess

import numpy as np

# Thresholds. Deliberately module-level constants so they are tunable in one
# place without hunting through the logic.
BLACK_FRAME_MAX_RUN_SECONDS = 0.5     # a longer solid-black run is a defect
BLACK_LUMA_THRESHOLD = 12             # 0-255; below this counts as "black"
MIN_MEAN_VOLUME_DB = -35.0            # quieter than this and nobody hears it
MAX_MEAN_VOLUME_DB = -12.0            # louder than this and it clips
MIN_DURATION_SECONDS = 12.0
MAX_DURATION_SECONDS = 175.0          # YouTube Shorts cap is 180s; leave margin
EXPECTED_SIZE = (1080, 1920)
SAMPLE_FPS = 4                        # frames per second sampled for analysis


def _ffprobe_json(path: str) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, text=True, timeout=120,
    )
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {out.stderr.strip()[:300]}")
    return json.loads(out.stdout)


def _mean_volume_db(path: str):
    """Returns (mean_db, max_db) via ffmpeg's volumedetect filter."""
    out = subprocess.run(
        ["ffmpeg", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, timeout=180,
    )
    mean = peak = None
    for line in out.stderr.splitlines():
        if "mean_volume:" in line:
            mean = float(line.split("mean_volume:")[1].strip().split()[0])
        elif "max_volume:" in line:
            peak = float(line.split("max_volume:")[1].strip().split()[0])
    return mean, peak


def _sample_luma(path: str, fps: int = SAMPLE_FPS):
    """Returns a list of mean-brightness values, one per sampled frame.

    Decodes to tiny 32x32 greyscale frames rather than full 1080x1920. A full
    decode of a 45-second video takes tens of seconds and tells us nothing
    extra: average brightness survives downscaling perfectly, and this runs in
    well under a second.
    """
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path,
         "-vf", f"fps={fps},scale=32:32", "-pix_fmt", "gray",
         "-f", "rawvideo", "-"],
        capture_output=True, timeout=240,
    )
    raw = proc.stdout
    frame_size = 32 * 32
    n = len(raw) // frame_size
    if n == 0:
        return []
    arr = np.frombuffer(raw[: n * frame_size], dtype=np.uint8).reshape(n, frame_size)
    return arr.mean(axis=1).tolist()


def run_gates(video_path: str, storyboard: dict = None, expect_audio: bool = True) -> dict:
    """Runs every gate. Returns a verdict dict.

    Never raises: if the checks themselves cannot run (ffmpeg missing, corrupt
    file), the verdict is "warn" and the video still reaches a human. A broken
    checker must not silently discard good videos.
    """
    result = {"verdict": "pass", "checks": [], "failures": [], "warnings": []}

    def add(name, ok, level, detail=""):
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            if level == "reject":
                result["failures"].append(f"{name}: {detail}")
            else:
                result["warnings"].append(f"{name}: {detail}")

    if not os.path.exists(video_path):
        result["verdict"] = "reject"
        result["failures"].append("file_missing: rendered file does not exist")
        return result

    try:
        meta = _ffprobe_json(video_path)
    except Exception as e:
        result["verdict"] = "warn"
        result["warnings"].append(f"probe_failed: {e}")
        return result

    vstream = next((s for s in meta.get("streams", []) if s.get("codec_type") == "video"), None)
    astream = next((s for s in meta.get("streams", []) if s.get("codec_type") == "audio"), None)
    duration = float(meta.get("format", {}).get("duration") or 0)

    # ── Duration ─────────────────────────────────────────────────────────────
    add("duration", MIN_DURATION_SECONDS <= duration <= MAX_DURATION_SECONDS, "reject",
        f"{duration:.1f}s (allowed {MIN_DURATION_SECONDS:.0f}-{MAX_DURATION_SECONDS:.0f}s)")

    # ── Resolution ───────────────────────────────────────────────────────────
    if vstream:
        size = (int(vstream.get("width", 0)), int(vstream.get("height", 0)))
        add("resolution", size == EXPECTED_SIZE, "warn", f"{size[0]}x{size[1]}, expected 1080x1920")
    else:
        add("video_stream", False, "reject", "no video stream found")

    # ── Audio present ────────────────────────────────────────────────────────
    if expect_audio:
        add("audio_stream", astream is not None, "reject", "no audio stream — the voiceover did not render")

    # ── Audio level ──────────────────────────────────────────────────────────
    if astream:
        try:
            mean_db, peak_db = _mean_volume_db(video_path)
            if mean_db is None:
                add("audio_level", False, "warn", "could not measure volume")
            else:
                add("audio_level", MIN_MEAN_VOLUME_DB <= mean_db <= MAX_MEAN_VOLUME_DB, "warn",
                    f"mean {mean_db:.1f} dB (want {MIN_MEAN_VOLUME_DB:.0f} to {MAX_MEAN_VOLUME_DB:.0f})")
                # A mean at or near digital silence means TTS produced nothing.
                add("audio_silence", mean_db > -60.0, "reject", f"effectively silent ({mean_db:.1f} dB)")
        except Exception as e:
            add("audio_level", False, "warn", f"check failed: {e}")

    # ── Black frames and frozen video ────────────────────────────────────────
    try:
        luma = _sample_luma(video_path)
        if luma:
            max_run, run = 0, 0
            for v in luma:
                run = run + 1 if v < BLACK_LUMA_THRESHOLD else 0
                max_run = max(max_run, run)
            black_seconds = max_run / SAMPLE_FPS
            add("black_frames", black_seconds <= BLACK_FRAME_MAX_RUN_SECONDS, "reject",
                f"{black_seconds:.1f}s of solid black (max allowed {BLACK_FRAME_MAX_RUN_SECONDS}s)")

            spread = float(np.std(luma))
            add("frozen_video", spread > 0.35, "warn",
                f"brightness barely changes (σ={spread:.2f}) — the video may be a still image")
        else:
            add("black_frames", False, "warn", "could not sample frames")
    except Exception as e:
        add("black_frames", False, "warn", f"check failed: {e}")

    # ── Caption overflow (from the storyboard, not pixels) ───────────────────
    if storyboard:
        longest = max(
            (len(s.get("voice_text", "")) for s in storyboard.get("scenes", [])),
            default=0,
        )
        add("caption_length", longest <= 240, "warn",
            f"longest scene is {longest} characters — may overflow on screen")

        # ── Caption timing precision ─────────────────────────────────────────
        # edge-tts reports the exact moment it spoke each word (ground truth).
        # Its two fallbacks (Piper, gTTS) do not — they estimate each word's
        # timing proportionally from syllable count, anchored to the real
        # total duration but with no way to know where an engine actually
        # paused for a breath or a comma. That estimate can visibly drift
        # from the real audio on longer sentences, which is exactly what
        # reads as "the captions feel out of sync" without any single frame
        # looking obviously broken.
        #
        # This used to fail completely silently: the video still rendered,
        # still passed every other gate, and the ONLY trace that it used
        # degraded timing was a console log line in a run nobody was
        # watching. Flagging it here means a human reviewing the queue sees
        # it before approving, instead of finding out from comments after
        # it is already public.
        voice_engine = storyboard.get("_voice_engine")
        if voice_engine and voice_engine != "edge-tts":
            add("caption_timing", False, "warn",
                f"voiced by '{voice_engine}', not edge-tts — captions use ESTIMATED "
                f"timing and may drift from the audio, especially on longer lines. "
                f"Watch this one before approving.")

        # ── Closing CTA present ─────────────────────────────────────────────
        # script_generator.py's prompt now REQUIRES the final scene to end on
        # a question/follow/share/subscribe line (see RULES item 4), but a
        # prompt instruction is a request, not a guarantee — Gemini (or a
        # backup provider) can still skip it, same as it skipped it before
        # this rule existed. This is the mechanical back-check: if auto
        # approve is ever going to be trusted, it has to depend on checks
        # like this, not on faith that the model followed instructions.
        scenes = storyboard.get("scenes") or []
        if scenes:
            last_voice_text = (scenes[-1].get("voice_text") or "").strip().lower()
            cta_markers = ("?", "follow", "subscribe", "comment", "share", "send this",
                           "part 2", "next time", "miss it", "don't miss")
            has_cta = any(m in last_voice_text for m in cta_markers)
            add("closing_cta", has_cta, "warn",
                "the final scene doesn't end with a question, follow/subscribe/share "
                "line, or part-2 tease — this video may just stop on the fact with no "
                "reason given to keep engaging. Worth a look before approving.")

        # ── Visual keywords are sport-locked ────────────────────────────────
        # THE CONFIRMED BUG THIS CATCHES: a cricket video that cut to baseball
        # stock footage because its visual_keyword was a bare action phrase
        # ("claims a relay") with no sport name in it, so stock search
        # matched the wrong sport. The prompt now requires the sport's name
        # (or a named player/ground/sport-unique term) in every
        # visual_keyword — this is the mechanical back-check for that rule,
        # same reasoning as closing_cta above: a heuristic, not a guarantee
        # (it cannot watch the actual footage), so it warns a human to look
        # rather than silently rejecting a video that may well be fine.
        SPORT_UNIQUE_TERMS = (
            "cricket", "wicket", "stump", "lbw", "googly", "crease", "over", "bowler",
            "batsman", "batter", "innings", "yorker", "spinner", "boundary", "powerplay",
            "lanka", "football", "soccer", "basketball", "nba", "tennis", "golf", "rugby",
            "hockey", "baseball", "volleyball", "badminton", "f1", "formula",
        )
        suspect_keywords = []
        for sc in scenes:
            kw = (sc.get("visual_keyword") or "").strip()
            if not kw:
                continue
            kw_lower = kw.lower()
            has_sport_term = any(term in kw_lower for term in SPORT_UNIQUE_TERMS)
            has_proper_noun = any(w[:1].isupper() for w in kw.split()[1:])  # skip first word (sentence-case)
            if not has_sport_term and not has_proper_noun:
                suspect_keywords.append(kw)
        if suspect_keywords:
            add("visual_sport_lock", False, "warn",
                f"{len(suspect_keywords)} scene(s) have a visual_keyword with no sport "
                f"name or named subject — stock search may return the wrong sport "
                f"entirely: {suspect_keywords[:3]}")

    if result["failures"]:
        result["verdict"] = "reject"
    elif result["warnings"]:
        result["verdict"] = "warn"

    return result


def summarize(result: dict) -> str:
    if result["verdict"] == "pass":
        return "All quality checks passed."
    parts = []
    if result["failures"]:
        parts.append("Rejected: " + "; ".join(result["failures"]))
    if result["warnings"]:
        parts.append("Warnings: " + "; ".join(result["warnings"]))
    return " | ".join(parts)
