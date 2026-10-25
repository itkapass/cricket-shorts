"""
openrouter_provider.py — the last link in the free fallback chain.
=============================================================================

WHERE THIS SITS
  Gemini -> Groq -> GitHub Models -> HuggingFace -> OpenRouter (this file)

By the time a call reaches here, three or four other free providers have
already refused it. That makes this the right place for a provider whose free
tier is real but modest: it is almost never used, and when it IS used it is
the difference between a video and a red error card.

WHY OPENROUTER SPECIFICALLY
It is a router, not a model host — one API key reaches dozens of models from
different labs, several of which carry a `:free` suffix and cost nothing.
That means this single link in the chain is itself diversified: if one free
model is saturated, another usually is not, and switching is a string change
rather than a new signup.

THE FREE TIER, HONESTLY
Models tagged `:free` are free to call but rate-limited per day, and which
models carry the tag changes over time. The list below is ordered best-first
and every entry is tried in turn, so one retired model name cannot take this
provider offline — the failure mode that DEFAULT_GROQ_MODEL's comment in
backup_provider.py describes. Set OPENROUTER_MODEL to pin one and skip the
list entirely.

INTERFACE
Matches engine/backup_provider.py exactly — available() and
call(system_prompt, user_prompt, temperature) -> str — so adding it to
llm_router._CHAIN is a one-line change there and needs nothing else anywhere.
"""
import json
import os
import urllib.error
import urllib.request

from engine.config import get

API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Tried in order. All currently carry a free tier; the list is defensive on
# purpose — see the module docstring.
FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "mistralai/mistral-small-3.2-24b-instruct:free",
]

TIMEOUT_SECONDS = 120


def available() -> bool:
    return bool(get("OPENROUTER_API_KEY"))


def call(system_prompt: str, user_prompt: str, temperature: float = 0.9) -> str:
    """Tries each free model in turn; returns the first successful answer.

    Raises RuntimeError with every model's own failure included only if all
    of them fail — so the error always names what to fix rather than just
    saying the provider did not work.
    """
    api_key = get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Get a free key at "
            "https://openrouter.ai/keys (no card needed) and add it as a "
            "GitHub secret — see docs/13_BACKUP_AI_PROVIDER.md."
        )

    pinned = os.environ.get("OPENROUTER_MODEL")
    models = [pinned] if pinned else list(FREE_MODELS)

    failures = []
    for model in models:
        try:
            return _call_model(model, system_prompt, user_prompt, temperature, api_key)
        except Exception as e:
            failures.append(f"{model}: {e}")
            print(f"[openrouter] ⚠ '{model}' failed ({e}) — trying the next free model.")

    raise RuntimeError(
        "Every free OpenRouter model failed:\n"
        + "\n".join(f"  - {f}" for f in failures)
        + "\nFree models are rate-limited per day; this usually clears on its own. "
          "Set OPENROUTER_MODEL to pin a specific model if you have a preference."
    )


def _call_model(model: str, system_prompt: str, user_prompt: str,
                temperature: float, api_key: str) -> str:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(temperature),
        # Every caller in this project parses the answer as JSON, so ask for
        # JSON explicitly rather than hoping the prompt alone is enough.
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # OpenRouter asks callers to identify themselves; these are
            # optional but improve free-tier treatment.
            "HTTP-Referer": "https://github.com/",
            "X-Title": "Shorts Studio",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:400]
        except Exception:
            pass
        if e.code == 429:
            raise RuntimeError(f"rate-limited (429). {detail}") from e
        if e.code in (401, 403):
            raise RuntimeError(
                f"key rejected ({e.code}). Check OPENROUTER_API_KEY at "
                f"https://openrouter.ai/keys. {detail}"
            ) from e
        if e.code == 404:
            raise RuntimeError(
                f"model '{model}' no longer exists (404). The free model list "
                f"changes; set OPENROUTER_MODEL to a current one from "
                f"https://openrouter.ai/models?q=free. {detail}"
            ) from e
        raise RuntimeError(f"HTTP {e.code}. {detail}") from e

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"no answer in the response: {str(data)[:300]}")
    text = (choices[0].get("message") or {}).get("content") or ""
    if not text.strip():
        raise RuntimeError("answered with empty content")
    return text
