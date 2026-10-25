# What was broken, why, and what changed

Plain English. One section per problem. Every claim here comes from reading the
code in this repo and checking it against your YouTube Studio numbers and your
dashboard screenshots — not from guessing.

---

## Problem 1 — Auto-approve "worked", but its videos never got published

### What was actually wrong

The approve/reject logic itself was fine. The bug was one line downstream.

When the engine auto-approved a video it wrote `status = 'approved'` and left
`approved_at` empty. Only the dashboard ever filled that column in
(`admin-panel/src/pages/VideoQueue.jsx` line 269).

Then the publisher picked the next video to post like this:

```python
.order("approved_at", desc=False)   # oldest first
.limit(publish_per_run)             # publish_per_run is 1
```

### Why that broke it

In PostgreSQL, an ascending sort puts empty (`NULL`) values **last**. So the
single video fetched each run was always the oldest **hand-approved** one.
Every auto-approved video sat behind every hand-approved video, forever. Not
delayed — permanently stuck.

Auto-approve was doing its job. The queue was quietly throwing the result away.

### What changed

Three things, because any one alone would have left a gap:

1. `engine/orchestrator.py` now stamps `approved_at` when it auto-approves.
   Fixes everything made from now on.
2. `engine/publish_approved.py` no longer depends on the database's NULL
   ordering at all. It sorts by `created_at` (never empty), pulls a wider
   window, then sorts in Python on *approved_at-or-created_at*. It also
   backfills the missing timestamp as it goes, so the queue heals itself.
3. Migration `009` repairs the rows already stuck:
   `UPDATE videos SET approved_at = COALESCE(approved_at, created_at) ...`

---

## Problem 2 — Videos generated didn't match videos published

Three separate leaks, all silent.

### Leak A — the queue starvation above

Covered in Problem 1. This was the biggest one.

### Leak B — a failed upload was permanent

`publish_failed` and `needs_manual` were dead-end statuses. **Nothing anywhere
in the codebase ever moved a row out of them** — no workflow, no script, no
dashboard button.

So a video that hit one momentary `503` during upload, or landed in the window
where your YouTube token had expired, was finished. Fully written, fully
rendered, sitting in storage, costing you the API calls and the compute, and
never published. It didn't appear in any failure count either, because from the
pipeline's point of view it had already succeeded at generation.

**Fixed:** `engine/publish_approved._revive_retryable_failures()` returns those
videos to the queue. It only retries failures whose error text suggests a later
attempt could work (quota, 5xx, timeout, expired token), at most 3 times,
tracked in a new `publish_attempts` column so it can never loop. A genuinely
broken video is still left alone for you to look at.

### Leak C — generation and publishing were paced differently

Generation target is `max_videos_daily` (5 by default), run across 6 scheduled
times a day. Publishing is 1 per run with a minimum gap derived from the daily
cap. Your Studio history matches the arithmetic exactly: 4–5 published per day
against 5 generated, so roughly one video a day joined a backlog that never
cleared.

With Leaks A and B fixed the backlog now drains. If you want it to drain
faster, raise `publish_per_run` in Settings to 2 for a week.

---

## Problem 3 — The engagement question only reached two kinds of video

### What was actually wrong

`engine/engagement.py` is well written and it *was* wired into the script
prompt. But the call site looked like this:

```python
quiz_close_block = engagement.prompt_block(archetype) \
    if archetype in arch.QUIZ_CLOSE_ARCHETYPES else ""
```

Only two archetypes are in `QUIZ_CLOSE_ARCHETYPES`. **Every other format — the
rules explainers, the myth-busts, the record videos — was handed an empty
string.** They were never told to ask the viewer for anything, so they asked
for nothing.

Your numbers say this plainly: 39 published Shorts, **0 comments on every
single one**.

### Why it was written that way

The reasoning was half right. Bolting a trivia question onto a rules explainer
*would* feel like a gimmick, and reserving the quiz mechanic for the formats
built around it was the correct call. The mistake was concluding that the other
formats should therefore end on nothing.

### What changed

`engagement.cta_block(archetype)` now always returns something:

