"""
analytics_sync.py — the entry point for the analytics-sync workflow.
=============================================================================

Run periodically (see .github/workflows/analytics-sync.yml — daily by
default, since view counts don't meaningfully change minute to minute).
Two jobs, in order:

  1. Pull fresh view/like/comment counts for every recently-published video
     and record them (engine/performance_loop.sync_all_published) — this is
     what lets effective_engagement_tier() start overriding sports_catalog's
     editorial guesses with real data, and what content_mix.py's daily
     "winner" scoring is actually built on.

  2. Look for genuine standouts among those videos and, for each one that
     hasn't already triggered this, invent a small number of genuinely
     different (never identical) follow-up topics to capitalize on that
     proven interest (engine/performance_loop.spawn_follow_ups) — the
     explicit ask: "if a post gets many views, comments and shares, the app
     can see that and can make similarly same topic and content (not same,
     just similar)".

Never raises past this function — a failure here should be visible (it logs
loudly and the workflow can still fail red) but must never touch anything
that generation or publishing depends on; this workflow only reads YouTube
stats and writes new topic rows.
"""
from engine.config import require
from engine import performance_loop
from engine import channels as channels_mod
from engine import step_summary


def run_analytics_sync():
    cfg = require(["SUPABASE_URL", "SUPABASE_SERVICE_KEY"])
    from supabase import create_client
    db = create_client(cfg["SUPABASE_URL"], cfg["SUPABASE_SERVICE_KEY"])

    print("[analytics_sync] Refreshing stats for recently published videos...")
    sync_result = performance_loop.sync_all_published(db)

    avg_views = performance_loop.channel_average_views(db)
    print(f"[analytics_sync] Channel's recent average: {avg_views:.0f} views/video.")

    # Uses the default (unsuffixed) Gemini key for the follow-up-idea call —
    # this app is single-channel, so there is only ever one channel's key to
    # reach for; a multi-channel fork would resolve this per-channel the same
    # way orchestrator.py resolves gemini_key_for(channel) for generation.
    channels = channels_mod.load_channels(db=db)
    api_key = channels_mod.gemini_key_for(channels[0]) if channels else None

    print("[analytics_sync] Looking for standout videos to spawn follow-ups from...")
    follow_up_result = performance_loop.spawn_follow_ups(db, api_key=api_key)

    step_summary.performance_synced(sync_result, follow_up_result, avg_views)
    print(f"[analytics_sync] ✓ Done. Synced {sync_result.get('updated', 0)} video(s), "
          f"spawned {follow_up_result.get('spawned', 0)} follow-up topic(s) from "
          f"{follow_up_result.get('standouts', 0)} standout(s).")


if __name__ == "__main__":
    run_analytics_sync()
