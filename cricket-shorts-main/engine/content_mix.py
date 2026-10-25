"""
content_mix.py — the daily content-mix strategy: 85/15 sport split, and a
"predicted winners + variety" cadence, run to run.
=============================================================================

TWO RULES THIS ENFORCES, BOTH ASKED FOR EXPLICITLY

1. THE 85/15 SPORT SPLIT
   "cricket... (85%), balance 15% is based on other sports and players whom
   have achieved in that and are currently in the achieving track." This
   module reads each topic's `sport` field ("cricket" | "other_sport" — see
   sports_catalog.py and topic_synthesizer.py, both of which tag every topic
   this way) and orders/selects each day's batch to land close to that ratio
   — not by chance, and not by whatever a random shuffle happens to produce.

2. THE "FAIR" CADENCE — WINNERS AND VARIETY, NOT ALL ONE OR THE OTHER
   "if per day video posting count is 4 (2 videos should be that more
   engaging, highly reachable ones and the other 2 should be based on other
   topics or contents)... this way the videos will be fair." Half of each
   day's batch (configurable via the `content_mix_winner_ratio` setting,
   default 0.5) is drawn from topics predicted to perform well; the rest is
   genuine variety, so the channel never becomes "only ever posts the
   statistically safest format" and never becomes "no strategy at all,
   fully random" either.

WHERE "PREDICTED TO PERFORM WELL" ACTUALLY COMES FROM
This module does not invent that score itself — it calls
engine.performance_loop.effective_engagement_tier(), which already resolves,
in priority order: real measured performance of the topic's OWN published
video, real measured performance of OTHER topics in the same category, and
only then falls back to sports_catalog.py's editorial "high"/"standard"
starting guess. So the "winner" half of the day's mix gets smarter over time
automatically, on its own, as real view/like/comment data accumulates — this
module only has to ask the one function that already knows, not reimplement
the guess.

WHY THIS IS A PURE ORDERING FUNCTION, NOT A DATABASE QUERY
orchestrator.py already loads the day's active, unused topic pool from the
database (see run_generation_pipeline) — this module just takes that list
and returns it REORDERED so the built-in `topics[i % len(topics)]` indexing
already used there naturally walks it in the right mix, ratio and cadence.
Nothing here talks to Supabase directly except the one settings read for the
two ratios, which degrades to sensible defaults if it fails.
"""
import random

DEFAULT_CRICKET_PCT = 85
DEFAULT_WINNER_RATIO = 0.5


def _setting_float(db, key: str, default: float) -> float:
    if db is None:
        return default
    try:
        rows = db.table("settings").select("value").eq("key", key).execute().data or []
        return float(rows[0]["value"]) if rows and rows[0].get("value") not in (None, "") else default
    except Exception:
        return default


def _sport_of(topic: dict) -> str:
    # A topic seeded before this feature existed, or inserted by hand with no
    # sport tag, defaults to "cricket" — the channel's overwhelming majority
    # case, and the safer default than silently treating an untagged topic as
    # the minority 15% slice.
    s = (topic.get("sport") or "cricket").strip().lower()
    return s if s in ("cricket", "other_sport") else "cricket"


def _is_winner(topic: dict, db=None) -> bool:
    from engine import performance_loop
    return performance_loop.effective_engagement_tier(topic, db=db) == "high"


def _split_winners(pool: list, db=None) -> tuple:
    """Returns (winners, variety) — two lists partitioning `pool` by
    effective_engagement_tier(), each internally shuffled so repeated runs on
    the same day don't always surface the identical topic first."""
    winners, variety = [], []
    for t in pool:
        (winners if _is_winner(t, db) else variety).append(t)
    random.shuffle(winners)
    random.shuffle(variety)
    return winners, variety


def _take_mixed(winners: list, variety: list, count: int, winner_ratio: float) -> list:
    """Pulls `count` topics from (winners, variety) at roughly `winner_ratio`,
    falling back to whichever pool has material when the other runs short —
    a day should never come up short on videos just because, say, every
    'high' topic in a category happened to be used up already."""
    n_winners = round(count * winner_ratio)
    n_variety = count - n_winners

    out = list(winners[:n_winners])
    out += variety[:n_variety]

    # Short on one side (e.g. not enough "high" topics today) — top up from
    # whichever pool still has material rather than under-filling the day.
    if len(out) < count:
        used_ids = {id(t) for t in out}
        remainder = [t for t in (winners + variety) if id(t) not in used_ids]
        out += remainder[: count - len(out)]
    return out[:count]


