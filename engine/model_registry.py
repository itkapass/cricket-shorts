"""
model_registry.py — never get 404'd by a deprecated model name again.
=====================================================================

THE PROBLEM THIS REMOVES
Google retires Gemini model names on roughly a 4-6 month cycle. This project
has already been bitten once: `gemini-1.5-flash` was hardcoded, went away, and
every generation failed with a 404 until someone noticed and edited the code.
Pinning a newer name just moves the failure a few months out.

THE FIX
Ask the API which models actually exist right now, then pick the best one that
supports what we need. Google's ListModels endpoint is free, unmetered, and
returns exactly this. The answer is cached to disk for a day so a batch of five
videos makes one discovery call, not five.

SELECTION POLICY
We want the cheapest model that is good enough, because this project's whole
premise is running at $0 on a free tier:
  1. Prefer "flash" variants — the free tier's quota is far more generous on
     Flash than Pro, and script writing does not need Pro.
  2. Among those, prefer the highest version number.
  3. Skip anything with an experimental/preview marker unless nothing stable
     exists, because preview models are the ones that vanish without notice.
  4. Skip non-text models (embedding, imagen, tts, vision-only).

ESCAPE HATCH
Setting GEMINI_MODEL in the environment pins a specific name and skips all of
this. That stays supported: when Google ships something new and good, you want
to be able to use it the same day without waiting for this heuristic to agree.
"""
import json
import os
import re
import time
import urllib.request

from engine.config import get

CACHE_PATH = os.path.join(os.path.expanduser("~"), ".cache", "shorts_studio_models.json")
CACHE_TTL_SECONDS = 24 * 60 * 60

# ─────────────────────────────────────────────────────────────────────────────
# BUGFIX — "Gemini never works, only Groq does"
#
# The old policy was "discover every model, pick the one with the highest
# version number". On a FREE API key that is actively harmful, and it is the
# reason this channel's videos were all tagged "written by groq/backup":
#
#   Google's newest Gemini models routinely ship with NO free-tier allowance
#   at all. A free key calling one gets 429 RESOURCE_EXHAUSTED on the very
#   first request of the day. api_budget.hard_stop() then reads that as "the
#   daily allowance is gone", writes spent = daily_budget into Supabase keyed
#   on the Pacific date, and Gemini is switched off for the WHOLE DAY — so
#   every one of the day's six generate runs quietly went to Groq instead.
#
#   Worse, the discovery result is cached for 24h, so the bad pick stuck.
#
# The new policy: prefer models KNOWN to have a real free tier, newest-first
# WITHIN that known-good set, and only fall back to version-number guessing
# if none of them are available. Pinning GEMINI_MODEL still overrides
# everything.
# ─────────────────────────────────────────────────────────────────────────────

# Models with a genuine, documented free-tier request allowance, best first.
# "Best" here means: generous free RPD, stable (not preview), good enough for
# script writing. Update this list when Google publishes a new FREE tier —
# not merely when it publishes a new model.
FREE_TIER_PREFERRED = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

# Last-resort ladder, used only if discovery itself fails (no network, API
# down). Free-tier-safe first on purpose — see the note above.
#
# BUGFIX: gemini-2.0-flash and gemini-2.0-flash-lite used to be here too.
# Google has since retired the whole 2.0 line (confirmed: live calls to
# gemini-2.0-flash now 404 with "model ... is no longer available", even
# though ListModels can keep advertising a retired name for a while after
# it stops actually working — see the 404 fallback in script_generator.py,
# which now treats that the same way a 429 is treated: drop the dead name
# and retry once with the next one, instead of dying outright).
FALLBACK_CHAIN = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

# Models that returned a hard quota error today. Kept in the same cache file
# as discovery so it survives between the day's separate workflow runs, and
# expires with it. This is what lets a 429 on ONE model try the NEXT model
# instead of writing off Gemini entirely for the day.
def _exhausted_today() -> list:
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            blob = json.load(f)
        if time.time() - blob.get("fetched_at", 0) < CACHE_TTL_SECONDS:
            return blob.get("exhausted") or []
    except Exception:
        pass
    return []


def mark_model_exhausted(name: str):
    """Records that `name` returned a quota error. Called by
    script_generator when Gemini 429s, BEFORE anything decides the whole day
    is over — a model with no free allowance at all must not be mistaken for
    'today's allowance is spent'."""
    if not name:
        return
    try:
        blob = {}
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                blob = json.load(f)
        except Exception:
            pass
        ex = set(blob.get("exhausted") or [])
        ex.add(name)
        blob["exhausted"] = sorted(ex)
        blob.setdefault("fetched_at", time.time())
        blob.setdefault("models", [])
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(blob, f)
        print(f"[model_registry] Noted that '{name}' is out of quota today; "
              f"the next call will try a different model before giving up on Gemini.")
    except Exception:
        pass

