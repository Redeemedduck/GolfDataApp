-- Supabase Schema for Golf Shot Data
-- Run this in your Supabase SQL Editor after creating your project

-- Create shots table with comprehensive golf metrics
CREATE TABLE shots (
    shot_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    date_added TIMESTAMPTZ DEFAULT NOW(),
    club TEXT,
    carry REAL,
    total REAL,
    smash REAL,
    club_path REAL,
    face_angle REAL,
    ball_speed REAL,
    club_speed REAL,
    side_spin INTEGER,
    back_spin INTEGER,
    launch_angle REAL,
    side_angle REAL,
    dynamic_loft REAL,
    attack_angle REAL,
    impact_x REAL,
    impact_y REAL,
    side_distance REAL,
    descent_angle REAL,
    apex REAL,
    flight_time REAL,
    shot_type TEXT,
    impact_img TEXT,
    swing_img TEXT,
    -- Advanced Optix Metrics (added for Club/Impact visualization)
    optix_x REAL,
    optix_y REAL,
    club_lie REAL,
    lie_angle TEXT
);

-- Create index on session_id for faster queries
CREATE INDEX idx_shots_session_id ON shots(session_id);

-- Create index on date_added for time-series queries
CREATE INDEX idx_shots_date_added ON shots(date_added);

-- Create index on club for club-specific analysis
CREATE INDEX idx_shots_club ON shots(club);

-- Enable Row Level Security (RLS)
ALTER TABLE shots ENABLE ROW LEVEL SECURITY;

-- Create policy to allow authenticated users to read all shots
CREATE POLICY "Allow authenticated users to read shots"
ON shots FOR SELECT
TO authenticated
USING (true);

-- Create policy to allow authenticated users to insert shots
CREATE POLICY "Allow authenticated users to insert shots"
ON shots FOR INSERT
TO authenticated
WITH CHECK (true);

-- Create policy to allow authenticated users to update shots
CREATE POLICY "Allow authenticated users to update shots"
ON shots FOR UPDATE
TO authenticated
USING (true);

-- Create policies for anonymous (anon) role
-- These are needed because the app uses the anon key, not authenticated sessions
CREATE POLICY "Allow anon to read shots"
ON shots FOR SELECT
TO anon
USING (true);

CREATE POLICY "Allow anon to insert shots"
ON shots FOR INSERT
TO anon
WITH CHECK (true);

CREATE POLICY "Allow anon to update shots"
ON shots FOR UPDATE
TO anon
USING (true);

CREATE POLICY "Allow anon to delete shots"
ON shots FOR DELETE
TO anon
USING (true);

-- Optional: Create a view for session summaries
CREATE OR REPLACE VIEW session_summary AS
SELECT
    session_id,
    club,
    COUNT(*) as shot_count,
    AVG(carry) as avg_carry,
    AVG(total) as avg_total,
    AVG(smash) as avg_smash,
    AVG(ball_speed) as avg_ball_speed,
    AVG(club_speed) as avg_club_speed,
    AVG(back_spin) as avg_back_spin,
    AVG(launch_angle) as avg_launch_angle,
    MIN(date_added) as session_start,
    MAX(date_added) as session_end
FROM shots
GROUP BY session_id, club
ORDER BY session_start DESC;
