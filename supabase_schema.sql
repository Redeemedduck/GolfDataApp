-- =============================================================================
-- Supabase Schema for GolfDataApp
-- =============================================================================
-- Canonical reference for the Supabase (Postgres) schema.
-- Run the full file in SQL Editor for a fresh project, or use the
-- "Migration for existing deployments" section at the bottom.
--
-- Project: Uneekor (lhccrzxgnmynxmvoydkm)
-- Last synced: 2026-01-27
-- =============================================================================
-- Note: The sync_audit table exists only in local SQLite and is not part of
-- this Supabase schema.


-- =============================================================================
-- 1. SHOTS — Core shot data (30+ metrics per shot)
-- =============================================================================

CREATE TABLE IF NOT EXISTS shots (
    shot_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    date_added TIMESTAMPTZ DEFAULT NOW(),
    session_date TIMESTAMPTZ,
    session_type TEXT,
    club TEXT,
    carry DOUBLE PRECISION,
    total DOUBLE PRECISION,
    smash DOUBLE PRECISION,
    club_path DOUBLE PRECISION,
    face_angle DOUBLE PRECISION,
    ball_speed DOUBLE PRECISION,
    club_speed DOUBLE PRECISION,
    side_spin INTEGER,
    back_spin INTEGER,
    launch_angle DOUBLE PRECISION,
    side_angle DOUBLE PRECISION,
    dynamic_loft DOUBLE PRECISION,
    attack_angle DOUBLE PRECISION,
    impact_x DOUBLE PRECISION,
    impact_y DOUBLE PRECISION,
    side_distance DOUBLE PRECISION,
    descent_angle DOUBLE PRECISION,
    apex DOUBLE PRECISION,
    flight_time DOUBLE PRECISION,
    shot_type TEXT,
    impact_img TEXT,
    swing_img TEXT,
    optix_x REAL,
    optix_y REAL,
    club_lie REAL,
    lie_angle TEXT,
    shot_tag TEXT
);

CREATE INDEX IF NOT EXISTS idx_shots_session_id ON shots(session_id);
CREATE INDEX IF NOT EXISTS idx_shots_session_date ON shots(session_date);
CREATE INDEX IF NOT EXISTS idx_shots_date_added ON shots(date_added);
CREATE INDEX IF NOT EXISTS idx_shots_club ON shots(club);

ALTER TABLE shots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anon read access on shots"
ON shots FOR SELECT TO anon USING (true);

CREATE POLICY "Service role full access on shots"
ON shots FOR ALL TO service_role USING (true) WITH CHECK (true);


-- =============================================================================
-- 2. TAG_CATALOG — Shared tag definitions for session labeling
-- =============================================================================

CREATE TABLE IF NOT EXISTS tag_catalog (
    tag TEXT PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_default INTEGER DEFAULT 0
);

ALTER TABLE tag_catalog ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anon read access on tag_catalog"
ON tag_catalog FOR SELECT TO anon USING (true);

CREATE POLICY "Service role full access on tag_catalog"
ON tag_catalog FOR ALL TO service_role USING (true) WITH CHECK (true);


-- =============================================================================
-- 3. SHOTS_ARCHIVE — Soft-deleted shots for recovery
-- =============================================================================

CREATE TABLE IF NOT EXISTS shots_archive (
    shot_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_reason TEXT,
    original_data TEXT
);

ALTER TABLE shots_archive ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on shots_archive"
ON shots_archive FOR ALL TO service_role USING (true) WITH CHECK (true);


-- =============================================================================
-- 4. CHANGE_LOG — Audit trail for data modifications
-- =============================================================================

CREATE TABLE IF NOT EXISTS change_log (
    log_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    operation TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details TEXT
);

ALTER TABLE change_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on change_log"
ON change_log FOR ALL TO service_role USING (true) WITH CHECK (true);


-- =============================================================================
-- 5. AUTOMATION TABLES — Scraper operational state
-- =============================================================================
-- These tables track Playwright scraper state. They exist in Supabase for
-- durability but are primarily written by the automation module.