_PREVIEW_MARKERS = ("exp", "preview", "experimental", "thinking", "-tuning")
_NON_TEXT_MARKERS = ("embedding", "aqa", "imagen", "veo", "tts", "image-generation")


def _version_key(name: str) -> tuple:
    """Sorts model names by version number, newest first.

    'gemini-2.5-flash' -> (2, 5). Names without a parseable version sort last
    so they never beat a real versioned model.
    """
    m = re.search(r"gemini-(\d+)(?:\.(\d+))?", name)
    if not m:
        return (-1, -1)
    return (int(m.group(1)), int(m.group(2) or 0))


def _fetch_model_list(api_key: str) -> list:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}&pageSize=200"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    out = []
    for m in data.get("models", []):
        name = (m.get("name") or "").replace("models/", "")
        methods = m.get("supportedGenerationMethods") or []
        if "generateContent" not in methods:
            continue
        out.append(name)
    return out


def _read_cache():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            blob = json.load(f)
        if time.time() - blob.get("fetched_at", 0) < CACHE_TTL_SECONDS:
            return blob.get("models") or []
    except Exception:
        pass
    return None


def _write_cache(models):
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": time.time(), "models": models}, f)
    except Exception:
        pass  # cache is an optimisation; never let it break a run


def choose_text_model(api_key: str = None, force_refresh: bool = False) -> str:
    """Returns the model name to use for script generation."""
    pinned = get("GEMINI_MODEL")
    if pinned:
        print(f"[model_registry] Using pinned GEMINI_MODEL={pinned}")
        return pinned

    api_key = api_key or get("GEMINI_API_KEY")
    models = None if force_refresh else _read_cache()

    if models is None and api_key:
        try:
            models = _fetch_model_list(api_key)
            _write_cache(models)
            print(f"[model_registry] Discovered {len(models)} available models from Google.")
        except Exception as e:
            print(f"[model_registry] ⚠ Could not list models ({e}); falling back to the built-in chain.")
            models = None

    if not models:
        return FALLBACK_CHAIN[0]

    def usable(n, allow_preview):
        low = n.lower()
        if any(x in low for x in _NON_TEXT_MARKERS):
            return False
        if not allow_preview and any(x in low for x in _PREVIEW_MARKERS):
            return False
        return True

    skip = set(_exhausted_today())
    if skip:
        print(f"[model_registry] Skipping model(s) already out of quota today: {sorted(skip)}")

    # (1) FIRST CHOICE: a model we KNOW has a real free tier. This is the
    # whole bugfix — see FREE_TIER_PREFERRED's note. Order is by our own
    # preference list, NOT by version number.
    available = set(models)
    for name in FREE_TIER_PREFERRED:
        if name in available and name not in skip:
            print(f"[model_registry] Selected model: {name} (known free tier)")
            return name

    # (2) SECOND CHOICE: a "-latest" Flash alias. It is a moving pointer, so
    # it survives the next deprecation on its own, but it can point at a
    # paid-only model — hence second, not first.
    for allow_preview in (False, True):
        flash = [m for m in models
                 if "flash" in m.lower() and usable(m, allow_preview) and m not in skip]
        if not flash:
            continue
        latest = [m for m in flash if m.endswith("-latest")]
        if latest:
            best = sorted(latest)[0]
            print(f"[model_registry] No known-free model available; selected alias: {best}")
            return best
        # (3) LAST CHOICE within Flash: version-number guessing, OLDEST
        # first. An older Flash model is far likelier to have a free tier
        # than a brand-new one, which is the opposite of the old policy.
        best = sorted(flash, key=_version_key)[0]
        print(f"[model_registry] Falling back to the oldest available Flash model, "
              f"which is the most likely to still have a free tier: {best}")
        return best

    any_text = [m for m in models if usable(m, True) and m not in skip]
    if any_text:
        best = sorted(any_text, key=_version_key)[0]
        print(f"[model_registry] No Flash model available; selected: {best}")
        return best

    return FALLBACK_CHAIN[0]


def next_fallback(current: str) -> str | None:
    """If `current` just failed with a 404, returns the next name to try."""
    chain = [m for m in FALLBACK_CHAIN if m != current]
    return chain[0] if chain else None
