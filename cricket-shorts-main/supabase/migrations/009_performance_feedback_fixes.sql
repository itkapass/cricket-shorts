-- ============================================================================
-- 009 — Make the performance feedback loop actually possible
-- ============================================================================
-- Everything in this file exists because of one finding in the audit:
-- the app was collecting analytics and then comparing them against nothing.
--
-- Part 5 asks to "compare performance across topic type, specific person/event
-- featured, script opening-hook style, script length/pacing, and publish time
-- slot". Three of those five were never recorded anywhere. No amount of
-- analysis code could have worked, because the inputs did not exist. This
-- migration adds them.
--
-- Safe to run on an existing database: every statement is IF NOT EXISTS or an
-- idempotent UPDATE. It does not delete or rewrite any existing data.
-- ============================================================================

-- ── 1. Script-decision metadata, written at generation time ────────────────
-- Filled by engine/insights.classify(), which labels every script the same
-- way forever so that last month's labels and this month's are comparable.
ALTER TABLE videos ADD COLUMN IF NOT EXISTS hook_style  TEXT;    -- question | statement | command | number
ALTER TABLE videos ADD COLUMN IF NOT EXISTS hook_text   TEXT;    -- the actual opening line, for eyeballing
ALTER TABLE videos ADD COLUMN IF NOT EXISTS word_count  INTEGER; -- total spoken words
ALTER TABLE videos ADD COLUMN IF NOT EXISTS pacing      TEXT;    -- slow | medium | fast

-- ── 2. Publish-slot metadata, written at publish time ──────────────────────
-- Stored as an IST hour label ('22:00'), not UTC, because the audience is
-- Indian and the whole point of the column is human-readable slot comparison.
ALTER TABLE videos ADD COLUMN IF NOT EXISTS publish_slot_hour TEXT;

-- ── 3. Publish retry counter ───────────────────────────────────────────────
-- 'publish_failed' and 'needs_manual' were terminal statuses: nothing in the
-- entire codebase ever moved a row out of them. A video that hit one
-- momentary 503 on upload was finished — written, rendered, stored, and never
-- published, with no trace in any count. That is a direct cause of the
-- "generated != published" gap. engine/publish_approved._revive_retryable_failures()
-- now retries those, and this column is what stops a retry becoming a loop.
ALTER TABLE videos ADD COLUMN IF NOT EXISTS publish_attempts INTEGER DEFAULT 0;

-- ── 4. Richer stats, from the YouTube ANALYTICS API ────────────────────────
-- performance_loop.py could only read the Data API, which exposes views,
-- likes and comments and nothing else — `shares` was hardcoded to 0 with a
-- comment saying so. The two most useful Shorts signals were invisible:
--   avg_view_percentage — how far through the video people actually get.
--                         This channel's own Studio shows 58.7% on one video
--                         and 54.8% on another; that gap says far more than
--                         the view counts beside it.
--   subscribers_gained  — the only metric that tracks channel growth per video.
-- NULL means "not measured", never "zero" — engine/insights.py depends on that
-- distinction, because a fabricated 0% retention would poison every comparison.
ALTER TABLE video_stats ADD COLUMN IF NOT EXISTS avg_view_percentage NUMERIC;
ALTER TABLE video_stats ADD COLUMN IF NOT EXISTS avg_view_duration   INTEGER;
ALTER TABLE video_stats ADD COLUMN IF NOT EXISTS subscribers_gained  INTEGER;

-- ── 5. insight_log — the auditable record of what the system changed, and why ─
-- Part 5: "log what the system decided to change and why, so it's auditable,
-- not a black box." Every finding engine/insights.py acts on lands here with
-- the numbers and the sample size behind it, so there is always a readable
-- answer to "why did the channel start writing hooks like this".
CREATE TABLE IF NOT EXISTS insight_log (
    id           BIGSERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    dimension    TEXT NOT NULL,    -- hook_style | pacing | archetype | publish_slot ...
    metric       TEXT NOT NULL,    -- views | engagement_score | avg_view_percentage
    winner       TEXT,
    winner_avg   NUMERIC,
    winner_n     INTEGER,
    loser        TEXT,
    loser_avg    NUMERIC,
    loser_n      INTEGER,
    lift         NUMERIC,          -- winner_avg / loser_avg
    applied_to   TEXT,             -- script_generation | topic_synthesis
    sample_size  INTEGER           -- total measured videos the finding came from
);

CREATE INDEX IF NOT EXISTS idx_insight_log_created ON insight_log (created_at DESC);
ALTER TABLE insight_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "authenticated_all_insight_log" ON insight_log;
CREATE POLICY "authenticated_all_insight_log" ON insight_log
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- ── 6. Heal the rows the approved_at bug already stranded ───────────────────
-- orchestrator.py set status='approved' without ever setting approved_at
-- (only the dashboard wrote that column). publish_approved.py then ordered by
-- `approved_at ASC`, and PostgreSQL sorts NULLs LAST — so with
-- publish_per_run = 1, every auto-approved video sat permanently behind every
-- hand-approved one and was never published at all. The code is fixed in both
-- places; this repairs the rows already stuck in the queue.
UPDATE videos
   SET approved_at = COALESCE(approved_at, created_at)
 WHERE status = 'approved' AND approved_at IS NULL;

-- Videos created before migration 007 have follow_up_spawned = NULL, and
-- `WHERE follow_up_spawned = false` never matches NULL in SQL — so those
-- videos were invisible to the follow-up loop forever, however well they
-- performed. The code now treats NULL as "not yet spawned"; this normalises
-- the existing data so both agree.
UPDATE videos SET follow_up_spawned = FALSE WHERE follow_up_spawned IS NULL;

-- ── 7. Recalibrate the standout bar ────────────────────────────────────────
-- At 3x the channel average with a 200-view floor, a video needed roughly 630
-- views to count as a standout on this channel. Four of its thirty-nine
-- published Shorts cleared that, so the follow-up loop almost never fired. A
-- learning loop that triggers on one video in ten teaches nothing.
UPDATE settings SET value = '2'
 WHERE key = 'performance_loop_view_multiplier' AND value = '3';
UPDATE settings SET value = '120'
 WHERE key = 'performance_loop_min_views' AND value = '200';

-- ── 8. Correct the Gemini daily budget ─────────────────────────────────────
-- The local pacing counter assumed ~20 requests/day. That figure belongs to
-- the Pro models; gemini-2.5-flash — the only kind this app calls — allows
-- roughly 250/day free. At 20, the tracker declared the day over after about
-- the 9th writing call and everything afterwards silently fell through to
-- Groq, which is exactly what the channel's "written by groq/backup" badges
-- were recording.
INSERT INTO settings (key, value, description) VALUES
    ('gemini_daily_budget', '200',
     'Local pacing guess for Gemini free-tier requests/day. gemini-2.5-flash allows ~250. Google''s own 429 is always the real authority.')
ON CONFLICT (key) DO NOTHING;

-- ── 9. Settings the dashboard reads for the new behaviour ───────────────────
INSERT INTO settings (key, value, description) VALUES
    ('publish_retry_enabled', 'true',
     'If true, videos that FAILED to upload for a transient reason (quota, 5xx, expired token) are returned to the approved queue and retried up to 3 times. Off means a single failed upload is permanent.')
ON CONFLICT (key) DO NOTHING;
