-- ============================================================================
-- 008_thumbnails_visual_dedup_and_fixes.sql
--
-- Safe to run more than once. Every statement is additive or guarded.
-- Paste the whole file into Supabase -> SQL Editor -> Run.
--
-- WHAT THIS MIGRATION DOES (all from the same round of real-world feedback:
-- videos were re-using the exact same stock clip/photo across unrelated
-- videos, the app had no thumbnails, auto-approve was effectively dead, and
-- a topic that failed once could fail forever burning the daily AI budget)
--
--   1. videos.thumbnail_url      — where the generated thumbnail lives.
--   2. topics.fail_count         — consecutive generation failures; a topic
--      that keeps failing (e.g. it keeps tripping a content filter) is
--      auto-deactivated instead of being retried forever.
--   3. visual_usage              — NEW TABLE. Every specific photo/clip
--      actually used in a published-or-pending video, so the next video can
--      be told "don't use this exact asset again" even though it's a
--      completely different video asking a similar search query. This is
--      the fix for the same England/clip/photo repeating across unrelated
--      videos — the old code only avoided repeats WITHIN one video.
--   4. New settings: voice default, peak-posting-hours, thumbnail toggle.
-- ============================================================================


-- ── 1. Thumbnail storage ────────────────────────────────────────────────────
ALTER TABLE videos ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;


-- ── 2. Auto-retire a topic that keeps failing ───────────────────────────────
-- Incremented in engine/orchestrator.py's _log_failure(); topic_synthesizer/
-- orchestrator deactivate the topic once this crosses TOPIC_MAX_FAILURES
-- (see orchestrator.py) so the same doomed topic can't burn AI-call budget
-- and fill the Failed tab with the same error forever.
ALTER TABLE topics ADD COLUMN IF NOT EXISTS fail_count INT DEFAULT 0;


-- ── 3. Cross-video visual-asset usage history ───────────────────────────────
-- One row per scene's resolved visual asset, written right after a video
-- renders (see engine/orchestrator.py's _record_visual_usage). `identifier`
-- is whatever uniquely names the actual asset for that source — a Pexels
-- video id, a Wikimedia file title, a Pixabay id, or (for a plain keyword
-- search with nothing more specific) the search keyword itself. Looked up
-- again before the NEXT video fetches visuals, so the same real photo/clip
-- doesn't show up in video after video just because two different scripts
-- both searched for "England cricket team celebrating".
CREATE TABLE IF NOT EXISTS visual_usage (
    id          BIGSERIAL PRIMARY KEY,
    job_id      TEXT NOT NULL,
    source      TEXT NOT NULL,   -- pexels | wikimedia | pixabay | ai_generated
    identifier  TEXT NOT NULL,   -- pexels video id / wikimedia file title / pixabay id / keyword
    used_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_visual_usage_source_identifier
    ON visual_usage (source, identifier);
CREATE INDEX IF NOT EXISTS idx_visual_usage_used_at ON visual_usage (used_at DESC);

ALTER TABLE visual_usage ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "authenticated_all_visual_usage" ON visual_usage;
CREATE POLICY "authenticated_all_visual_usage" ON visual_usage
    FOR ALL TO authenticated USING (true) WITH CHECK (true);


-- ── 4. New settings ──────────────────────────────────────────────────────────
INSERT INTO settings (key, value, description)
SELECT * FROM (VALUES
    ('generate_thumbnails', 'true',
     'If true, a custom thumbnail is generated for every video and uploaded automatically alongside it. See engine/thumbnail_generator.py.'),
    ('publish_use_peak_hours', 'true',
     'If true, the publish schedule prefers the Indian-audience peak windows in publish_peak_hours_ist over strict even spacing (still never exceeds the daily cap). See engine/channels.py.'),
    ('publish_peak_hours_ist', '7-10,12-14,18-23',
     'Comma-separated IST hour ranges (24h, start-end) to prefer for publishing — commute, lunch and evening windows when this channel''s mostly-Indian cricket audience is actually on YouTube. Edit freely.'),
    ('topic_max_failures', '3',
     'A topic is automatically deactivated (and you get an alert) after this many consecutive generation failures, so one cursed topic can''t keep burning AI-call budget and filling the Failed tab forever.')
) AS v(key, value, description)
WHERE NOT EXISTS (SELECT 1 FROM settings WHERE settings.key = v.key);


-- ── 5. Voice default: the old single hardcoded value gets replaced with an
-- Indian-English option better suited to this channel's audience. Only
-- applied if nobody has already picked something in Settings.
UPDATE settings SET value = 'indian_male'
WHERE key = 'voice_profile' AND value = 'documentary_male';
