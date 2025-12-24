import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "golf_stats.db")

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
        'optix_x': 'REAL',
        'optix_y': 'REAL',
        'club_lie': 'REAL',
        'lie_angle': 'TEXT'
    }

    for col, col_type in required_columns.items():
        if col not in existing_columns:
            print(f"Migrating: Adding column {col} to SQLite")
            cursor.execute(f"ALTER TABLE shots ADD COLUMN {col} {col_type}")

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_session_id ON shots(session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_date_added ON shots(date_added)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_club ON shots(club)')
    conn.commit()
    conn.close()

# --- Data Storage (SQLite Only) ---
def save_shot(data):
    """Save shot data to local SQLite database."""

    # Prepare unified payload
    payload = {
        'shot_id': data.get('id', data.get('shot_id')),
        'session_id': data.get('session', data.get('session_id')),
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
        # Advanced metrics
        'optix_x': clean_value(data.get('optix_x')),
        'optix_y': clean_value(data.get('optix_y')),
        'club_lie': clean_value(data.get('club_lie')),
        'lie_angle': data.get('lie_angle') if data.get('lie_angle') else None
    }

    # Save to Local SQLite
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
        raise

# --- Data Retrieval ---
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
    """Get unique sessions from local SQLite database."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        query = "SELECT DISTINCT session_id, MAX(date_added) as date_added FROM shots GROUP BY session_id ORDER BY date_added DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict('records')
    except Exception as e:
        print(f"SQLite Session Error: {e}")
        return []

# --- Data Management ---
def delete_shot(shot_id):
    """Delete a specific shot from local SQLite."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM shots WHERE shot_id = ?", (shot_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Delete Error: {e}")
        raise

def rename_club(session_id, old_name, new_name):
    """Rename all instances of a club within a session."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE shots SET club = ? WHERE session_id = ? AND club = ?", (new_name, session_id, old_name))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Rename Error: {e}")
        raise

def delete_club_session(session_id, club_name):
    """Delete all shots for a specific club within a session."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM shots WHERE session_id = ? AND club = ?", (session_id, club_name))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Club Delete Error: {e}")
        raise

# --- BigQuery Sync (Optional - for cloud analytics only) ---
def get_all_shots_for_sync():
    """
    Get all shots from SQLite for BigQuery sync.
    Used by scripts/sqlite_to_bigquery.py for cloud analytics.
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        df = pd.read_sql_query("SELECT * FROM shots ORDER BY date_added DESC", conn)
        conn.close()
        return df
    except Exception as e:
        print(f"SQLite Read Error: {e}")
        return pd.DataFrame()
