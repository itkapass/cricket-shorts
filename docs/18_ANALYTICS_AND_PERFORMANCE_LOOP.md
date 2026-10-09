# 18 — The performance loop (the app learns from its own real views)

## What this is

A new workflow, **Analytics Sync**, runs once a day and does two things —
both asked for directly: *"if per day video posting count is 4, 2 videos
should be more engaging/highly reachable ones and the other 2 should be
based on other topics... if a post gets many views, comments and shares,
the app can see that and can make similarly same topic and content (not
same, just similar)."*

1. **Reads real stats.** For every video published in the last 30 days, it
   pulls current view/like/comment counts from YouTube and saves them.
2. **Finds standouts and spawns follow-ups.** A video that clearly
   outperformed this channel's own recent average gets 2 new, genuinely
   different follow-up topics added to the pool — never a rename of the
   original (see `engine/performance_loop.py`'s module docstring for the
   full reasoning and the exact rules the AI is given for "different, not
   identical").

## Where the "2 winners + 2 variety" strategy comes from

`engine/content_mix.py` reads each day's topic pool and splits it into
**predicted winners** and **variety**, at a ratio you control
(`content_mix_winner_ratio`, default 50/50 — so a 4-video day really is 2
and 2, exactly as asked). "Predicted winner" is never a fixed guess forever:

1. **This exact topic already has a published video with real stats?** Its
   own measured performance decides — reality always outranks a guess.
2. **No video yet, but other topics in the same category have published?**
   Their average performance is used as the best available signal.
3. **Neither exists yet (a brand-new topic)?** Falls back to
   `engine/sports_catalog.py`'s one-time editorial guess (`engagement_tier`:
   `"high"` or `"standard"`) — a human judgment call about which angles
   usually travel, used only until real data exists.

This is `engine/performance_loop.py`'s `effective_engagement_tier()` — every
other module calls that one function instead of reading the static guess
directly, so the whole channel gets smarter on its own as real views
accumulate, with nothing to configure.

## What counts as a "standout" (and why there's no fixed number)

A channel's first week might average 40 views a video — a video with 300
views that week is a genuine standout. The same 300 views on a channel that
normally gets 50,000 would be a quiet underperformer. So "standout" is
always relative to **this channel's own** recent average, not a number
copied from someone else's channel:

| Setting | Default | What it does |
|---|---|---|
| `performance_loop_view_multiplier` | `3.0` | A video needs ≥ 3× the channel's recent average views to count as a standout. |
| `performance_loop_min_views` | `200` | ...but always needs at least this many views, so a brand-new channel (no average yet) doesn't fire on pure noise. |
| `performance_loop_enabled` | `true` | Turn the whole follow-up-spawning half off without touching the stats-sync half. |

All three are editable in **Settings** in the dashboard, same as any other
setting — no code changes needed to tune this.

## What it does NOT do

- It never uploads, edits, or deletes a video — strictly reads YouTube
  statistics and writes new rows to the `topics` table.
- It never touches share counts — the YouTube Data API (the scope this
  project already sets up for uploading) doesn't expose a public share
  count. The engagement score still works well from views/likes/comments
  alone; share counts are recorded as `0` rather than guessed.
- It never repeats itself: once a video has spawned its follow-ups, it's
  marked (`follow_up_spawned`) so the same standout can't fire twice.

## Setup

**You need one thing you may not have yet: `YOUTUBE_API_KEY`.** This is
*not* the OAuth credentials used for uploading (`YOUTUBE_CLIENT_ID` /
`_SECRET` / `_REFRESH_TOKEN`) — it's a separate, much simpler key, because
view/like/comment counts on a public video are public data that doesn't
need anyone's permission to read.

1. In the same Google Cloud project you used for YouTube publishing
   (docs/07), go to **APIs & Services → Credentials → Create Credentials →
   API key**.
2. Copy it, add it as a GitHub repo secret named `YOUTUBE_API_KEY`.
3. That's it. If you already added this key for Trending Radar
   (`engine/trending.py` uses the exact same one), you're already done —
   nothing new to create.

Everything else — Supabase, Gemini/Groq — reuses the exact same secrets
your other workflows already use. The whole loop is enabled automatically
once you've run migration `007_cricket_sports_content_mix.sql` (see docs/01).

To run it by hand once (useful right after your first few videos have had a
day to collect views): repo → **Actions** → **Analytics Sync** → **Run
workflow**.

## If you ever see "YouTube rejected the statistics read"

First check `YOUTUBE_API_KEY` is actually set — that's the fix for almost
everyone. Without it, the app falls back to your upload-scoped OAuth
credentials, which can sometimes read public statistics too but aren't
guaranteed to. If you'd rather not add a second key, re-run
`python -m engine.publisher --setup` locally and request a broader scope,
but adding `YOUTUBE_API_KEY` is the simpler fix. Either way, this only
pauses the performance loop — publishing and everything else keeps working
normally while you sort it out.
