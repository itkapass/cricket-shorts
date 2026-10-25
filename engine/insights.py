"""
insights.py — turns real YouTube numbers into instructions the writer follows.
=============================================================================

WHY THIS FILE EXISTS (the Part 4.4 bug, in one paragraph)

The repo already pulled real view/like/comment counts (analytics_sync.py ->
performance_loop.sync_all_published) and already scored them. But nothing
downstream read any of it. A search of the whole repo for the words
`video_stats`, `engagement_score` or `performance_loop` inside
topic_synthesizer.py or script_generator.py returned ZERO hits, and
orchestrator.py imported performance_loop without ever calling it. The only
consumer anywhere was content_mix.is_high_engagement(), which affects which
SLOT a topic fills — not which topics get invented, and not one word of how
the script is written.

So the "smart" loop measured everything and changed nothing. This module is
the missing half: it reads what actually performed, works out WHICH
DECISIONS correlate with that performance, and hands back plain-English
instructions that go straight into the topic-inventing prompt and the
script-writing prompt.

WHAT IT COMPARES
Part 5 asks for performance compared across topic type, the specific subject,
the opening-hook style, script length/pacing, and publish time slot. Those
last three were not even being recorded, so comparison was impossible no
matter how good the analysis was. Migration 009 adds the columns; classify()
below fills them at save time; this module reads them back.

HONEST ABOUT SMALL NUMBERS
Every finding carries the sample size it came from, and nothing is reported
as a finding below MIN_SAMPLE videos per side of a comparison. A channel with
nine videos does not have statistically meaningful evidence that question
hooks beat statement hooks, and pretending otherwise would bias the whole
channel on noise. When there isn't enough data yet this module returns empty
strings, and every caller treats that as "carry on as before" — so the app
behaves exactly like the old one until it genuinely knows something.

AUDITABLE, NOT A BLACK BOX
Part 5 asks for before/after visibility. Every finding this module acts on is
written to the `insight_log` table with the numbers behind it and the date,
and printed to the workflow Summary tab, so there is always an answer to
"why did it start writing hooks that way".
"""
import re
from datetime import datetime, timezone, timedelta

# Below this many videos on EITHER side of a comparison, we say nothing.
MIN_SAMPLE = 4
# How far back to look. Older videos were made by a different version of the
# prompt and comparing against them measures the code, not the content.
WINDOW_DAYS = 90
# A difference smaller than this is noise, not a finding.
MIN_LIFT = 1.25  # the winner must average 25% better to count


# ─── Classifying a script, so performance can be attributed to a choice ─────

HOOK_STYLES = ("question", "statement", "command", "number")


def classify_hook(first_line: str) -> str:
    """Names the opening-hook style of a script in one word.

    This is deliberately crude and rule-based rather than a model call: it
    runs on every video, it must be free, and it must give the SAME answer
    for the same text forever, otherwise last month's labels and this
    month's are not comparable and the whole analysis is meaningless.
    """
    t = (first_line or "").strip()
    if not t:
        return "unknown"
    low = t.lower()
    if "?" in t:
        return "question"
    if re.match(r"^\s*(why|how|what|who|when|where|which|did|does|do|is|are|can|could|would)\b", low):
        return "question"          # a question in spirit, even without the mark
    if re.match(r"^\s*\d", t) or re.search(r"\b\d{2,}\b", t[:40]):
        return "number"            # opens on a figure
    if re.match(r"^\s*(imagine|picture|think|watch|listen|forget|stop|meet|look)\b", low):
        return "command"           # second-person imperative
    return "statement"


def classify_length(word_count: int) -> str:
    """Buckets pacing. Shorts live or die on pacing, and 'how many words did
    we cram into 45 seconds' is the measurable version of that."""
    if word_count <= 0:
        return "unknown"
    if word_count < 75:
        return "slow"
    if word_count < 110:
        return "medium"
    return "fast"


def _has_cta(last_scene: dict) -> bool:
    if (last_scene or {}).get("scene_kind") == "quiz":
        return True
    try:
        from engine import engagement
        return engagement.has_closing_ask({"scenes": [last_scene or {}]})
    except Exception:
        return "?" in ((last_scene or {}).get("voice_text") or "")


