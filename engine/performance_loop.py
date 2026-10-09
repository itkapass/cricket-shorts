"""
performance_loop.py — real numbers replace guesses, and standouts spawn
genuinely new (never identical) follow-ups.
=============================================================================

TWO THINGS THIS DOES, BOTH EXPLICITLY REQUESTED

1. REAL DATA OVERRIDES THE EDITORIAL GUESS
   sports_catalog.py tags every starter topic with an `engagement_tier`
   ("high" | "standard") — a human editorial guess about which angles travel
   best, used to seed content_mix.py's daily slot planner before any real
   analytics exist. The moment a topic's video actually publishes and gets
   measured, that guess should stop mattering — real view/like/comment data
   is strictly better information. `effective_engagement_tier()` is the one
   function every other module calls instead of reading `engagement_tier`
   directly, so this override happens in exactly one place.

2. STANDOUTS SPAWN SIMILAR, NEVER IDENTICAL, FOLLOW-UPS
   Asked for in these exact words: "if a post gets many views, comments and
   shares, the app can see that and can make similarly same topic and
   content (not same, just similar) so that it will also get reached (but
   the followup everything will not be the same)". `spawn_follow_ups()` is
   that mechanism: it finds published videos that are genuine standouts
   relative to THIS channel's own recent average (a fixed view-count
   threshold means nothing for a brand-new channel), and asks the model for
   a small number of genuinely different angles on the same underlying
   subject — never a rename of the original, and explicitly told not to
   re-litigate the exact same specific fact or record the original already
   covered.

WHY "STANDOUT" IS RELATIVE, NOT A FIXED NUMBER
A channel's first week might average 40 views a video; a video with 300
views on week one is a genuine standout worth following up. The same 300
views on a channel that normally gets 50,000 would be a quiet underperformer.
Comparing against this channel's OWN recent average (settings:
performance_loop_view_multiplier, default 3x) makes the signal meaningful at
any channel size, with a small absolute floor (performance_loop_min_views)
so it can't fire on pure noise while the channel is brand new.

WHAT THIS DOES NOT DO
It never touches Test scores, comments, or anything else on YouTube — it
only READS statistics and WRITES new topic rows. Nothing here uploads,
deletes, or edits an existing video.
"""
import math
from datetime import datetime, timezone, timedelta

from engine import sports_catalog

DEFAULT_VIEW_MULTIPLIER = 3.0
DEFAULT_MIN_VIEWS = 200
RECENT_WINDOW_DAYS = 14
FOLLOW_UP_COUNT = 2  # per standout — enough variety, never a flood from one hit


def _setting(db, key: str, default: str) -> str:
    try:
        rows = db.table("settings").select("value").eq("key", key).execute().data or []
        return rows[0]["value"] if rows and rows[0].get("value") not in (None, "") else default
    except Exception:
        return default


def _setting_float(db, key: str, default: float) -> float:
    try:
        return float(_setting(db, key, str(default)))
    except (TypeError, ValueError):
        return default


# ─── Scoring ──────────────────────────────────────────────────────────────

def score_video(views: int, likes: int, comments: int, shares: int = 0) -> float:
    """A single 0-100 engagement score.

    Views alone reward reach, not engagement — someone scrolling past a
    thumbnail is a weaker signal than someone stopping to comment or share
    it. So the score is REACH (log-scaled, so one viral outlier doesn't blow
    the scale for every other video) plus an ENGAGEMENT-RATE bonus (actions
    per view, which is what actually says "this specific video landed" for
    a channel of any size).

    `shares` defaults to 0 and is fine to leave at 0 forever — the YouTube
    Data API (the scope this project already sets up) does not expose a
    public share count; getting a real one needs the separate YouTube
    Analytics API and an extra OAuth scope, which is optional (see
    docs/18_ANALYTICS_AND_PERFORMANCE_LOOP.md). The score still works well
    from views/likes/comments alone.
    """
    views = max(0, int(views or 0))
    likes = max(0, int(likes or 0))
    comments = max(0, int(comments or 0))
    shares = max(0, int(shares or 0))

    reach = math.log10(views + 1) * 10  # 0 views -> 0; 1,000 -> ~30; 100,000 -> ~50
    # Comments and shares are weighted far above likes: a like costs the
    # viewer one tap, a comment or share costs a real decision to act.
    actions = likes * 1 + comments * 4 + shares * 8
    rate_bonus = min(30.0, (actions / max(views, 1)) * 1000)  # actions per 1,000 views, capped
    return round(min(100.0, reach + rate_bonus), 1)


