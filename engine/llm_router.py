"""
llm_router.py — tries every configured free backup provider, in order,
before giving up.
==============================================================================

Gemini is always tried first (see script_generator.py) — this module only
runs once Gemini has genuinely failed with a per-day quota error. It tries
each configured backup in turn and returns the first one that succeeds:

  1. Groq            (engine/backup_provider.py)      — 1,000 req/day/model
  2. GitHub Models    (engine/github_models_provider.py) — modest but free,
                        and needs zero new signup for anyone already using
                        this project's own GitHub repo + Actions.

Either or both can be left unconfigured with no code changes needed
anywhere else — this function simply skips whichever ones aren't
available() and raises a clear, combined error only if NONE of them work.
"""
from engine import backup_provider
from engine import github_models_provider


# Ordered (name, module) pairs — add a new free backup by adding one line
# here, nowhere else.
_CHAIN = [
    ("groq", backup_provider),
    ("github_models", github_models_provider),
]


def any_backup_available() -> bool:
    return any(mod.available() for _, mod in _CHAIN)


def call(system_prompt: str, user_prompt: str, temperature: float = 0.9) -> tuple:
    """Tries each configured backup provider in order. Returns
    (text, provider_name) from the first one that succeeds.

    Raises RuntimeError, with every provider's own failure message
    included, only if every configured provider failed (or none are
    configured at all) — so the final error always says exactly what to
    fix, never just "no backup available" when one WAS configured and
    simply had its own problem today.
    """
    tried = []
    for name, mod in _CHAIN:
        if not mod.available():
            continue
        try:
            text = mod.call(system_prompt, user_prompt, temperature)
            return text, name
        except Exception as e:
            tried.append(f"{name}: {e}")
            print(f"[llm_router] ⚠ Backup provider '{name}' failed, trying the next one: {e}")

    if not tried:
        raise RuntimeError(
            "No backup provider is configured at all. See docs/13_BACKUP_AI_PROVIDER.md "
            "to add a free Groq key (~2 minutes) and/or enable GitHub Models "
            "(`models: read` in the workflow permissions — needs no new key)."
        )
    raise RuntimeError(
        "Every configured backup provider failed today:\n" + "\n".join(f"  - {t}" for t in tried)
    )