def classify(storyboard: dict) -> dict:
    """The metadata bundle recorded alongside every video, so that months
    later we can ask 'which of these choices actually worked'. Returns plain
    values ready to write straight onto the videos row."""
    scenes = (storyboard or {}).get("scenes") or []
    first_line = ""
    for sc in scenes:
        txt = (sc.get("voice_text") or "").strip()
        if txt:
            first_line = txt
            break
    words = sum(len((sc.get("voice_text") or "").split()) for sc in scenes)
    last = scenes[-1] if scenes else {}
    return {
        "hook_style": classify_hook(first_line),
        "hook_text": first_line[:300] or None,
        "word_count": words,
        "pacing": classify_length(words),
        "scene_count": len(scenes),
        # Uses engagement.has_closing_ask so "comment below" counts as a CTA
        # and not only a question mark — otherwise the label disagrees with
        # the quality gate that checks the same thing.
        "has_cta": _has_cta(last),
    }


# ─── Reading performance back out ───────────────────────────────────────────

def _published_with_stats(db, days: int = WINDOW_DAYS) -> list:
    """Every published video in the window, each joined to its most recent
    stats row. Returns [] on any problem — an analysis that cannot run must
    never stop a video from being made."""
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        vids = (
            db.table("videos")
            .select("id, title, archetype, category, topic_id, hook_style, pacing, "
                    "word_count, published_at, publish_slot_hour")
            .eq("status", "published").gte("published_at", since)
            .execute().data
        ) or []
        if not vids:
            return []
        ids = [v["id"] for v in vids]
        stats = (
            db.table("video_stats")
            .select("video_id, views, likes, comments, shares, engagement_score, "
                    "avg_view_percentage, fetched_at")
            .in_("video_id", ids).execute().data
        ) or []
        latest = {}
        for s in stats:
            vid = s["video_id"]
            if vid not in latest or (s.get("fetched_at") or "") > (latest[vid].get("fetched_at") or ""):
                latest[vid] = s
        out = []
        for v in vids:
            st = latest.get(v["id"])
            if not st:
                continue
            row = dict(v)
            row.update({k: st.get(k) for k in
                        ("views", "likes", "comments", "shares",
                         "engagement_score", "avg_view_percentage")})
            out.append(row)
        return out
    except Exception as e:
        print(f"[insights] ⚠ Could not read performance history: {e}")
        return []


def _compare(rows: list, field: str, metric: str = "views") -> dict | None:
    """Groups rows by `field` and returns the best and worst group, but only
    when both sides clear MIN_SAMPLE and the gap clears MIN_LIFT. Returns
    None — meaning "say nothing" — in every other case."""
    groups = {}
    for r in rows:
        key = r.get(field)
        if not key or key == "unknown":
            continue
        groups.setdefault(key, []).append(float(r.get(metric) or 0))
    eligible = {k: v for k, v in groups.items() if len(v) >= MIN_SAMPLE}
    if len(eligible) < 2:
        return None
    averaged = {k: sum(v) / len(v) for k, v in eligible.items()}
    best = max(averaged, key=averaged.get)
    worst = min(averaged, key=averaged.get)
    if averaged[worst] <= 0 or averaged[best] / averaged[worst] < MIN_LIFT:
        return None
    return {
        "field": field, "metric": metric,
        "winner": best, "winner_avg": round(averaged[best], 1),
        "winner_n": len(eligible[best]),
        "loser": worst, "loser_avg": round(averaged[worst], 1),
        "loser_n": len(eligible[worst]),
        "lift": round(averaged[best] / averaged[worst], 2),
    }


def compute(db) -> dict:
    """The whole analysis. Returns a dict of findings, each either a
    comparison dict or None. Safe on an empty channel."""
    rows = _published_with_stats(db)
    findings = {
        "sample_size": len(rows),
        "hook_style": _compare(rows, "hook_style", "views"),
        "pacing": _compare(rows, "pacing", "views"),
        "archetype": _compare(rows, "archetype", "views"),
        "publish_slot": _compare(rows, "publish_slot_hour", "views"),
        "hook_style_engagement": _compare(rows, "hook_style", "engagement_score"),
    }
    # Retention is the single most useful Shorts signal, and only exists once
    # the YouTube Analytics API is wired up (engine/youtube_analytics.py).
    if any(r.get("avg_view_percentage") for r in rows):
        findings["pacing_retention"] = _compare(rows, "pacing", "avg_view_percentage")
        findings["hook_retention"] = _compare(rows, "hook_style", "avg_view_percentage")
    return findings


# ─── Turning findings into instructions the model will actually follow ──────

_LABEL = {
    "hook_style": "opening-hook style",
    "pacing": "script pacing",
    "archetype": "video format",
    "publish_slot": "publish hour",
    "hook_style_engagement": "opening-hook style (by engagement, not reach)",
    "pacing_retention": "script pacing (by how long people watch)",
    "hook_retention": "opening-hook style (by how long people watch)",
}