- **Quiz formats** → the full quiz mechanic, unchanged.
- **Everything else** → a shorter closing ask, written as a *menu* the model
  picks from and rephrases, not a line it copies. Three shapes: share-to-a-named-
  person ("send this to the friend who still argues about the no-ball rule"),
  comment-an-opinion, or pick-a-side. One ask only, under ~12 words, tied to
  what the video just said, and never a generic "like and subscribe".

`engagement.has_closing_ask()` is new and lets `quality_gates.py` actually check
the instruction was followed — previously nothing anywhere verified it, which is
exactly why nobody noticed it was only being sent to two formats.

---

## Problem 4 — The "smart" feedback loop measured everything and changed nothing

**This was the big one.** The data collection worked. The data was used by
almost nothing.

### What was actually wrong

`analytics_sync.py` → `performance_loop.sync_all_published()` really did pull
real view/like/comment counts and really did score them. Then:

- **`engine/orchestrator.py` imported `performance_loop` and never called it.**
  A dead import, line 78.
- Searching `topic_synthesizer.py` and `script_generator.py` for `video_stats`,
  `engagement_score` or `performance_loop` returned **zero hits.** Nothing about
  which topic, hook, length or format had worked ever reached the code that
  invents topics or writes scripts.
- The only consumer anywhere was `content_mix.is_high_engagement()`, which
  affects which *slot* a topic fills — not which topics exist, and not one word
  of how they're written.

So the channel could discover that one kind of video outperformed everything
else by 10x and carry on writing exactly as before.

### Four more things were wrong underneath that

1. **Three of the five things Part 5 asks to compare were never recorded.**
   Opening-hook style, script length/pacing and publish time slot had no
   columns. The comparison wasn't broken, it was impossible.
2. **Only the Data API was used**, which exposes views, likes and comments and
   nothing else. `shares` was hardcoded `0`. Retention — the single most
   important Shorts signal, and visible right there in your Studio at 58.7% and
   54.8% — was invisible to the app.
3. **The standout bar was set so high it almost never fired.** "At least 200
   views AND at least 3x the channel average" meant ~630 views on your channel.
   4 of 39 videos cleared it. A learning loop that triggers on one video in ten
   teaches nothing.
4. **`follow_up_spawned` filtered with `= false`, which never matches `NULL`.**
   Any video created before migration 007 had `NULL` there and was invisible to
   the follow-up loop permanently, however well it performed.

### What changed

**New file: `engine/insights.py`** — the missing half of the loop. It reads what
performed, works out which *decisions* correlate with that performance, and
returns plain-English instructions.

- `classify()` labels every script the same way forever (hook style, word
  count, pacing), so last month's labels and this month's are comparable.
- `prompt_block()` goes into the script-writing prompt: *"this channel's own
  videos show question hooks averaging 840 vs statement hooks at 190 — 4.4x
  better, from 7 and 11 videos. Prefer question hooks unless the topic fights
  it."*
- `topic_bias_block()` goes into the topic-inventing prompt, including your five
  best-performing videos by name so the model can see what actually landed.
- `log_decisions()` writes every finding to a new `insight_log` table with the
  numbers and sample size behind it, so there's always a readable answer to
  "why did it start writing like this".

**It is deliberately cautious.** Nothing is reported as a finding below 4 videos
per side of a comparison, and the winner must average 25% better to count. Below
that it returns an empty string, and an empty string behaves exactly like the
old code. A channel with nine videos does not have real evidence about hook
styles, and biasing the whole channel on noise would be worse than not learning.

**New file: `engine/youtube_analytics.py`** — reads the YouTube *Analytics* API
on the same OAuth credentials, for retention, average view duration, real share
counts, subscribers gained and traffic source. Unavailable values are stored as
`NULL`, never `0`, because a fabricated "0% retention" would poison every
comparison.

**Also changed:**
- `publisher.SCOPES` now requests `yt-analytics.readonly`. **An existing token
  does not gain this retroactively** — see the action list below.
- Standout bar lowered to 2.0x with a 120-view floor (both still editable in
  Settings).
- `follow_up_spawned` now filtered in Python, treating `NULL` as "not spawned".
- Migration `009` adds `hook_style`, `hook_text`, `word_count`, `pacing`,
  `publish_slot_hour`, `publish_attempts`, the three new `video_stats` columns,
  and the `insight_log` table.

---

## Problem 5 — Gemini never worked, so Groq wrote everything