def channel_average_views(db, days: int = RECENT_WINDOW_DAYS) -> float:
    """This channel's own recent average views per published video — the
    baseline a 'standout' is measured against. Returns 0.0 (never raises) if
    there isn't enough history yet, which callers treat as 'nothing to
    compare against yet' rather than a crash."""
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        videos = (
            db.table("videos").select("id").eq("status", "published")
            .gte("published_at", since).execute().data
        ) or []
        if not videos:
            return 0.0
        video_ids = [v["id"] for v in videos]
        # Latest stats row per video, summed. A single query pulling every
        # stats row and reducing in Python is simplest and these tables stay
        # small (one row per video per analytics-sync run, not per view).
        stats = (
            db.table("video_stats").select("video_id, views, fetched_at")
            .in_("video_id", video_ids).execute().data
        ) or []
        latest = {}
        for s in stats:
            vid = s["video_id"]
            if vid not in latest or s["fetched_at"] > latest[vid]["fetched_at"]:
                latest[vid] = s
        if not latest:
            return 0.0
        return sum(s.get("views") or 0 for s in latest.values()) / len(latest)
    except Exception as e:
        print(f"[performance_loop] ⚠ Could not compute channel average views: {e}")
        return 0.0


def is_standout(views: int, avg_views: float, db) -> bool:
    multiplier = _setting_float(db, "performance_loop_view_multiplier", DEFAULT_VIEW_MULTIPLIER)
    min_views = _setting_float(db, "performance_loop_min_views", DEFAULT_MIN_VIEWS)
    if views < min_views:
        return False
    # No baseline yet (brand-new channel) — the absolute floor alone decides.
    if avg_views <= 0:
        return True
    return views >= avg_views * multiplier


# ─── Fetching real stats from YouTube ───────────────────────────────────────

YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _fetch_statistics(youtube_id: str, creds_override: dict = None) -> dict | None:
    """Returns the raw `statistics` dict for one video, or None if it
    couldn't be read. Tries the SIMPLE path first: view/like/comment counts
    on a public video are public data — the same YOUTUBE_API_KEY this
    project already uses for Trending Radar (engine/trending.py) can read
    them with no OAuth consent at all, which is both simpler and avoids
    asking every user to redo the publishing OAuth flow just for this.
    Falls back to the OAuth-authenticated upload credentials only if no API
    key is configured, since those credentials can usually read public
    statistics too even though they were issued for uploading."""
    from engine.config import get
    api_key = get("YOUTUBE_API_KEY")
    if api_key:
        import urllib.request
        import urllib.parse
        import json as jsonlib
        params = urllib.parse.urlencode({"part": "statistics", "id": youtube_id, "key": api_key})
        with urllib.request.urlopen(f"{YOUTUBE_VIDEOS_URL}?{params}", timeout=15) as resp:
            data = jsonlib.loads(resp.read())
        items = data.get("items") or []
        return items[0].get("statistics", {}) if items else None

    from engine import publisher
    youtube = publisher.get_authenticated_service(creds_override)
    resp = youtube.videos().list(part="statistics", id=youtube_id).execute()
    items = resp.get("items") or []
    return items[0].get("statistics", {}) if items else None


def fetch_and_record_stats(video_row: dict, db, creds_override: dict = None) -> dict | None:
    """Pulls current view/like/comment counts for one published video and
    writes a video_stats row. Returns the row written, or None on any
    failure — one video's API hiccup (or a channel whose OAuth token predates
    this feature) must never stop the whole analytics-sync run.
    """
    youtube_id = video_row.get("youtube_id")
    if not youtube_id:
        return None
    try:
        stats = _fetch_statistics(youtube_id, creds_override)
        if stats is None:
            print(f"[performance_loop] ⚠ YouTube has no video matching id {youtube_id} "
                  f"(job {video_row.get('job_id')}) — skipping.")
            return None
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        row = {
            "video_id": video_row["id"],
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": 0,  # see score_video()'s docstring — not exposed by this API/scope
            "engagement_score": score_video(views, likes, comments, 0),
        }
        db.table("video_stats").insert(row).execute()
        return row
    except Exception as e:
        msg = str(e)
        if "insufficient" in msg.lower() or "403" in msg:
            print(f"[performance_loop] ⚠ YouTube rejected the statistics read for "
                  f"{youtube_id}. If YOUTUBE_API_KEY isn't set, add it (docs/07) — it's a "
                  f"plain, free API key that reads public stats with no OAuth consent "
                  f"needed. See docs/18_ANALYTICS_AND_PERFORMANCE_LOOP.md. ({e})")
        else:
            print(f"[performance_loop] ⚠ Could not fetch stats for {youtube_id}: {e}")
        return None