-- 5a. sessions_discovered — Discovered Uneekor portal sessions
CREATE TABLE IF NOT EXISTS sessions_discovered (
    report_id TEXT PRIMARY KEY,
    api_key TEXT NOT NULL,
    portal_name TEXT,
    session_date TIMESTAMPTZ,
    date_source TEXT,
    shot_count_expected INTEGER,
    clubs_json TEXT,
    source_url TEXT,
    discovered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    import_status TEXT DEFAULT 'pending',
    import_started_at TIMESTAMPTZ,
    import_completed_at TIMESTAMPTZ,
    import_shots_actual INTEGER,
    import_error TEXT,
    skip_reason TEXT,
    last_checked_at TIMESTAMPTZ,
    checksum TEXT,
    priority INTEGER DEFAULT 0,
    session_name TEXT,
    session_type TEXT,
    tags_json TEXT,
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sessions_discovered_date ON sessions_discovered(session_date);
CREATE INDEX IF NOT EXISTS idx_sessions_discovered_status ON sessions_discovered(import_status);

ALTER TABLE sessions_discovered ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on sessions_discovered"
ON sessions_discovered FOR ALL TO service_role USING (true) WITH CHECK (true);


-- 5b. automation_runs — High-level automation run tracking
CREATE TABLE IF NOT EXISTS automation_runs (
    run_id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',
    sessions_discovered INTEGER DEFAULT 0,
    sessions_imported INTEGER DEFAULT 0,
    sessions_skipped INTEGER DEFAULT 0,
    sessions_failed INTEGER DEFAULT 0,
    total_shots_imported INTEGER DEFAULT 0,
    trigger_source TEXT,
    error_log TEXT,
    duration_seconds DOUBLE PRECISION,
    config_json TEXT
);

ALTER TABLE automation_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on automation_runs"
ON automation_runs FOR ALL TO service_role USING (true) WITH CHECK (true);


-- 5c. backfill_runs — Backfill progress with checkpointing
CREATE TABLE IF NOT EXISTS backfill_runs (
    run_id TEXT PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',
    config_json TEXT,
    target_date_start DATE,
    target_date_end DATE,
    clubs_filter TEXT,
    sessions_total INTEGER DEFAULT 0,
    sessions_processed INTEGER DEFAULT 0,
    sessions_imported INTEGER DEFAULT 0,
    sessions_skipped INTEGER DEFAULT 0,
    sessions_failed INTEGER DEFAULT 0,
    total_shots INTEGER DEFAULT 0,
    last_processed_report_id TEXT,
    last_checkpoint_at TIMESTAMPTZ,
    error_log TEXT
);

ALTER TABLE backfill_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on backfill_runs"
ON backfill_runs FOR ALL TO service_role USING (true) WITH CHECK (true);


-- =============================================================================
-- 6. VIEWS
-- =============================================================================

CREATE OR REPLACE VIEW session_summary AS
SELECT
    session_id,
    club,
    COUNT(*) AS shot_count,
    AVG(carry) AS avg_carry,
    AVG(total) AS avg_total,
    AVG(smash) AS avg_smash,
    AVG(ball_speed) AS avg_ball_speed,
    AVG(club_speed) AS avg_club_speed,
    AVG(back_spin) AS avg_back_spin,
    AVG(launch_angle) AS avg_launch_angle,
    MIN(date_added) AS session_start,
    MAX(date_added) AS session_end,
    MIN(session_date) AS session_date
FROM shots
GROUP BY session_id, club
ORDER BY session_start DESC;


-- =============================================================================
-- 7. MIGRATION — For existing deployments
-- =============================================================================
-- If upgrading from an older schema, run these statements individually.
-- Each uses IF NOT EXISTS / OR REPLACE so they are safe to re-run.
--
-- Step 1: Add session_date to shots (if missing)
--   ALTER TABLE shots ADD COLUMN IF NOT EXISTS session_date TIMESTAMPTZ;
--   CREATE INDEX IF NOT EXISTS idx_shots_session_date ON shots(session_date);
--
-- Step 2: Add missing indexes
--   CREATE INDEX IF NOT EXISTS idx_shots_date_added ON shots(date_added);
--   CREATE INDEX IF NOT EXISTS idx_shots_club ON shots(club);
--
-- Step 3: Create shots_archive (run the CREATE TABLE from section 3)
--
-- Step 4: Create change_log (run the CREATE TABLE from section 4)
--
-- Step 5: Update session_summary view (run the CREATE OR REPLACE VIEW from section 6)