def prompt_block(db) -> str:
    """The plain-English block injected into the script-writing prompt.

    Returns "" when there is not enough data — callers must treat that as
    "no guidance", never as "no preference", so a young channel writes
    exactly as it did before.
    """
    f = compute(db)
    lines = []
    for key in ("hook_retention", "hook_style", "hook_style_engagement", "pacing_retention", "pacing"):
        c = f.get(key)
        if not c:
            continue
        lines.append(
            f"- This channel's own published videos show {_LABEL[key]} '{c['winner']}' "
            f"averaging {c['winner_avg']} vs '{c['loser']}' at {c['loser_avg']} "
            f"({c['lift']}x better, from {c['winner_n']} and {c['loser_n']} videos). "
            f"Prefer '{c['winner']}' unless the topic genuinely fights it."
        )
        if key in ("hook_retention", "hook_style"):
            break   # one hook instruction is guidance; three is noise
    if not lines:
        return ""
    return (
        "\n\nWHAT HAS ACTUALLY WORKED ON THIS CHANNEL (real measured data, not a guess):\n"
        + "\n".join(lines)
        + "\nThese are preferences drawn from real numbers, not hard rules. A genuinely "
          "better idea for THIS topic beats the pattern — but all else equal, follow the "
          "pattern.\n"
    )


def topic_bias_block(db) -> str:
    """The equivalent block for the topic-INVENTING prompt. Different job:
    the script prompt wants style guidance, this wants subject guidance."""
    f = compute(db)
    c = f.get("archetype")
    rows = _published_with_stats(db)
    lines = []
    if c:
        lines.append(
            f"- The '{c['winner']}' format averages {c['winner_avg']} views on this channel "
            f"vs '{c['loser']}' at {c['loser_avg']} ({c['winner_n']} and {c['loser_n']} videos). "
            f"Lean toward subjects that suit '{c['winner']}'."
        )
    # The five best-performing individual videos, named, so the model can see
    # what kind of subject actually landed rather than being told a category.
    ranked = sorted(rows, key=lambda r: float(r.get("views") or 0), reverse=True)[:5]
    if len(rows) >= MIN_SAMPLE and ranked:
        titles = "; ".join(f"\"{r['title']}\" ({int(r.get('views') or 0)} views)" for r in ranked)
        lines.append(f"- This channel's five best-performing videos so far: {titles}. "
                     f"Invent topics with the same kind of pull, never the same subject again.")
    weakest = sorted(rows, key=lambda r: float(r.get("views") or 0))[:3]
    if len(rows) >= MIN_SAMPLE * 2 and weakest:
        titles = "; ".join(f"\"{r['title']}\"" for r in weakest)
        lines.append(f"- These landed worst, so avoid this shape of idea: {titles}.")
    if not lines:
        return ""
    return ("\n\nREAL PERFORMANCE DATA FROM THIS CHANNEL:\n" + "\n".join(lines) + "\n")


def log_decisions(db, findings: dict = None, applied_to: str = "generation"):
    """Writes what the system decided and why to `insight_log`, so Part 5's
    'genuine before/after visibility, auditable, not a black box' is a real
    table someone can read rather than a claim."""
    f = findings if findings is not None else compute(db)
    try:
        written = 0
        for key, c in f.items():
            if key == "sample_size" or not isinstance(c, dict):
                continue
            db.table("insight_log").insert({
                "dimension": key,
                "metric": c["metric"],
                "winner": str(c["winner"]),
                "winner_avg": c["winner_avg"],
                "winner_n": c["winner_n"],
                "loser": str(c["loser"]),
                "loser_avg": c["loser_avg"],
                "loser_n": c["loser_n"],
                "lift": c["lift"],
                "applied_to": applied_to,
                "sample_size": f.get("sample_size", 0),
            }).execute()
            written += 1
        if written:
            print(f"[insights] Recorded {written} finding(s) to insight_log.")
    except Exception as e:
        print(f"[insights] ⚠ Could not write insight_log ({e}) — analysis still applied.")


def summarize(db) -> str:
    """One short human-readable paragraph for the Actions Summary tab."""
    f = compute(db)
    n = f.get("sample_size", 0)
    if n < MIN_SAMPLE * 2:
        return (f"Performance learning: {n} measured video(s) so far — need about "
                f"{MIN_SAMPLE * 2} before any pattern is trustworthy. Writing normally "
                f"until then.")
    found = [k for k, v in f.items() if k != "sample_size" and isinstance(v, dict)]
    if not found:
        return (f"Performance learning: {n} measured videos, but no difference big enough "
                f"to act on yet (needs a {MIN_LIFT}x gap). Writing normally.")
    return (f"Performance learning: from {n} measured videos, acting on "
            f"{len(found)} finding(s): {', '.join(_LABEL.get(k, k) for k in found)}.")