def _interleave(a: list, b: list) -> list:
    """Alternates two lists (A B A B A B...), appending whichever runs out
    first's remainder at the end. Used so a day's winners and variety videos
    end up spread across the day's publish schedule instead of clumped —
    channels.py's min_gap_minutes() already spaces uploads across the day by
    time, this just makes sure WHAT gets spaced out is actually a good mix,
    not 'all the safe bets this morning, all the filler this evening'."""
    out, i, j = [], 0, 0
    while i < len(a) or j < len(b):
        if i < len(a):
            out.append(a[i]); i += 1
        if j < len(b):
            out.append(b[j]); j += 1
    return out


def order_daily_batch(topics: list, daily_count: int, db=None) -> list:
    """Reorders/selects from `topics` (the day's active, unused pool already
    loaded by orchestrator.py) into the 85/15 sport split and winner/variety
    cadence described above. Returns a list of AT MOST `len(topics)` topics —
    never more, since this only reorders what's actually available; the
    caller's own `topics[i % len(topics)]` indexing handles the case where
    daily_count exceeds the pool size, exactly as it already did before this
    function existed.

    Never raises: on any settings-read or scoring problem, degrades to the
    input list, lightly shuffled — the 85/15 mix and cadence are a real
    strategy improvement, not a correctness requirement a generation run
    should ever fail over.
    """
    if not topics:
        return []

    try:
        cricket_pct = _setting_float(db, "content_mix_cricket_pct", DEFAULT_CRICKET_PCT) / 100.0
        cricket_pct = min(1.0, max(0.0, cricket_pct))
        winner_ratio = _setting_float(db, "content_mix_winner_ratio", DEFAULT_WINNER_RATIO)
        winner_ratio = min(1.0, max(0.0, winner_ratio))

        cricket_pool = [t for t in topics if _sport_of(t) == "cricket"]
        other_pool = [t for t in topics if _sport_of(t) == "other_sport"]

        count = min(daily_count, len(topics)) if daily_count else len(topics)
        if count <= 0:
            count = len(topics)

        if not other_pool:
            n_cricket, n_other = count, 0
        elif not cricket_pool:
            n_cricket, n_other = 0, count
        else:
            n_cricket = round(count * cricket_pct)
            n_other = count - n_cricket

        cricket_winners, cricket_variety = _split_winners(cricket_pool, db)
        other_winners, other_variety = _split_winners(other_pool, db)

        cricket_batch = _take_mixed(cricket_winners, cricket_variety, n_cricket, winner_ratio)
        other_batch = _take_mixed(other_winners, other_variety, n_other, winner_ratio)

        ordered = _interleave(cricket_batch, other_batch)

        # Anything left over (pool bigger than today's count) is appended at
        # the end, shuffled — still usable if the caller's daily_count turns
        # out larger than expected, and never silently dropped.
        used_ids = {id(t) for t in ordered}
        leftover = [t for t in topics if id(t) not in used_ids]
        random.shuffle(leftover)
        ordered += leftover

        cricket_n = sum(1 for t in ordered[:count] if _sport_of(t) == "cricket")
        print(f"[content_mix] Today's batch: {cricket_n}/{min(count, len(ordered))} cricket "
              f"(target {cricket_pct*100:.0f}%), winner_ratio={winner_ratio:.2f}.")
        return ordered

    except Exception as e:
        print(f"[content_mix] ⚠ Could not apply the 85/15/cadence mix ({e}) — "
              f"using the existing pool order instead.")
        return list(topics)


def summarize_mix(topics: list, db=None) -> dict:
    """A quick stats dict for the dashboard/step-summary — actual sport split
    and winner/variety split of a list of topics, no side effects."""
    cricket = sum(1 for t in topics if _sport_of(t) == "cricket")
    other = len(topics) - cricket
    winners = sum(1 for t in topics if _is_winner(t, db))
    return {
        "total": len(topics), "cricket": cricket, "other_sport": other,
        "cricket_pct": round(100 * cricket / max(len(topics), 1), 1),
        "predicted_winners": winners, "variety": len(topics) - winners,
    }


if __name__ == "__main__":
    # Quick manual sanity check with fake topics, no database needed.
    fake = (
        [{"name": f"cricket high {i}", "sport": "cricket", "engagement_tier": "high"} for i in range(6)]
        + [{"name": f"cricket std {i}", "sport": "cricket", "engagement_tier": "standard"} for i in range(14)]
        + [{"name": f"other high {i}", "sport": "other_sport", "engagement_tier": "high"} for i in range(2)]
        + [{"name": f"other std {i}", "sport": "other_sport", "engagement_tier": "standard"} for i in range(3)]
    )
    batch = order_daily_batch(fake, 4, db=None)
    for t in batch[:4]:
        print(f"  {t['sport']:12s} {t['engagement_tier']:8s} {t['name']}")
    print(summarize_mix(batch[:4], db=None))
