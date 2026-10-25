"""
github_models_provider.py — a THIRD free, independent script-writing
fallback, for the day Gemini's quota AND Groq's are both gone.
==============================================================================

WHY THIS EXISTS
engine/backup_provider.py already adds Groq as a fallback when Gemini's
free tier is spent for the day. This adds one more independent option
behind that: GitHub Models (models.github.ai), which is genuinely free and
needs literally ZERO new signup for anyone already using this project —
every GitHub account (the same one already hosting this repo and running
the Actions workflows) can call it with the same GITHUB_TOKEN GitHub
Actions already provides automatically, plus one line of extra permission
in the workflow file (`permissions: models: read`).

WHEN THIS IS ACTUALLY REACHED
Gemini is tried first, always. Groq is tried second, always. This is only
reached if BOTH have already failed with a genuine daily-quota error —
a third-choice safety net, not a first-choice provider. On an ordinary
day, for a channel posting a handful of videos, this file never runs at
all.

FREE TIER, HONESTLY
GitHub Models' free (non-Copilot-subscriber) rate limits are modest —
roughly 50-150 requests per day depending on the model's tier, refreshed
daily — which is exactly why it sits third in the chain rather than first:
it is a safety net for "both of my other two free options ran dry today",
not a primary workhorse.

GETTING ACCESS (genuinely free, ~1 minute, already-owned account)
  1. In the repo's GitHub Actions workflow YAML, add under `permissions:`:
         models: read
  2. That's it — the workflow's own automatic `GITHUB_TOKEN` secret can now
     call GitHub Models. No new key to create or store.
  For a local test outside Actions, a personal access token with the
  `models: read` scope works the same way — set it as GITHUB_MODELS_TOKEN.

THE SAME HONESTY RULE AS EVERY OTHER FALLBACK IN THIS PROJECT
Every response is tagged with the provider that actually served it
("github_models") so nothing generated this way is ever mistaken for a
Gemini or Groq result anywhere it's displayed, logged, or saved.
"""
import os
import requests

GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference/chat/completions"

# A "low tier" model (higher daily request allowance on the free plan) is
# the right default here — this file is a safety net reached only when two
# other providers already failed today, so favouring request HEADROOM over
# raw capability is the correct trade. Override with GITHUB_MODELS_MODEL.
DEFAULT_MODEL = "openai/gpt-4.1-mini"

TIMEOUT_SECONDS = 60
PROVIDER_NAME = "github_models"


def _token() -> str | None:
    # GITHUB_TOKEN is what GitHub Actions injects automatically for every
    # workflow run once `permissions: models: read` is set — no secret to
    # create. GITHUB_MODELS_TOKEN is the explicit override for local runs
    # or a personal access token, checked first so it always wins if set.
    return os.environ.get("GITHUB_MODELS_TOKEN") or os.environ.get("GITHUB_TOKEN")


def available() -> bool:
    return bool(_token())


def call(system_prompt: str, user_prompt: str, temperature: float = 0.9) -> str:
    """Sends one chat completion request to GitHub Models and returns the
    raw text. Same (text) contract as backup_provider.call() — raises on
    any failure; never returns a silent empty string."""
    token = _token()
    if not token:
        raise RuntimeError(
            "No GitHub Models token available. In GitHub Actions, add "
            "`models: read` under `permissions:` in the workflow YAML — the "
            "automatic GITHUB_TOKEN then works with no new secret. For a "
            "local run, set GITHUB_MODELS_TOKEN to a personal access token "
            "with the `models: read` scope."
        )

    model = os.environ.get("GITHUB_MODELS_MODEL", DEFAULT_MODEL)

    try:
        resp = requests.post(
            GITHUB_MODELS_ENDPOINT,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt
                     + "\n\nRespond with ONLY the JSON. No markdown fences, no commentary."},
                ],
                "temperature": temperature,
            },
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Could not reach GitHub Models (network error): {e}") from e

    if resp.status_code == 401 or resp.status_code == 403:
        raise RuntimeError(
            f"GitHub Models rejected the token ({resp.status_code}). Check that the "
            f"workflow has `models: read` under `permissions:`, or that "
            f"GITHUB_MODELS_TOKEN has the `models: read` scope."
        )
    if resp.status_code == 429:
        raise RuntimeError(
            f"GitHub Models daily/rate limit reached: {resp.text[:200]}"
        )
    if not resp.ok:
        raise RuntimeError(f"GitHub Models returned {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected response shape from GitHub Models: {data}") from e
