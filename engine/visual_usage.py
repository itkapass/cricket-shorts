"""
visual_usage.py — cross-video memory of which specific photo/clip was
already used, so the SAME real asset doesn't show up in video after video.
=============================================================================

THE BUG THIS FIXES (reported directly: "for some clips like 'england',
repeated clip is shown in each video ... YouTube will detect this and
decide to make this a non-effort video")

Every visual-fetching provider in this project (visual_fetcher.py's Pexels
path, wikimedia_visuals.py, pixabay_visuals.py) only ever avoided repeating
an asset WITHIN one video's own scenes (see visual_fetcher.py's
`used_video_ids` / `used_keywords`). None of them remembered anything
BETWEEN videos. Wikimedia and Pixabay both deterministically return the
same top search result for the same query every single time (no
randomness, no memory — `candidates[0]` / `hits[0]`), so two completely
unrelated videos that both happen to search for something like "England
cricket team celebrating" get the exact literal same photo, every time,
forever. Pexels has its own version of the same problem via
visual_fetcher.py's permanent on-disk clip cache, keyed only by the exact
search text used.

THE FIX
Every real asset actually used in a rendered video is written here (one row
per scene that got a real photo/clip — "stat"/"quiz" designed cards and the
flat-gradient fallback are not assets and are never recorded) right after
rendering — see orchestrator.py's `_record_visual_usage`. Before the NEXT
video fetches its visuals, the last few weeks of identifiers are loaded
once per video and threaded through as an extra exclusion set alongside
each provider's own within-video dedup, so a provider that would otherwise
hand back the same top result instead moves on to its next candidate (or,
for the rare case where every candidate from every provider is excluded,
the next provider in the existing fallback chain).

This never blocks a video from rendering. If every provider's candidates
are genuinely exhausted, the existing fallback chain (a different provider,
eventually the flat gradient) still applies exactly as if this module did
not exist — a little visual repetition is a real but minor problem; an
empty background because a nice-to-have safety net broke would be worse.
"""
from datetime import datetime, timezone, timedelta

DEFAULT_LOOKBACK_DAYS = 21


def recent_identifiers(db, source: str = None, days: int = DEFAULT_LOOKBACK_DAYS) -> set:
    """Every identifier used by any recent video, as a set of strings,
    optionally filtered to one source ('pexels' | 'wikimedia' | 'pixabay').

    Returns an empty set — never raises — if the table doesn't exist yet
    (migration not applied), the database is unreachable, or any other
    error occurs. This is a variety improvement, not a correctness
    requirement a render should ever fail over.
    """
    if db is None:
        return set()
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        q = db.table("visual_usage").select("identifier").gte("used_at", since)
        if source:
            q = q.eq("source", source)
        rows = q.execute().data or []
        return {str(r["identifier"]) for r in rows if r.get("identifier")}
    except Exception as e:
        print(f"[visual_usage] ⚠ Could not load recent visual usage ({e}) — "
              f"continuing without cross-video exclusion this run (migration "
              f"008 may not be applied yet; see supabase/migrations/).")
        return set()


def load_all(db, days: int = DEFAULT_LOOKBACK_DAYS) -> dict:
    """Convenience: all three sources' exclusion sets in one round trip
    instead of three. Returns {"pexels": set(), "wikimedia": set(), "pixabay": set()}."""
    if db is None:
        return {"pexels": set(), "wikimedia": set(), "pixabay": set()}
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = (
            db.table("visual_usage").select("source, identifier")
            .gte("used_at", since).execute().data
        ) or []
        out = {"pexels": set(), "wikimedia": set(), "pixabay": set()}
        for r in rows:
            src = r.get("source")
            ident = r.get("identifier")
            if src in out and ident:
                out[src].add(str(ident))
        return out
    except Exception as e:
        print(f"[visual_usage] ⚠ Could not load recent visual usage ({e}) — "
              f"continuing without cross-video exclusion this run (migration "
              f"008 may not be applied yet; see supabase/migrations/).")
        return {"pexels": set(), "wikimedia": set(), "pixabay": set()}


def record_many(db, job_id: str, items: list) -> None:
    """Records real visual assets used by one video. `items` is a list of
    (source, identifier) tuples — callers should only include scenes that
    actually used a real, specific photo/clip (skip designed stat/quiz
    cards and the flat-gradient fallback, which are not "assets" in the
    sense this exists to track).

    Best-effort, never raises — a failure here must never take down a
    render that already succeeded.
    """
    if db is None or not items:
        return
    rows = [
        {"job_id": job_id, "source": str(source), "identifier": str(identifier)[:500]}
        for source, identifier in items if source and identifier
    ]
    if not rows:
        return
    try:
        db.table("visual_usage").insert(rows).execute()
    except Exception as e:
        print(f"[visual_usage] ⚠ Could not record visual usage for {job_id} ({e}) "
              f"— this video is unaffected, only future cross-video variety is.")