You were right. Every single video card in your dashboard is badged
**"written by groq/backup"**. Two separate bugs, both fixed.

### Bug A — a dropped connection killed the whole video

Your queue has a FAILED card reading *"Server disconnected without sending a
response."*

`script_generator._call_model_with_clear_errors()` had exactly one `except`
clause: `except errors.APIError`. That covers errors Gemini *answered* with —
429, 503, 404. It does **not** cover the connection dying before any answer
arrives, which comes out of httpx as `RemoteProtocolError`, `ReadTimeout` or
`ConnectError`. None of those are `APIError` subclasses.

So the single most retryable failure there is escaped both the retry loop *and*
the Groq fallback, and killed a video five minutes into its render.

**Fixed:** a new `except _TRANSPORT_ERRORS` branch gives connection failures the
same treatment as a 503 — retry with backoff, then fall back to the backup chain.

### Bug B — the app kept picking a model your free key can't call

`model_registry.choose_text_model()` discovered every available model and picked
**the highest version number**. On a free key that is actively harmful:

> Google's newest Gemini models routinely ship with **no free tier at all**. A
> free key calling one gets `429 RESOURCE_EXHAUSTED` on the very first request
> of the day.

Then `api_budget.hard_stop()` read that 429 as "today's allowance is gone",
wrote `spent = daily_budget` into Supabase keyed on the Pacific date, and
**switched Gemini off for the entire day**. All six of that day's generate runs
went to Groq. And the model-discovery result is cached for 24 hours, so the bad
pick stuck.

On top of that, `DEFAULT_DAILY_BUDGET` was `20`. That figure belongs to the Pro
models. `gemini-2.5-flash` — the only kind this app calls — allows roughly
**250/day** free. At 20, the pacing counter declared the day over after about
the 9th writing call even when Google was perfectly happy to keep answering.

**Fixed:**
- New `FREE_TIER_PREFERRED` list. Models **known** to have a real free tier are
  chosen first, in our order of preference, not by version number. Version-number
  guessing is now the last resort and prefers the **oldest** Flash model, which
  is the most likely to still be free — the exact opposite of before.
- `DEFAULT_GEMINI_MODEL` changed from `gemini-3.5-flash` to `gemini-2.5-flash`.
- A 429 on one model now calls `model_registry.mark_model_exhausted()` and
  retries once on a *different* model before anything concludes the day is over.
- `DEFAULT_DAILY_BUDGET` raised 20 → 200.

Groq stays in the chain as a backup, which is what it was always meant to be.

---

## Problem 6 — Your YouTube token keeps dying (not a code bug)

One of your dashboard cards says:

> The YouTube refresh token was rejected (invalid_grant). The usual cause: your
> Google OAuth consent screen is still in 'Testing' status, and Google expires
> refresh tokens after 7 days in that state.

The app's error message is already correct and already tells you the fix. It is
not a code bug — it is a setting in Google Cloud, and it will keep breaking your
channel every 7 days until you change it. **It is the first thing on the action
list below.**

---

## Problem 7 — Keepalive was only doing half its job

It was supposed to do two things. It did one.

- **Keep the GitHub repo active** so GitHub doesn't auto-disable scheduled
  workflows after ~60 days. ✅ It did this.
- **Keep the Supabase project awake**, because free projects auto-pause after 7
  idle days. ❌ There was **no database call anywhere in the file.**

The cadence was also wrong for that second job in principle: running every 10
days cannot protect against a 7-day window.

**Fixed:** added a real Supabase query to `keepalive.yml`, and changed the
schedule from every 10 days to every 5, which covers both windows.

---

## Also added

- **OpenRouter** as the last link in the LLM fallback chain
  (`engine/openrouter_provider.py`). One free key reaches several free models,
  each tried in turn, so one retired model name can't take the link offline.
  Chain is now: Gemini → Groq → GitHub Models → OpenRouter.
- **GitLab CI backup scheduler** (`.gitlab-ci.yml`), **disabled by default** so
  it cannot double-post. See `docs/19_BACKUP_SCHEDULER_GITLAB.md`.
- `engine/step_summary.note()` so every run prints what it learned from your
  real numbers onto the Actions Summary tab.

Cloudflare R2 with delete-after-publish was **already** built and wired in
(`engine/storage_r2.py`). Nothing needed doing there.