def sync_all_published(db, creds_override: dict = None, max_age_days: int = 30) -> dict:
    """Fetches and records fresh stats for every published video from the
    last `max_age_days` — the whole point of the analytics-sync workflow.
    Returns a small summary dict; never raises, so one bad video never stops
    the rest from being measured."""
    since = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    videos = (
        db.table("videos").select("id, job_id, youtube_id, published_at")
        .eq("status", "published").gte("published_at", since)
        .not_.is_("youtube_id", "null")
        .execute().data
    ) or []

    updated = 0
    for v in videos:
        if fetch_and_record_stats(v, db, creds_override):
            updated += 1
    print(f"[performance_loop] ✓ Synced stats for {updated}/{len(videos)} published video(s).")
    return {"checked": len(videos), "updated": updated}


# ─── effective_engagement_tier() — the override sports_catalog.py promises ──

def effective_engagement_tier(topic: dict, db=None) -> str:
    """'high' | 'standard' for one topic. This is what content_mix.py calls
    instead of reading topic['engagement_tier'] directly.

    Priority, each step only used if the one before it has nothing to say:
      1. Real measured performance of THIS topic's own published video(s) —
         once reality exists for this exact topic, the editorial guess no
         longer gets a vote.
      2. Real measured AVERAGE for OTHER topics in the same category + sport
         that have already published — a brand-new topic in a category
         that's reliably landed deserves the same "high" prediction even
         before its own specific video exists.
      3. The topic's own static `engagement_tier` field (the sports_catalog.py
         editorial starting guess) — used until step 1 or 2 has real data.
    """
    static_guess = (topic.get("engagement_tier") or "standard").lower()
    if static_guess not in ("high", "standard"):
        static_guess = "standard"
    if db is None:
        return static_guess

    try:
        topic_id = topic.get("id")
        if topic_id:
            own_videos = (
                db.table("videos").select("id").eq("topic_id", topic_id)
                .eq("status", "published").execute().data
            ) or []
            if own_videos:
                ids = [v["id"] for v in own_videos]
                stats = (
                    db.table("video_stats").select("video_id, views, engagement_score, fetched_at")
                    .in_("video_id", ids).execute().data
                ) or []
                if stats:
                    latest = {}
                    for s in stats:
                        vid = s["video_id"]
                        if vid not in latest or s["fetched_at"] > latest[vid]["fetched_at"]:
                            latest[vid] = s
                    avg_score = sum(s.get("engagement_score") or 0 for s in latest.values()) / len(latest)
                    return "high" if avg_score >= 50 else "standard"

        category = topic.get("category")
        sport = topic.get("sport")
        if category and sport:
            siblings = (
                db.table("topics").select("id").eq("category", category).eq("sport", sport)
                .execute().data
            ) or []
            sibling_ids = [t["id"] for t in siblings if t.get("id") != topic_id]
            if sibling_ids:
                sib_videos = (
                    db.table("videos").select("id").in_("topic_id", sibling_ids)
                    .eq("status", "published").execute().data
                ) or []
                if sib_videos:
                    vids = [v["id"] for v in sib_videos]
                    stats = (
                        db.table("video_stats").select("video_id, engagement_score, fetched_at")
                        .in_("video_id", vids).execute().data
                    ) or []
                    if stats:
                        latest = {}
                        for s in stats:
                            vid = s["video_id"]
                            if vid not in latest or s["fetched_at"] > latest[vid]["fetched_at"]:
                                latest[vid] = s
                        avg_score = sum(s.get("engagement_score") or 0 for s in latest.values()) / len(latest)
                        return "high" if avg_score >= 45 else "standard"
    except Exception as e:
        print(f"[performance_loop] ⚠ effective_engagement_tier fell back to the static "
              f"guess for '{topic.get('name', '?')}' ({e}).")

    return static_guess


# ─── Follow-up spawning ─────────────────────────────────────────────────────

FOLLOW_UP_SYSTEM = """You write follow-up video topics for a sports/cricket
YouTube Shorts channel. You are given ONE video that clearly outperformed
this channel's own average — real viewers stopped for it. Your job is to
invent genuinely NEW topics that capitalize on the same proven interest
WITHOUT being the same video again.

A follow-up must be:
  - The SAME broad subject or category the original was about (so it earns
    the same audience interest), but a DIFFERENT specific angle, fact, era,
    player, or record — never a reworded restatement of the exact same claim.
  - Something the original video did NOT already cover. If the original was
    "who holds the most Test wickets", a bad follow-up is "the most Test
    wickets, revisited" — a good one is "who holds the most ODI wickets" or
    "the bowler with the best strike rate, not just the most wickets".
  - Standalone: a viewer who never saw the original should still find this
    topic interesting entirely on its own.

Return ONLY a JSON array, no markdown, no preamble:
[
  {"name": "the follow-up topic, phrased as a specific video idea", "description": "one sentence on the angle, and one clause on how it differs from the original"}
]"""


