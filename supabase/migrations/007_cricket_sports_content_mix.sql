-- ============================================================================
-- 007_cricket_sports_content_mix.sql
--
-- Safe to run more than once. Every statement is additive or guarded.
-- Paste the whole file into Supabase -> SQL Editor -> Run.
--
-- WHAT THIS MIGRATION DOES
-- This app is a fork of a general-purpose multi-channel Shorts pipeline,
-- rebuilt into ONE single-purpose channel: cricket first (~85% of output),
-- other sports second (~15%) — see engine/sports_catalog.py and
-- engine/personas.py. This migration adds the handful of columns and
-- settings that single-purpose content-mix logic (engine/content_mix.py)
-- and the view/engagement feedback loop (engine/performance_loop.py) need,
-- and re-points the default channel and topic-synthesis setting at the new
-- 'cricket_and_sports' persona.
--
-- `archetype` already existed on `topics` (added in migration 002) — this
-- only adds the columns that did NOT already exist.
--
-- FIX (this version): section 5 originally did
--     INSERT INTO settings (key, value)
--     SELECT 'auto_topic_personas', 'cricket_and_sports'
--     WHERE NOT EXISTS (...) OR (SELECT value FROM settings WHERE key = '...') = ''
-- The OR branch meant the INSERT still ran even when the row already
-- existed (with value = '', which migration 003 sets), so it hit the
-- primary key on settings.key and the whole script got rolled back. It's
-- now a single INSERT ... ON CONFLICT upsert that only overwrites an
-- empty/missing value — same intent, no duplicate-key error, and a value
-- you've since typed into Settings yourself is still left alone.
-- ============================================================================


-- ── 1. New topic columns for the 85/15 split and content-mix scoring ───────
-- sport            'cricket' | 'other_sport' — what content_mix.py splits on.
-- sub_sport        only set when sport = 'other_sport' (e.g. 'hockey', 'kabaddi').
-- engagement_tier  'high' | 'standard' — an editorial STARTING GUESS at which
--                  topics travel best, used to seed content_mix.py's daily
--                  slot planner before any real analytics exist for a topic.
--                  performance_loop.py overrides this with real view/like/
--                  share data the moment a topic's video actually publishes
--                  and gets measured (see that module's effective_engagement_
--                  tier()) — this column is only ever the FALLBACK guess.
-- quiz_friendly    true if the topic naturally ends in a good "guess the
--                  related stat" close (engine/engagement.py's quiz mechanic).

ALTER TABLE topics ADD COLUMN IF NOT EXISTS sport           TEXT DEFAULT 'cricket';
ALTER TABLE topics ADD COLUMN IF NOT EXISTS sub_sport       TEXT;
ALTER TABLE topics ADD COLUMN IF NOT EXISTS engagement_tier TEXT DEFAULT 'standard';
ALTER TABLE topics ADD COLUMN IF NOT EXISTS quiz_friendly   BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_topics_sport ON topics (sport);


-- ── 2. video_stats: the real-world performance feedback loop ───────────────
-- One row per (video, time a stats snapshot was pulled from the YouTube
-- Analytics/Data API). Kept as a HISTORY, not a single overwritten row, so
-- performance_loop.py can see a video's trajectory (a video with 500 views
-- after 1 day and climbing is a different signal than one flat at 500 views
-- after a week) rather than just its latest number.

CREATE TABLE IF NOT EXISTS video_stats (
    id              BIGSERIAL PRIMARY KEY,
    video_id        BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    views           BIGINT DEFAULT 0,
    likes           BIGINT DEFAULT 0,
    comments        BIGINT DEFAULT 0,
    shares          BIGINT DEFAULT 0,
    -- A single 0-100 engagement score computed at fetch time (see
    -- performance_loop.py's score_video()) so the dashboard and the
    -- follow-up-spawning logic don't each reimplement the same formula.
    engagement_score FLOAT,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_video_stats_video_id ON video_stats (video_id);
CREATE INDEX IF NOT EXISTS idx_video_stats_fetched_at ON video_stats (fetched_at DESC);

ALTER TABLE video_stats ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "authenticated_all_video_stats" ON video_stats;
CREATE POLICY "authenticated_all_video_stats" ON video_stats
    FOR ALL TO authenticated USING (true) WITH CHECK (true);


-- ── 3. Track which published videos already spawned a follow-up ────────────
-- Stops a single viral video from spawning a new "similar" topic every time
-- performance_loop.py runs — it should trigger once per video, not once per
-- run for as long as that video stays a top performer.

ALTER TABLE videos ADD COLUMN IF NOT EXISTS follow_up_spawned BOOLEAN DEFAULT FALSE;


-- ── 4. Content-mix / performance-loop settings ──────────────────────────────

INSERT INTO settings (key, value, description)
SELECT * FROM (VALUES
    ('content_mix_cricket_pct', '85',
     'Target % of generated videos that are cricket vs other sports. See engine/content_mix.py.'),
    ('content_mix_winner_ratio', '0.5',
     'Fraction of each day''s batch reserved for predicted high-engagement topics (the rest is variety). 0.5 with a 4-video day = 2 predicted winners + 2 other topics, per the original spec.'),
    ('performance_loop_enabled', 'true',
     'If true, the analytics-sync workflow scores published videos and can spawn similar (not identical) follow-up topics from genuine standouts. See engine/performance_loop.py.'),
    ('performance_loop_view_multiplier', '3',
     'A video counts as a "standout" worth a follow-up when its views are at least this many times the channel''s own recent average — not a fixed number, since a brand-new channel''s "good" view count is not the same as an established one''s.'),
    ('performance_loop_min_views', '200',
     'A floor below the multiplier check — stops a follow-up firing on a 3-view video just because the channel average happens to be 1 view.')
) AS v(key, value, description)
WHERE NOT EXISTS (SELECT 1 FROM settings WHERE settings.key = v.key);


-- ── 5. Point topic synthesis and the default channel at the new persona ────
-- Migration 003 cleared the old seeded 'tech_science_explainer' value so it
-- would stop silently blocking other personas. This app has exactly one
-- persona, so setting it explicitly here is correct (not the same mistake —
-- there is no second persona for this value to block).
--
-- Single upsert instead of a plain guarded INSERT: if the row already
-- exists with value = '' (which migration 003 leaves it as), a bare INSERT
-- would still attempt to insert and collide with the settings primary key.
-- ON CONFLICT lets us update in that exact case while still leaving a
-- value you've since typed into Settings yourself untouched.

INSERT INTO settings (key, value)
VALUES ('auto_topic_personas', 'cricket_and_sports')
ON CONFLICT (key) DO UPDATE
    SET value = EXCLUDED.value
    WHERE settings.value = '' OR settings.value IS NULL;

-- The default catchall channel seeded in migration 002 carried the old
-- 10-archetype v19 category list and no persona. Re-point it at this app's
-- one persona and its real archetype set (see engine/archetypes.py's
-- SPORTS_ARCHETYPES) — guarded so a channel you've since renamed or
-- reconfigured by hand is left alone.
UPDATE channels
SET persona_key = 'cricket_and_sports',
    categories = ARRAY['records_and_stats','player_story','where_are_they_now',
                        'unsung_history','history_deep_dive','rules_explainer',
                        'business_and_governance','quiz_challenge','informative',
                        'myth_busting'],
    name = 'Cricket & Sports Shorts'
WHERE name = 'Main Channel' AND persona_key IS NULL;
