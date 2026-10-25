"""
youtube_analytics.py — retention, shares and traffic sources.
=============================================================================

WHY THIS FILE EXISTS

performance_loop.py reads the YouTube DATA API, which exposes exactly three
numbers per video: viewCount, likeCount, commentCount. It hardcodes
`shares: 0` and has a comment explaining that shares are simply not available
there. That was accurate, and it was also the wrong place to stop, because
the two most useful numbers for a Shorts channel are not in the Data API at
all:

  - AVERAGE VIEW PERCENTAGE — what fraction of the video people actually
    watch. On Shorts this is close to the whole algorithm. This channel's own
    Studio screenshots show 58.7% on one video and 54.8% on another; that gap
    is far more actionable than the view counts next to them, and nothing in
    the repo could see it.
  - TRAFFIC SOURCE — one of this channel's videos gets 98.1% of its views
    from the Shorts feed. Knowing whether a video travelled on the feed or on
    search completely changes what "it did well" means.

Both live in the YouTube ANALYTICS API, which is a different API, with a
different scope, on the same OAuth credentials this project already has.

ABOUT THE EXTRA SCOPE
Reading analytics needs `yt-analytics.readonly` in addition to the upload
scope. A token issued before this module existed will not have it, so every
call here fails with a 403. That is handled as a normal, expected state, not
an error: `available()` reports it, every function returns None, and
performance_loop carries on with the Data API numbers exactly as it did
before. The channel keeps working; it just learns less until the token is
re-issued (one command — see docs/18).

COST: free. The Analytics API has a generous free quota and this runs once a
day over at most a few dozen videos.
"""
from datetime import datetime, timezone, timedelta

ANALYTICS_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"

# Remembered for the process so a channel without the scope logs the
# explanation once per run instead of once per video.
_scope_warning_shown = False


def _service(creds_override: dict = None):
    """Builds an authenticated youtubeAnalytics service, or returns None."""
    try:
        from engine import publisher
        from googleapiclient.discovery import build
        # Reuses the SAME OAuth credentials the uploader already has — no
        # second login, no second key. See publisher.SCOPES.
        creds = publisher._credentials_from_env(creds_override)
        if creds is None:
            return None
        return build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    except Exception as e:
        msg = str(e)
        if "invalid_grant" in msg.lower():
            # The channel's refresh token is dead — publisher.py already
            # explains that one loudly at upload time; no point repeating
            # the whole thing here.
            print("[youtube_analytics] Skipping analytics: the YouTube refresh token "
                  "needs renewing (see the publish step's error for the fix).")
        else:
            print(f"[youtube_analytics] Could not build the analytics service: {e}")
        return None


def _warn_scope_once(detail: str):
    global _scope_warning_shown
    if _scope_warning_shown:
        return
    _scope_warning_shown = True
    print("[youtube_analytics] ⚠ Retention and share data are unavailable on this "
          "token. That is expected if the token was created before this feature "
          "existed — it needs the extra 'yt-analytics.readonly' scope.")
    print("[youtube_analytics]   Fix (2 minutes, free): re-run "
          "`python -m engine.publisher --setup` and update the YOUTUBE_TOKEN secret. "
          "Everything else keeps working until then, just with view/like/comment "
          "counts only.")
    print(f"[youtube_analytics]   Detail: {detail}")


def available(creds_override: dict = None) -> bool:
    return _service(creds_override) is not None


def fetch_video_metrics(youtube_id: str, published_at: str = None,
                        creds_override: dict = None) -> dict | None:
    """Retention, shares, subscribers-gained and average view duration for
    one video. Returns None if the Analytics API cannot be reached — callers
    must treat None as 'no extra data', never as zeros, because writing a
    real 0% retention when the truth is 'unknown' would poison every
    comparison engine/insights.py makes.
    """
    svc = _service(creds_override)
    if svc is None:
        return None

    start = "2005-01-01"
    if published_at:
        try:
            start = published_at[:10]
        except Exception:
            pass
    end = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        resp = svc.reports().query(
            ids="channel==MINE",
            startDate=start,
            endDate=end,
            metrics=("views,likes,comments,shares,subscribersGained,"
                     "averageViewDuration,averageViewPercentage"),
            filters=f"video=={youtube_id}",
        ).execute()
    except Exception as e:
        msg = str(e)
        if "403" in msg or "insufficient" in msg.lower() or "scope" in msg.lower():
            _warn_scope_once(msg[:200])
        else:
            print(f"[youtube_analytics] ⚠ Analytics read failed for {youtube_id}: {e}")
        return None

    rows = resp.get("rows") or []
    if not rows:
        return None
    headers = [h["name"] for h in (resp.get("columnHeaders") or [])]
    values = dict(zip(headers, rows[0]))

    def num(key, cast=int):
        try:
            return cast(values.get(key) or 0)
        except (TypeError, ValueError):
            return 0

    return {
        "views": num("views"),
        "likes": num("likes"),
        "comments": num("comments"),
        "shares": num("shares"),
        "subscribers_gained": num("subscribersGained"),
        "avg_view_duration": num("averageViewDuration"),
        "avg_view_percentage": round(num("averageViewPercentage", float), 1),
    }


def fetch_traffic_sources(youtube_id: str, published_at: str = None,
                          creds_override: dict = None) -> dict | None:
    """Share of views by traffic source, e.g. {'SHORTS': 98.1, 'YT_SEARCH': 1.1}.

    This is what tells you whether a video travelled on the Shorts feed or
    was found deliberately — two completely different kinds of success that
    the view count alone cannot distinguish.
    """
    svc = _service(creds_override)
    if svc is None:
        return None
    start = (published_at or "2005-01-01")[:10]
    end = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        resp = svc.reports().query(
            ids="channel==MINE", startDate=start, endDate=end,
            metrics="views", dimensions="insightTrafficSourceType",
            filters=f"video=={youtube_id}", sort="-views",
        ).execute()
    except Exception as e:
        if "403" in str(e):
            _warn_scope_once(str(e)[:200])
        return None
    rows = resp.get("rows") or []
    total = sum((r[1] or 0) for r in rows) or 1
    return {str(r[0]): round((r[1] or 0) * 100.0 / total, 1) for r in rows}