def _generate_follow_up_ideas(original_title: str, original_desc: str, category: str,
                              sport: str, n: int, api_key: str = None) -> list:
    from engine.script_generator import _get_client, _call_model_with_clear_errors
    from engine.topic_synthesizer import _extract_json_array

    user = f"""THE VIDEO THAT OUTPERFORMED THIS CHANNEL'S AVERAGE:
Title: {original_title}
About: {original_desc}
Category: {category}
Sport: {sport}

Invent {n} genuinely different follow-up topics, same category and sport,
that were NOT already covered by the original."""

    client, model_name = _get_client(api_key)
    response = _call_model_with_clear_errors(client, model_name, FOLLOW_UP_SYSTEM, user, temperature=0.9)
    ideas = _extract_json_array(response.text)
    return [
        {"name": i["name"].strip(), "description": i.get("description", "").strip(),
         "category": category, "sport": sport,
         "archetype": sports_catalog.archetype_for(category),
         "engagement_tier": "high",  # inherits the parent's proven pull as its own starting guess
         "quiz_friendly": False, "_provider": response.provider}
        for i in ideas if i.get("name")
    ]


def spawn_follow_ups(db, api_key=None, persona_key: str = "cricket_and_sports") -> dict:
    """Finds published videos that are genuine standouts and haven't already
    spawned a follow-up, and inserts FOLLOW_UP_COUNT genuinely new topics per
    standout. Marks each source video follow_up_spawned=TRUE so it can never
    fire twice for the same video. Returns a summary dict; never raises.
    """
    if _setting(db, "performance_loop_enabled", "true").lower() not in ("true", "1", "yes"):
        return {"checked": 0, "standouts": 0, "spawned": 0}

    try:
        avg_views = channel_average_views(db)
        candidates = (
            db.table("videos")
            .select("id, job_id, topic_id, title, description, follow_up_spawned")
            .eq("status", "published").eq("follow_up_spawned", False)
            .execute().data
        ) or []
    except Exception as e:
        print(f"[performance_loop] ⚠ Could not load candidates for follow-up spawning: {e}")
        return {"checked": 0, "standouts": 0, "spawned": 0}

    standouts, spawned = 0, 0
    for v in candidates:
        try:
            latest_stats = (
                db.table("video_stats").select("views, likes, comments")
                .eq("video_id", v["id"]).order("fetched_at", desc=True).limit(1)
                .execute().data
            ) or []
            if not latest_stats:
                continue
            views = latest_stats[0].get("views") or 0
            if not is_standout(views, avg_views, db):
                continue

            standouts += 1
            topic = None
            if v.get("topic_id"):
                rows = db.table("topics").select("*").eq("id", v["topic_id"]).execute().data or []
                topic = rows[0] if rows else None
            # `videos` has no `category` column of its own — the topic row
            # is the source of truth, with a safe default for the rare
            # custom-prompt video that was never linked to a topic at all.
            category = (topic or {}).get("category") or "trivia_quiz"
            sport = (topic or {}).get("sport") or "cricket"

            ideas = _generate_follow_up_ideas(
                v.get("title") or "", v.get("description") or "", category, sport,
                FOLLOW_UP_COUNT, api_key=api_key,
            )
            existing_names = {
                t["name"].strip().lower()
                for t in (db.table("topics").select("name").execute().data or [])
            }
            for idea in ideas:
                key = idea["name"].strip().lower()
                if key in existing_names:
                    continue
                db.table("topics").insert({
                    "name": idea["name"], "description": idea["description"],
                    "persona_key": persona_key, "is_active": True,
                    "added_by": "performance-follow-up",
                    "category": idea["category"], "sport": idea["sport"],
                    "archetype": idea["archetype"], "engagement_tier": idea["engagement_tier"],
                    "quiz_friendly": idea["quiz_friendly"],
                }).execute()
                existing_names.add(key)
                spawned += 1

            db.table("videos").update({"follow_up_spawned": True}).eq("id", v["id"]).execute()
            print(f"[performance_loop] ✓ '{v.get('title')}' is a standout ({views} views vs "
                  f"channel average {avg_views:.0f}) — spawned {len(ideas)} follow-up topic(s).")
        except Exception as e:
            print(f"[performance_loop] ⚠ Follow-up spawning failed for video {v.get('id')}: {e}")

    return {"checked": len(candidates), "standouts": standouts, "spawned": spawned}
