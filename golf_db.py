import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Use data/ directory for Docker compatibility, fallback to local for development
# Docker mounts ./data to /app/data, so we check if that directory exists
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
if os.path.exists(DATA_DIR):
    SQLITE_DB_PATH = os.path.join(DATA_DIR, "golf_stats.db")
else:
    # Fallback for local development (non-Docker)
    SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "golf_stats.db")

# Initialize Supabase client
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None
    print("Warning: Supabase credentials not found. Cloud sync disabled.")

# --- Helper Functions ---
def clean_value(val, default=0.0):
    """Handle sentinel values (99999) and None."""
    if val is None or val == 99999:
        return default
    return val

# --- SQLite Local Database ---
def init_db():
    """Initialize the local SQLite database and handle migrations."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shots (
            shot_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_date TEXT,
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
            optix_x REAL,
            optix_y REAL,
            club_lie REAL,
            lie_angle TEXT
        )
    ''')

    # Migration: Add missing columns if table already existed
    cursor.execute("PRAGMA table_info(shots)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    required_columns = {
        'session_date': 'TEXT',
        'optix_x': 'REAL',
        'optix_y': 'REAL',
        'club_lie': 'REAL',
        'lie_angle': 'TEXT',
        'video_frames': 'TEXT',  # Comma-separated list of video frame URLs
        # NEW COLUMNS (Dec 2024 expansion)
        'sensor_name': 'TEXT',  # Launch monitor model
        'client_shot_id': 'TEXT',  # Device shot number
        'server_timestamp': 'TEXT',  # Server upload timestamp
        'is_deleted': 'TEXT',  # Soft delete flag
        'ball_name': 'TEXT',  # Ball compression
        'ball_type': 'TEXT',  # Ball type code
        'club_name_std': 'TEXT',  # Standardized club name
        'club_type': 'TEXT',  # Club type code
        'client_session_id': 'TEXT',  # Device session ID
        'low_point': 'REAL'  # Estimated low point (inches)
    }

    for col, col_type in required_columns.items():
        if col not in existing_columns:
            print(f"Migrating: Adding column {col} to SQLite")
            cursor.execute(f"ALTER TABLE shots ADD COLUMN {col} {col_type}")

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_session_id ON shots(session_id)')
    conn.commit()
    conn.close()

# --- Hybrid Save (Local + Cloud) ---
def save_shot(data):
    """Save shot data to local SQLite and Supabase (hybrid)."""
    
    # Prepare unified payload
    payload = {
        'shot_id': data.get('id', data.get('shot_id')),
        'session_id': data.get('session', data.get('session_id')),
        'session_date': data.get('session_date'),  # Actual practice date from Uneekor
        'club': data.get('club'),
        'carry': clean_value(data.get('carry', data.get('carry_distance'))),
        'total': clean_value(data.get('total', data.get('total_distance'))),
        'smash': clean_value(data.get('smash', 0.0)),
        'club_path': clean_value(data.get('club_path')),
        'face_angle': clean_value(data.get('face_angle', data.get('club_face_angle'))),
        'ball_speed': clean_value(data.get('ball_speed')),
        'club_speed': clean_value(data.get('club_speed')),
        'side_spin': clean_value(data.get('side_spin'), 0),
        'back_spin': clean_value(data.get('back_spin'), 0),
        'launch_angle': clean_value(data.get('launch_angle')),
        'side_angle': clean_value(data.get('side_angle')),
        'dynamic_loft': clean_value(data.get('dynamic_loft')),
        'attack_angle': clean_value(data.get('attack_angle')),
        'impact_x': clean_value(data.get('impact_x')),
        'impact_y': clean_value(data.get('impact_y')),
        'side_distance': clean_value(data.get('side_distance')),
        'descent_angle': clean_value(data.get('descent_angle', data.get('decent_angle'))),
        'apex': clean_value(data.get('apex')),
        'flight_time': clean_value(data.get('flight_time')),
        'shot_type': data.get('shot_type', data.get('type')),
        'impact_img': data.get('impact_img'),
        'swing_img': data.get('swing_img'),
        'video_frames': data.get('video_frames'),  # Comma-separated list of video frame URLs
        # New advanced metrics
        'optix_x': clean_value(data.get('optix_x')),
        'optix_y': clean_value(data.get('optix_y')),
        'club_lie': clean_value(data.get('club_lie')),
        'lie_angle': data.get('lie_angle') if data.get('lie_angle') else None,
        # NEW: Additional metrics (Dec 2024)
        'sensor_name': data.get('sensor_name'),
        'client_shot_id': data.get('client_shot_id'),
        'server_timestamp': data.get('server_timestamp'),
        'is_deleted': data.get('is_deleted', 'N'),
        'ball_name': data.get('ball_name'),
        'ball_type': data.get('ball_type'),
        'club_name_std': data.get('club_name_std'),
        'club_type': data.get('club_type'),
        'client_session_id': data.get('client_session_id'),
        'low_point': clean_value(data.get('low_point'))
    }

    # 1. Save to Local SQLite
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        columns = ', '.join(payload.keys())
        placeholders = ', '.join(['?'] * len(payload))
        sql = f"INSERT OR REPLACE INTO shots ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, list(payload.values()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Error: {e}")

    # 2. Save to Supabase (if available)
    if supabase:
        try:
            supabase.table('shots').upsert(payload).execute()
        except Exception as e:
            print(f"Supabase Error: {e}")

# --- Data Retrieval (Local-First) ---
def get_session_data(session_id=None):
    """Get session data from local SQLite database."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        query = "SELECT * FROM shots"
        if session_id:
            query += f" WHERE session_id = ?"
            df = pd.read_sql_query(query, conn, params=[session_id])
        else:
            df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"SQLite Read Error: {e}")
        return pd.DataFrame()

def get_unique_sessions():
    """Get unique sessions from local SQLite database with session dates."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        query = """
            SELECT DISTINCT
                session_id,
                MAX(session_date) as session_date,
                MAX(date_added) as date_added,
                MAX(club) as club
            FROM shots
            GROUP BY session_id
            ORDER BY COALESCE(session_date, date_added) DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict('records')
    except Exception as e:
        print(f"SQLite Session Error: {e}")
        return []

# --- Data Management ---
def delete_shot(shot_id):
    """Delete a specific shot from local SQLite and Supabase."""
    # Local
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM shots WHERE shot_id = ?", (shot_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Delete Error: {e}")
    
    # Cloud
    if supabase:
        try:
            supabase.table('shots').delete().eq('shot_id', shot_id).execute()
        except Exception as e:
            print(f"Supabase Delete Error: {e}")

def rename_club(session_id, old_name, new_name):
    """Rename all instances of a club within a session."""
    # Local
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE shots SET club = ? WHERE session_id = ? AND club = ?", (new_name, session_id, old_name))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Rename Error: {e}")
    
    # Cloud
    if supabase:
        try:
            supabase.table('shots').update({'club': new_name}).eq('session_id', session_id).eq('club', old_name).execute()
        except Exception as e:
            print(f"Supabase Rename Error: {e}")

def delete_club_session(session_id, club_name):
    """Delete all shots for a specific club within a session."""
    # Local
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM shots WHERE session_id = ? AND club = ?", (session_id, club_name))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Club Delete Error: {e}")
    
    # Cloud
    if supabase:
        try:
            supabase.table('shots').delete().eq('session_id', session_id).eq('club', club_name).execute()
        except Exception as e:
            print(f"Supabase Club Delete Error: {e}")