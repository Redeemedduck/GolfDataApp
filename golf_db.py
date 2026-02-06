import os
import sqlite3
from datetime import datetime
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from supabase import create_client, Client

from exceptions import ValidationError, DatabaseError

load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "golf_stats.db")

# Detect environment
IS_CLOUD_RUN = os.getenv('K_SERVICE') is not None
USE_SUPABASE_READS = os.getenv("USE_SUPABASE_READS", "").lower() in ("1", "true", "yes")
READ_MODE = "auto"

# Initialize Supabase client
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None
    print("Warning: Supabase credentials not found. Cloud sync disabled.")

# --- Helper Functions ---
def clean_value(val, default=None):
    """Handle sentinel values (99999) and None.

    Returns default (None) for missing/sentinel data so SQL AVG()
    naturally ignores these rows instead of counting them as 0.
    """
    if val is None or val == 99999:
        return default
    return val


# Columns where 0.0 is NOT a valid measurement — sentinels must become NULL
_ZERO_INVALID_COLUMNS = frozenset({
    'carry', 'total', 'ball_speed', 'club_speed', 'smash',
    'back_spin', 'launch_angle', 'apex', 'flight_time',
    'descent_angle', 'dynamic_loft',
})


def migrate_zeros_to_null():
    """Convert false-zero values back to NULL for columns where 0 is invalid.

    Fixes historical data corrupted by the old clean_value(default=0.0) bug.
    Columns like face_angle, club_path, impact_x/y where 0.0 means
    "neutral/centered" are left untouched.

    Returns:
        Dict with counts per column of rows updated.
    """
    results = {}
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        for col in _ZERO_INVALID_COLUMNS:
            cursor.execute(
                f"UPDATE shots SET {col} = NULL WHERE {col} = 0.0"
            )
            results[col] = cursor.rowcount

        conn.commit()

        total = sum(results.values())
        if total > 0:
            cursor.execute(
                "INSERT INTO change_log (operation, entity_type, entity_id, details) "
                "VALUES (?, ?, ?, ?)",
                ("MIGRATE_ZEROS", "shots", "all",
                 f"Converted {total} false-zeros to NULL across {len(results)} columns")
            )
            conn.commit()

        conn.close()
    except Exception as e:
        print(f"Migration Error: {e}")

    return results

def _normalize_read_mode(mode):
    if mode in ("auto", "sqlite", "supabase"):
        return mode
    return "auto"

def set_read_mode(mode):
    """Set the preferred read mode: auto, sqlite, or supabase."""
    global READ_MODE
    READ_MODE = _normalize_read_mode(mode)

def get_read_mode():
    return READ_MODE

# --- SQLite Local Database ---
def init_db():
    """Initialize the local SQLite database and handle migrations."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Enable WAL mode for better concurrent access
    # WAL (Write-Ahead Logging) allows readers and writers to operate simultaneously
    cursor.execute("PRAGMA journal_mode=WAL")

    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shots (
            shot_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_date TIMESTAMP,
            session_type TEXT,
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
        'lie_angle': 'TEXT',
        'shot_tag': 'TEXT',
        'session_type': 'TEXT',
        'session_date': 'TIMESTAMP',
        'face_to_path': 'REAL',
        'strike_distance': 'REAL',
    }
    
    for col, col_type in required_columns.items():
        if col not in existing_columns:
            print(f"Migrating: Adding column {col} to SQLite")
            cursor.execute(f"ALTER TABLE shots ADD COLUMN {col} {col_type}")

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_session_id ON shots(session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_session_date ON shots(session_date)')
    # Composite indexes for journal/club queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_session_club ON shots(session_id, club)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_date_club ON shots(session_date, club)')

    # Shared tag catalog
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tag_catalog (
            tag TEXT PRIMARY KEY,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_default INTEGER DEFAULT 0
        )
    ''')

    # Create archive table for deleted shots (audit trail)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shots_archive (
            shot_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_reason TEXT,
            original_data TEXT
        )
    ''')

    # Create change log table for tracking modifications
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS change_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            operation TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            details TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            records_synced INTEGER DEFAULT 0,
            records_failed INTEGER DEFAULT 0,
            error_message TEXT,
            details TEXT
        )
    ''')

    # Pre-computed session aggregates (eliminates N+1 queries)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_stats (
            session_id TEXT PRIMARY KEY,
            session_date TEXT,
            session_type TEXT,
            shot_count INTEGER DEFAULT 0,
            clubs_used TEXT,
            avg_carry REAL,
            avg_total REAL,
            avg_ball_speed REAL,
            avg_club_speed REAL,
            avg_smash REAL,
            best_carry REAL,
            avg_face_angle REAL,
            std_face_angle REAL,
            avg_club_path REAL,
            std_club_path REAL,
            avg_face_to_path REAL,
            avg_strike_distance REAL,
            std_strike_distance REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

    _ensure_default_tags()


def _ensure_default_tags():
    defaults = [
        ("Warmup", "Early warmup shots", 1),
        ("Practice", "Skill work or gapping", 1),
        ("Round", "On-course or simulator round play", 1),
        ("Fitting", "Equipment or shaft fitting", 1),
    ]
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        for tag, desc, is_default in defaults:
            cursor.execute(
                "INSERT OR IGNORE INTO tag_catalog (tag, description, is_default) VALUES (?, ?, ?)",
                (tag, desc, is_default)
            )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        # Log database errors but don't fail initialization
        print(f"Warning: Could not ensure default tags: {e}")

# --- Data Source Info ---
def get_read_source():
    """Return the preferred read source based on environment and configuration."""
    mode = _normalize_read_mode(READ_MODE)
    if mode == "sqlite":
        return "SQLite (forced)"
    if mode == "supabase":
        return "Supabase (forced)" if supabase else "SQLite (fallback)"
    if supabase and not _sqlite_has_data():
        return "Supabase (auto)"
    return "SQLite (auto)"

def _sqlite_has_data():
    try:
        if not os.path.exists(SQLITE_DB_PATH):
            return False
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM shots LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return row is not None
    except Exception:
        return False

def get_shot_counts():
    """Return shot counts for SQLite and Supabase."""
    counts = {"sqlite": 0, "supabase": 0}
    try:
        if os.path.exists(SQLITE_DB_PATH):
            conn = sqlite3.connect(SQLITE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM shots")
            counts["sqlite"] = cursor.fetchone()[0]
            conn.close()
    except Exception:
        pass

    if supabase:
        try:
            response = supabase.table('shots').select('shot_id', count='exact').execute()
            if hasattr(response, "count") and response.count is not None:
                counts["supabase"] = response.count
        except Exception:
            pass
    return counts


def get_sync_status(drift_threshold=0):
    """Return SQLite/Supabase drift information for reconciliation."""
    counts = get_shot_counts()
    drift = None
    drift_exceeds = False
    if supabase:
        drift = abs(counts["sqlite"] - counts["supabase"])
        drift_exceeds = drift > drift_threshold
    return {
        "counts": counts,
        "drift": drift,
        "drift_exceeds": drift_exceeds
    }


def get_tag_catalog(read_mode=None):
    """Return shared tags for consistent labeling across sessions."""
    mode = _normalize_read_mode(read_mode or READ_MODE)
    if mode == "supabase" and supabase:
        tags = _get_tag_catalog_supabase()
        if tags:
            return tags
    return _get_tag_catalog_sqlite()


def _get_tag_catalog_sqlite():
    _ensure_default_tags()
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT tag FROM tag_catalog ORDER BY tag ASC")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception:
        return []


def _get_tag_catalog_supabase():
    try:
        response = supabase.table('tag_catalog').select('tag').order('tag').execute()
        if hasattr(response, "data") and response.data:
            return [row["tag"] for row in response.data if row.get("tag")]
    except Exception:
        return []
    return []


def add_tag_to_catalog(tag, description=None):
    """Add or update a tag in the shared catalog."""
    tag = (tag or "").strip()
    if not tag:
        return False
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tag_catalog (tag, description) VALUES (?, ?) "
            "ON CONFLICT(tag) DO UPDATE SET description = excluded.description, updated_at = CURRENT_TIMESTAMP",
            (tag, description)
        )
        conn.commit()
        conn.close()
    except Exception:
        return False

    if supabase:
        try:
            supabase.table('tag_catalog').upsert(
                {'tag': tag, 'description': description}
            ).execute()
        except Exception:
            pass
    return True


def delete_tag_from_catalog(tag):
    """Remove a tag from the shared catalog."""
    tag = (tag or "").strip()
    if not tag:
        return False
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tag_catalog WHERE tag = ?", (tag,))
        conn.commit()
        conn.close()
    except Exception:
        return False

    if supabase:
        try:
            supabase.table('tag_catalog').delete().eq('tag', tag).execute()
        except Exception:
            pass
    return True

def _merge_shots(local_df, cloud_df):
    """Merge local and cloud shots, preferring local rows on conflicts."""
    if local_df.empty:
        return cloud_df
    if cloud_df.empty:
        return local_df
    if 'shot_id' not in local_df.columns or 'shot_id' not in cloud_df.columns:
        return pd.concat([local_df, cloud_df], ignore_index=True)
    combined = pd.concat([local_df, cloud_df], ignore_index=True)
    return combined.drop_duplicates(subset=['shot_id'], keep='first')

def _fetch_supabase_shots(session_id=None, page_size=1000):
    """Fetch shots from Supabase with pagination."""
    if not supabase:
        return pd.DataFrame()
    all_rows = []
    offset = 0
    while True:
        query = supabase.table('shots').select('*').range(offset, offset + page_size - 1)
        if session_id:
            query = query.eq('session_id', session_id)
        response = query.execute()
        data = response.data or []
        if not data:
            break
        all_rows.extend(data)
        if len(data) < page_size:
            break
        offset += page_size
    if not all_rows:
        return pd.DataFrame()
    df = pd.DataFrame(all_rows)
    if 'date_added' in df.columns:
        df['date_added'] = pd.to_datetime(df['date_added'])
    return df

def _fetch_supabase_sessions(page_size=1000):
    """Fetch session metadata from Supabase with pagination."""
    if not supabase:
        return pd.DataFrame()
    all_rows = []
    offset = 0
    while True:
        query = (
            supabase.table('shots')
            .select('session_id, date_added, session_type')
            .range(offset, offset + page_size - 1)
        )
        response = query.execute()
        data = response.data or []
        if not data:
            break
        all_rows.extend(data)
        if len(data) < page_size:
            break
        offset += page_size
    if not all_rows:
        return pd.DataFrame()
    df = pd.DataFrame(all_rows)
    if 'date_added' in df.columns:
        df['date_added'] = pd.to_datetime(df['date_added'])
    return df

# --- Hybrid Save (Local + Cloud) ---
def save_shot(data):
    """Save shot data to local SQLite and Supabase (hybrid).

    Args:
        data: Dict containing shot data. Must include 'id'/'shot_id' and 'session'/'session_id'.

    Raises:
        ValidationError: If shot_id or session_id is missing/null
    """
    # Validate required fields before any database operation
    shot_id = data.get('id', data.get('shot_id'))
    session_id = data.get('session', data.get('session_id'))

    if not shot_id:
        raise ValidationError(
            "shot_id is required",
            field='shot_id',
            value=shot_id
        )
    if not session_id:
        raise ValidationError(
            "session_id is required",
            field='session_id',
            value=session_id
        )

    # Prepare unified payload
    payload = {
        'shot_id': shot_id,
        'session_id': session_id,
        'session_date': data.get('session_date'),
        'session_type': data.get('session_type'),
        'club': data.get('club'),
        # Distance/speed metrics — 0 is invalid (NULL = no data captured)
        'carry': clean_value(data.get('carry', data.get('carry_distance'))),
        'total': clean_value(data.get('total', data.get('total_distance'))),
        'ball_speed': clean_value(data.get('ball_speed')),
        'club_speed': clean_value(data.get('club_speed')),
        'smash': clean_value(data.get('smash')),
        'launch_angle': clean_value(data.get('launch_angle')),
        'dynamic_loft': clean_value(data.get('dynamic_loft')),
        'descent_angle': clean_value(data.get('descent_angle', data.get('decent_angle'))),
        'apex': clean_value(data.get('apex')),
        'flight_time': clean_value(data.get('flight_time')),
        # Spin — 0 is valid (no spin)
        'side_spin': clean_value(data.get('side_spin'), 0),
        'back_spin': clean_value(data.get('back_spin'), 0),
        # Angles/position — 0 means neutral/centered (valid)
        'club_path': clean_value(data.get('club_path'), 0.0),
        'face_angle': clean_value(data.get('face_angle', data.get('club_face_angle')), 0.0),
        'attack_angle': clean_value(data.get('attack_angle'), 0.0),
        'side_angle': clean_value(data.get('side_angle'), 0.0),
        'side_distance': clean_value(data.get('side_distance'), 0.0),
        'impact_x': clean_value(data.get('impact_x'), 0.0),
        'impact_y': clean_value(data.get('impact_y'), 0.0),
        'shot_type': data.get('shot_type', data.get('type')),
        'impact_img': data.get('impact_img'),
        'swing_img': data.get('swing_img'),
        # Advanced metrics — 0 means centered (valid)
        'optix_x': clean_value(data.get('optix_x'), 0.0),
        'optix_y': clean_value(data.get('optix_y'), 0.0),
        'club_lie': clean_value(data.get('club_lie')),
        'lie_angle': data.get('lie_angle') if data.get('lie_angle') else None,
        'shot_tag': data.get('shot_tag')
    }

    # Compute derived columns
    face = payload.get('face_angle')
    path = payload.get('club_path')
    if face is not None and path is not None:
        payload['face_to_path'] = round(face - path, 2)
    else:
        payload['face_to_path'] = None

    ix = payload.get('impact_x')
    iy = payload.get('impact_y')
    if ix is not None and iy is not None:
        import math
        payload['strike_distance'] = round(math.sqrt(ix ** 2 + iy ** 2), 4)
    else:
        payload['strike_distance'] = None

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
def get_session_data(session_id=None, read_mode=None):
    """Get session data from local SQLite database, with fallback to Supabase."""
    df = pd.DataFrame()

    def fetch_from_sqlite():
        try:
            if os.path.exists(SQLITE_DB_PATH):
                conn = sqlite3.connect(SQLITE_DB_PATH)
                query = "SELECT * FROM shots"
                if session_id:
                    query += " WHERE session_id = ?"
                    local_df = pd.read_sql_query(query, conn, params=[session_id])
                else:
                    local_df = pd.read_sql_query(query, conn)
                conn.close()
                return local_df
        except Exception as e:
            print(f"SQLite Read Error: {e}")
        return pd.DataFrame()

    def fetch_from_supabase():
        try:
            return _fetch_supabase_shots(session_id=session_id)
        except Exception as e:
            print(f"Supabase Read Error: {e}")
            return pd.DataFrame()

    mode = _normalize_read_mode(read_mode or READ_MODE)
    prefer_supabase = supabase and (USE_SUPABASE_READS or IS_CLOUD_RUN or mode == "supabase")

    local_df = fetch_from_sqlite()
    if mode == "supabase":
        cloud_df = fetch_from_supabase()
        return cloud_df if not cloud_df.empty else local_df

    if mode == "sqlite":
        return local_df

    if not local_df.empty:
        return local_df

    if supabase:
        return fetch_from_supabase()

    if prefer_supabase:
        return fetch_from_supabase()

    return local_df

def get_all_shots(read_mode=None):
    """Get all shots from the local SQLite database, with Supabase fallback."""
    return get_session_data(read_mode=read_mode)

def get_unique_sessions(read_mode=None):
    """Get unique sessions from local SQLite, optionally merged with Supabase."""
    local_df = pd.DataFrame()
    cloud_df = pd.DataFrame()

    try:
        if os.path.exists(SQLITE_DB_PATH):
            conn = sqlite3.connect(SQLITE_DB_PATH)
            query = (
                "SELECT session_id, MAX(date_added) as date_added, MAX(session_type) as session_type "
                "FROM shots GROUP BY session_id ORDER BY date_added DESC"
            )
            local_df = pd.read_sql_query(query, conn)
            conn.close()
    except Exception as e:
        print(f"SQLite Session Error: {e}")

    mode = _normalize_read_mode(read_mode or READ_MODE)
    should_check_cloud = supabase and (USE_SUPABASE_READS or IS_CLOUD_RUN or mode == "supabase" or local_df.empty)
    if should_check_cloud:
        try:
            cloud_df = _fetch_supabase_sessions()
            if not cloud_df.empty:
                def _last_non_null(series):
                    non_null = series.dropna()
                    return non_null.iloc[-1] if not non_null.empty else None

                cloud_df = cloud_df.sort_values('date_added')
                cloud_df = (
                    cloud_df.groupby('session_id')
                    .agg(
                        date_added=('date_added', 'max'),
                        session_type=('session_type', _last_non_null)
                    )
                    .reset_index()
                )
        except Exception as e:
            print(f"Supabase Session Error: {e}")

    if local_df.empty and cloud_df.empty:
        return []

    if mode == "supabase":
        return cloud_df.to_dict('records') if not cloud_df.empty else local_df.to_dict('records')

    if mode == "sqlite":
        return local_df.to_dict('records')

    if not local_df.empty:
        return local_df.to_dict('records')

    combined = pd.concat([local_df, cloud_df], ignore_index=True)
    combined['date_added'] = pd.to_datetime(combined['date_added'])
    combined = combined.sort_values('date_added')
    combined = (
        combined.groupby('session_id')
        .agg(
            date_added=('date_added', 'max'),
            session_type=('session_type', lambda x: x.dropna().iloc[-1] if not x.dropna().empty else None)
        )
        .reset_index()
        .sort_values('date_added', ascending=False)
    )
    return combined.to_dict('records')

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

def delete_shots_by_tag(session_id, tag):
    """Delete all shots for a specific tag within a session."""
    deleted = 0
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM shots WHERE session_id = ? AND shot_tag = ?",
            (session_id, tag)
        )
        deleted = cursor.rowcount
        conn.commit()
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ("DELETE_BY_TAG", "session", session_id, f"Deleted {deleted} shots tagged '{tag}'")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Tag Delete Error: {e}")

    if supabase:
        try:
            supabase.table('shots').delete().eq('session_id', session_id).eq('shot_tag', tag).execute()
        except Exception as e:
            print(f"Supabase Tag Delete Error: {e}")

    return deleted


# ============================================================================
# SESSION-LEVEL OPERATIONS (Phase 2)
# ============================================================================

def delete_session(session_id, archive=True):
    """
    Delete an entire session from local SQLite and Supabase.

    Args:
        session_id: Session identifier to delete
        archive: If True, archive shots before deletion (default: True)

    Returns:
        Number of shots deleted
    """
    import json

    # Get shots for archival
    shots_to_delete = get_session_data(session_id)
    shot_count = len(shots_to_delete)

    if archive and shot_count > 0:
        # Archive to shots_archive
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            cursor = conn.cursor()

            for _, shot in shots_to_delete.iterrows():
                original_data = shot.to_dict()
                cursor.execute(
                    "INSERT OR REPLACE INTO shots_archive (shot_id, session_id, deleted_reason, original_data) VALUES (?, ?, ?, ?)",
                    (shot['shot_id'], session_id, f"Session deletion: {session_id}", json.dumps(original_data, default=str))
                )

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Archive Error: {e}")

    # Delete from local
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM shots WHERE session_id = ?", (session_id,))
        conn.commit()

        # Log the deletion
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ("DELETE", "session", session_id, f"Deleted {shot_count} shots")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Delete Session Error: {e}")

    # Archive to cloud before deleting
    if supabase and archive and shot_count > 0:
        try:
            for _, shot in shots_to_delete.iterrows():
                original_data = shot.to_dict()
                supabase.table('shots_archive').upsert({
                    'shot_id': shot['shot_id'],
                    'session_id': session_id,
                    'deleted_reason': f"Session deletion: {session_id}",
                    'original_data': json.dumps(original_data, default=str)
                }).execute()
        except Exception as e:
            print(f"Supabase Archive Error: {e}")

    # Delete from cloud
    if supabase:
        try:
            supabase.table('shots').delete().eq('session_id', session_id).execute()
        except Exception as e:
            print(f"Supabase Delete Session Error: {e}")

    return shot_count


def merge_sessions(session_ids, new_session_id):
    """
    Merge multiple sessions into one unified session.

    Args:
        session_ids: List of session IDs to merge
        new_session_id: New session ID for merged data

    Returns:
        Number of shots merged
    """
    total_shots = 0

    # Local
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        for old_session_id in session_ids:
            cursor.execute("UPDATE shots SET session_id = ? WHERE session_id = ?", (new_session_id, old_session_id))
            total_shots += cursor.rowcount

        conn.commit()

        # Log the merge
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ("MERGE", "session", new_session_id, f"Merged sessions: {', '.join(session_ids)}")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Merge Error: {e}")

    # Cloud
    if supabase:
        try:
            for old_session_id in session_ids:
                supabase.table('shots').update({'session_id': new_session_id}).eq('session_id', old_session_id).execute()
        except Exception as e:
            print(f"Supabase Merge Error: {e}")

    return total_shots


def split_session(session_id, shot_ids, new_session_id):
    """
    Move specific shots from one session to a new session.

    Args:
        session_id: Original session ID
        shot_ids: List of shot IDs to move
        new_session_id: New session ID for moved shots

    Returns:
        Number of shots moved
    """
    # Guard against empty shot_ids (would cause SQL syntax error)
    if not shot_ids:
        return 0

    # Local
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        # Update session_id for specified shots
        placeholders = ','.join(['?'] * len(shot_ids))
        cursor.execute(
            f"UPDATE shots SET session_id = ? WHERE shot_id IN ({placeholders})",
            [new_session_id] + shot_ids
        )
        shots_moved = cursor.rowcount

        conn.commit()

        # Log the split
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ("SPLIT", "session", session_id, f"Moved {shots_moved} shots to {new_session_id}")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Split Error: {e}")
        shots_moved = 0

    # Cloud
    if supabase:
        try:
            for shot_id in shot_ids:
                supabase.table('shots').update({'session_id': new_session_id}).eq('shot_id', shot_id).execute()
        except Exception as e:
            print(f"Supabase Split Error: {e}")

    return shots_moved


def rename_session(old_session_id, new_session_id):
    """
    Rename a session (change session_id for all shots).

    Args:
        old_session_id: Current session ID
        new_session_id: New session ID

    Returns:
        Number of shots updated
    """
    # Local
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE shots SET session_id = ? WHERE session_id = ?", (new_session_id, old_session_id))
        shots_updated = cursor.rowcount
        conn.commit()

        # Log the rename
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ("RENAME", "session", new_session_id, f"Renamed from {old_session_id}")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Rename Session Error: {e}")
        shots_updated = 0

    # Cloud
    if supabase:
        try:
            supabase.table('shots').update({'session_id': new_session_id}).eq('session_id', old_session_id).execute()
        except Exception as e:
            print(f"Supabase Rename Session Error: {e}")

    return shots_updated


# ============================================================================
# SESSION METADATA
# ============================================================================

def update_session_type(session_id, session_type):
    """Update session_type for all shots in a session."""
    session_type = (session_type or "").strip() or None
    updated = 0
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE shots SET session_type = ? WHERE session_id = ?",
            (session_type, session_id)
        )
        updated = cursor.rowcount
        conn.commit()
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ("SESSION_TYPE", "session", session_id, f"Set session_type = {session_type}")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Session Type Error: {e}")
        updated = 0

    if supabase:
        try:
            supabase.table('shots').update({'session_type': session_type}).eq('session_id', session_id).execute()
        except Exception as e:
            print(f"Supabase Session Type Error: {e}")

    return updated


# ============================================================================
# BULK EDITING FUNCTIONS (Phase 2)
# ============================================================================

# Allowlist of fields that can be updated via update_shot_metadata
# This prevents SQL injection by validating the field name
ALLOWED_UPDATE_FIELDS = frozenset({
    'shot_tag',      # For tagging shots
    'session_type',  # For categorizing sessions
    'club',          # For correcting club assignments
    'session_id',    # For moving shots between sessions
    'shot_type',     # For shot classification
    'session_date',  # For correcting session dates
})


def update_shot_metadata(shot_ids, field, value):
    """
    Bulk update a specific field for multiple shots.

    Args:
        shot_ids: List of shot IDs to update
        field: Column name to update (must be in ALLOWED_UPDATE_FIELDS)
        value: New value for the field

    Returns:
        Number of shots updated

    Raises:
        ValueError: If field is not in the allowlist
    """
    # SECURITY: Validate field name against allowlist to prevent SQL injection
    if field not in ALLOWED_UPDATE_FIELDS:
        raise ValueError(
            f"Invalid field '{field}'. Allowed fields: {', '.join(sorted(ALLOWED_UPDATE_FIELDS))}"
        )

    # Local
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        placeholders = ','.join(['?'] * len(shot_ids))
        # Field is now validated, safe to interpolate
        cursor.execute(
            f"UPDATE shots SET {field} = ? WHERE shot_id IN ({placeholders})",
            [value] + shot_ids
        )
        shots_updated = cursor.rowcount
        conn.commit()

        # Log the update
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ("UPDATE", "shot", f"{len(shot_ids)} shots", f"Set {field} = {value}")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Bulk Update Error: {e}")
        shots_updated = 0

    # Cloud
    if supabase:
        try:
            for shot_id in shot_ids:
                supabase.table('shots').update({field: value}).eq('shot_id', shot_id).execute()
        except Exception as e:
            print(f"Supabase Bulk Update Error: {e}")

    return shots_updated

def update_shot_tags(shot_ids, tag):
    """Bulk update shot_tag for multiple shots."""
    if not shot_ids:
        return 0
    return update_shot_metadata(shot_ids, "shot_tag", tag)

def split_session_by_tag(session_id, tag, new_session_id):
    """Split a session into a new session using a tag filter."""
    shots_moved = 0
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE shots SET session_id = ? WHERE session_id = ? AND shot_tag = ?",
            (new_session_id, session_id, tag)
        )
        shots_moved = cursor.rowcount
        conn.commit()
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            (
                "SPLIT_BY_TAG",
                "session",
                session_id,
                f"Moved {shots_moved} shots tagged '{tag}' to {new_session_id}. "
                f"Undo: move tag '{tag}' from {new_session_id} back to {session_id}."
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Split by Tag Error: {e}")
        shots_moved = 0

    if supabase:
        try:
            supabase.table('shots').update({'session_id': new_session_id}).eq('session_id', session_id).eq('shot_tag', tag).execute()
        except Exception as e:
            print(f"Supabase Split by Tag Error: {e}")

    return shots_moved


def recalculate_metrics(session_id=None):
    """
    Recompute derived metrics (smash factor) and clean invalid data.

    Args:
        session_id: Optional session ID to limit recalculation (None = all shots)

    Returns:
        Number of shots updated
    """
    # Get shots to recalculate
    df = get_session_data(session_id) if session_id else get_session_data()
    if df.empty:
        return 0

    shots_updated = 0

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        df_updates = df.copy()
        exclude_cols = [
            'shot_id', 'session_id', 'date_added', 'club',
            'shot_type', 'impact_img', 'swing_img', 'lie_angle'
        ]
        update_cols = [col for col in df_updates.columns if col not in exclude_cols]

        numeric_cols = df_updates[update_cols].select_dtypes(include=['number']).columns
        df_updates[numeric_cols] = df_updates[numeric_cols].replace(99999, 0).fillna(0)

        if 'ball_speed' in df_updates.columns and 'club_speed' in df_updates.columns and 'smash' in df_updates.columns:
            df_updates['smash'] = 0.0
            valid_speed = df_updates['club_speed'] > 0
            df_updates.loc[valid_speed, 'smash'] = (
                df_updates.loc[valid_speed, 'ball_speed'] / df_updates.loc[valid_speed, 'club_speed']
            ).round(2)

        if update_cols:
            set_clause = ', '.join([f"{col} = ?" for col in update_cols])
            values = df_updates[update_cols + ['shot_id']].values.tolist()
            cursor.executemany(
                f"UPDATE shots SET {set_clause} WHERE shot_id = ?",
                values
            )
            shots_updated = len(values)

        conn.commit()

        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ("RECALCULATE", "shot", session_id or "all", f"Recalculated {shots_updated} shots")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Recalculate Error: {e}")

    return shots_updated


def bulk_rename_clubs(old_name, new_name):
    """
    Rename a club across ALL sessions (not just one).

    Args:
        old_name: Current club name
        new_name: New club name

    Returns:
        Number of shots updated
    """
    # Local
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE shots SET club = ? WHERE club = ?", (new_name, old_name))
        shots_updated = cursor.rowcount
        conn.commit()

        # Log the rename
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ("RENAME", "club", new_name, f"Renamed '{old_name}' across all sessions")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Bulk Rename Error: {e}")
        shots_updated = 0

    # Cloud
    if supabase:
        try:
            supabase.table('shots').update({'club': new_name}).eq('club', old_name).execute()
        except Exception as e:
            print(f"Supabase Bulk Rename Error: {e}")

    return shots_updated


# ============================================================================
# DATA QUALITY TOOLS (Phase 2)
# ============================================================================

def find_outliers(session_id=None, club=None):
    """
    Detect shots with unrealistic values.

    Args:
        session_id: Optional session ID to filter
        club: Optional club name to filter

    Returns:
        DataFrame of outlier shots with reasons
    """
    df = get_session_data(session_id)

    if df.empty:
        return pd.DataFrame()

    # Filter by club if specified
    if club:
        df = df[df['club'] == club]

    reasons_df = pd.DataFrame(index=df.index)

    if 'carry' in df.columns:
        reasons_df['carry'] = np.where(
            df['carry'] > 400,
            df['carry'].map(lambda v: f"Carry too high: {v:.0f} yds"),
            ""
        )
    if 'smash' in df.columns:
        reasons_df['smash_high'] = np.where(
            df['smash'] > 1.6,
            df['smash'].map(lambda v: f"Smash too high: {v:.2f}"),
            ""
        )
        reasons_df['smash_low'] = np.where(
            (df['smash'] > 0) & (df['smash'] < 0.8),
            df['smash'].map(lambda v: f"Smash too low: {v:.2f}"),
            ""
        )
    if 'ball_speed' in df.columns:
        reasons_df['ball_speed'] = np.where(
            df['ball_speed'] > 200,
            df['ball_speed'].map(lambda v: f"Ball speed too high: {v:.0f} mph"),
            ""
        )
    if 'back_spin' in df.columns:
        reasons_df['back_spin'] = np.where(
            df['back_spin'] > 10000,
            df['back_spin'].map(lambda v: f"Back spin too high: {v:.0f} rpm"),
            ""
        )
    if 'side_spin' in df.columns:
        reasons_df['side_spin'] = np.where(
            df['side_spin'].abs() > 5000,
            df['side_spin'].map(lambda v: f"Side spin excessive: {v:.0f} rpm"),
            ""
        )

    if reasons_df.empty:
        return pd.DataFrame()

    def join_reasons(row):
        return '; '.join([val for val in row if val])

    reason_series = reasons_df.apply(join_reasons, axis=1)
    outlier_rows = df[reason_series != ""].copy()
    outlier_rows['reasons'] = reason_series[reason_series != ""]

    return outlier_rows[['shot_id', 'session_id', 'club', 'carry', 'smash', 'ball_speed', 'reasons']]


def validate_shot_data(session_id=None):
    """
    Find shots missing critical fields.

    Returns:
        DataFrame of invalid shots with missing fields
    """
    df = get_session_data(session_id)

    if df.empty:
        return pd.DataFrame()

    critical_fields = ['ball_speed', 'club_speed', 'carry', 'total', 'club']
    invalid_shots = []

    for _, shot in df.iterrows():
        missing_fields = []

        for field in critical_fields:
            value = shot.get(field)
            if pd.isna(value) or value == 0 or value == '':
                missing_fields.append(field)

        if missing_fields:
            invalid_shots.append({
                'shot_id': shot['shot_id'],
                'session_id': shot['session_id'],
                'club': shot.get('club', 'Unknown'),
                'missing_fields': ', '.join(missing_fields)
            })

    return pd.DataFrame(invalid_shots)


def deduplicate_shots():
    """
    Remove exact duplicates by shot_id.

    Returns:
        Number of duplicates removed
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        # Find duplicates (shouldn't happen due to PRIMARY KEY, but check anyway)
        cursor.execute("""
            SELECT shot_id, COUNT(*) as count
            FROM shots
            GROUP BY shot_id
            HAVING count > 1
        """)

        duplicates = cursor.fetchall()
        removed = 0

        for shot_id, count in duplicates:
            # Keep the first, delete the rest (shouldn't be reachable with PRIMARY KEY)
            cursor.execute("""
                DELETE FROM shots
                WHERE rowid NOT IN (
                    SELECT MIN(rowid)
                    FROM shots
                    WHERE shot_id = ?
                )
            """, (shot_id,))
            removed += cursor.rowcount

        conn.commit()

        # Log deduplication
        if removed > 0:
            cursor.execute(
                "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
                ("DEDUPLICATE", "shot", "multiple", f"Removed {removed} duplicates")
            )
            conn.commit()

        conn.close()
    except Exception as e:
        print(f"Deduplicate Error: {e}")
        removed = 0

    return removed


# ============================================================================
# AUDIT TRAIL FUNCTIONS (Phase 2)
# ============================================================================

# Allowlist of valid columns for restore operation (security: prevent SQL injection)
ALLOWED_RESTORE_COLUMNS = frozenset({
    'shot_id', 'session_id', 'date_added', 'session_date', 'session_type',
    'club', 'carry', 'total', 'smash', 'club_path', 'face_angle',
    'ball_speed', 'club_speed', 'side_spin', 'back_spin', 'launch_angle',
    'side_angle', 'dynamic_loft', 'attack_angle', 'impact_x', 'impact_y',
    'side_distance', 'descent_angle', 'apex', 'flight_time', 'shot_type',
    'impact_img', 'swing_img', 'optix_x', 'optix_y', 'club_lie', 'lie_angle',
    'shot_tag', 'face_to_path', 'strike_distance',
})


def restore_deleted_shots(shot_ids):
    """
    Restore previously deleted shots from archive.

    Args:
        shot_ids: List of shot IDs to restore

    Returns:
        Number of shots restored

    Raises:
        ValidationError: If archived data contains invalid column names
    """
    import json

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        restored = 0
        for shot_id in shot_ids:
            # Get archived data
            cursor.execute("SELECT original_data FROM shots_archive WHERE shot_id = ?", (shot_id,))
            row = cursor.fetchone()

            if row:
                original_data = json.loads(row[0])

                # Security: Validate column names against allowlist
                invalid_keys = set(original_data.keys()) - ALLOWED_RESTORE_COLUMNS
                if invalid_keys:
                    raise ValidationError(
                        f"Invalid columns in archived data: {invalid_keys}",
                        field='columns',
                        value=list(invalid_keys)
                    )

                # Restore to shots table (columns now validated)
                columns = ', '.join(original_data.keys())
                placeholders = ', '.join(['?'] * len(original_data))
                cursor.execute(
                    f"INSERT OR REPLACE INTO shots ({columns}) VALUES ({placeholders})",
                    list(original_data.values())
                )

                # Remove from archive
                cursor.execute("DELETE FROM shots_archive WHERE shot_id = ?", (shot_id,))
                restored += 1

        conn.commit()

        # Log restoration
        if restored > 0:
            cursor.execute(
                "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
                ("RESTORE", "shot", f"{restored} shots", f"Restored from archive")
            )
            conn.commit()

        conn.close()
    except Exception as e:
        print(f"Restore Error: {e}")
        restored = 0

    return restored


def get_change_log(session_id=None, limit=50):
    """
    Retrieve change history log.

    Args:
        session_id: Optional session ID to filter logs
        limit: Maximum number of log entries to return

    Returns:
        DataFrame of change log entries
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)

        if session_id:
            query = "SELECT * FROM change_log WHERE entity_id = ? ORDER BY timestamp DESC LIMIT ?"
            df = pd.read_sql_query(query, conn, params=[session_id, limit])
        else:
            query = "SELECT * FROM change_log ORDER BY timestamp DESC LIMIT ?"
            df = pd.read_sql_query(query, conn, params=[limit])

        conn.close()
        return df
    except Exception as e:
        print(f"Change Log Error: {e}")
        return pd.DataFrame()


def get_archived_shots(session_id=None):
    """
    Get list of archived (deleted) shots.

    Args:
        session_id: Optional session ID to filter

    Returns:
        DataFrame of archived shots
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)

        if session_id:
            query = "SELECT * FROM shots_archive WHERE session_id = ? ORDER BY deleted_at DESC"
            df = pd.read_sql_query(query, conn, params=[session_id])
        else:
            query = "SELECT * FROM shots_archive ORDER BY deleted_at DESC"
            df = pd.read_sql_query(query, conn)

        conn.close()
        return df
    except Exception as e:
        print(f"Archive Retrieval Error: {e}")
        return pd.DataFrame()


# ============================================================================
# SESSION DATE MANAGEMENT
# ============================================================================

def backfill_session_dates():
    """
    Update shots.session_date from sessions_discovered table.

    This function copies session_date values from the sessions_discovered
    tracking table to the shots table, enabling accurate date-based analytics.

    Returns:
        Dict with counts: {'updated': int, 'skipped': int, 'errors': int}
    """
    result = {'updated': 0, 'skipped': 0, 'errors': 0}

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        # Get sessions with known dates from sessions_discovered
        cursor.execute('''
            SELECT report_id, session_date
            FROM sessions_discovered
            WHERE session_date IS NOT NULL
        ''')
        sessions_with_dates = cursor.fetchall()

        for report_id, session_date in sessions_with_dates:
            try:
                # Update all shots for this session
                cursor.execute('''
                    UPDATE shots
                    SET session_date = ?
                    WHERE session_id = ?
                    AND (session_date IS NULL OR session_date = '')
                ''', (session_date, report_id))

                if cursor.rowcount > 0:
                    result['updated'] += cursor.rowcount
                else:
                    result['skipped'] += 1

            except Exception as e:
                print(f"Error updating session {report_id}: {e}")
                result['errors'] += 1

        conn.commit()

        # Log the backfill
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ("BACKFILL_DATES", "shots", "multiple",
             f"Updated {result['updated']} shots with session dates")
        )
        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Backfill Session Dates Error: {e}")
        result['errors'] += 1

    return result


def backfill_derived_columns():
    """Compute face_to_path and strike_distance for all existing shots.

    Returns:
        Number of shots updated.
    """
    import math

    updated = 0
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT shot_id, face_angle, club_path, impact_x, impact_y
            FROM shots
            WHERE face_to_path IS NULL OR strike_distance IS NULL
        ''')
        rows = cursor.fetchall()

        for shot_id, face, path, ix, iy in rows:
            ftp = round(face - path, 2) if face is not None and path is not None else None
            sd = round(math.sqrt(ix ** 2 + iy ** 2), 4) if ix is not None and iy is not None else None

            cursor.execute(
                "UPDATE shots SET face_to_path = ?, strike_distance = ? WHERE shot_id = ?",
                (ftp, sd, shot_id)
            )
            updated += 1

        conn.commit()

        if updated > 0:
            cursor.execute(
                "INSERT INTO change_log (operation, entity_type, entity_id, details) "
                "VALUES (?, ?, ?, ?)",
                ("BACKFILL_DERIVED", "shots", "all",
                 f"Computed face_to_path and strike_distance for {updated} shots")
            )
            conn.commit()

        conn.close()
    except Exception as e:
        print(f"Backfill Derived Columns Error: {e}")

    return updated


# ============================================================================
# SESSION STATS CACHE
# ============================================================================

def compute_session_stats(session_id=None):
    """Compute and cache aggregated stats for sessions.

    Args:
        session_id: Optional — recompute one session. None = recompute all.

    Returns:
        Number of sessions updated.
    """
    updated = 0
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        if session_id:
            session_ids = [session_id]
        else:
            cursor.execute("SELECT DISTINCT session_id FROM shots")
            session_ids = [row[0] for row in cursor.fetchall()]

        for sid in session_ids:
            cursor.execute('''
                SELECT
                    COUNT(*) as shot_count,
                    GROUP_CONCAT(DISTINCT club) as clubs_used,
                    AVG(carry) as avg_carry,
                    AVG(total) as avg_total,
                    AVG(ball_speed) as avg_ball_speed,
                    AVG(club_speed) as avg_club_speed,
                    AVG(smash) as avg_smash,
                    MAX(carry) as best_carry,
                    AVG(face_angle) as avg_face_angle,
                    AVG((face_angle - (SELECT AVG(face_angle) FROM shots WHERE session_id = ?)) *
                        (face_angle - (SELECT AVG(face_angle) FROM shots WHERE session_id = ?))) as var_face,
                    AVG(club_path) as avg_club_path,
                    AVG((club_path - (SELECT AVG(club_path) FROM shots WHERE session_id = ?)) *
                        (club_path - (SELECT AVG(club_path) FROM shots WHERE session_id = ?))) as var_path,
                    AVG(face_to_path) as avg_face_to_path,
                    AVG(strike_distance) as avg_strike_distance,
                    AVG((strike_distance - (SELECT AVG(strike_distance) FROM shots WHERE session_id = ?)) *
                        (strike_distance - (SELECT AVG(strike_distance) FROM shots WHERE session_id = ?))) as var_strike,
                    MAX(session_date) as session_date,
                    MAX(session_type) as session_type
                FROM shots
                WHERE session_id = ?
            ''', (sid, sid, sid, sid, sid, sid, sid))

            row = cursor.fetchone()
            if row and row[0] > 0:
                import math
                std_face = math.sqrt(row[9]) if row[9] is not None else None
                std_path = math.sqrt(row[11]) if row[11] is not None else None
                std_strike = math.sqrt(row[14]) if row[14] is not None else None

                cursor.execute('''
                    INSERT OR REPLACE INTO session_stats
                    (session_id, session_date, session_type, shot_count, clubs_used,
                     avg_carry, avg_total, avg_ball_speed, avg_club_speed, avg_smash,
                     best_carry, avg_face_angle, std_face_angle, avg_club_path,
                     std_club_path, avg_face_to_path, avg_strike_distance,
                     std_strike_distance, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    sid, row[15], row[16], row[0], row[1],
                    row[2], row[3], row[4], row[5], row[6],
                    row[7], row[8], std_face, row[10],
                    std_path, row[12], row[13],
                    std_strike,
                ))
                updated += 1

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Compute Session Stats Error: {e}")

    return updated


def get_recent_sessions_with_stats(weeks=4):
    """Get recent sessions with pre-computed stats for the journal view.

    Single query, no N+1. Returns sessions from the last `weeks` weeks.

    Args:
        weeks: Number of weeks to look back (default 4).

    Returns:
        List of dicts with session stats.
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT *
            FROM session_stats
            WHERE session_date >= date('now', ? || ' days')
               OR session_date IS NULL
            ORDER BY COALESCE(session_date, '9999-99-99') DESC
        ''', (str(-weeks * 7),))

        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"Get Recent Sessions Error: {e}")
        return []


def get_session_aggregates(session_id):
    """Get Big 3 + performance stats for a single session.

    Returns:
        Dict with all session stats, or empty dict if not found.
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM session_stats WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
    except Exception as e:
        print(f"Get Session Aggregates Error: {e}")

    return {}


def get_club_profile(club_name):
    """Get per-club performance story over time.

    Args:
        club_name: Club to profile (e.g., "Driver", "7 Iron").

    Returns:
        DataFrame with per-session aggregates for this club, ordered by date.
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        df = pd.read_sql_query('''
            SELECT
                session_id,
                session_date,
                COUNT(*) as shot_count,
                AVG(carry) as avg_carry,
                AVG(total) as avg_total,
                AVG(ball_speed) as avg_ball_speed,
                AVG(smash) as avg_smash,
                MAX(carry) as best_carry,
                AVG(face_angle) as avg_face_angle,
                AVG(club_path) as avg_club_path,
                AVG(face_to_path) as avg_face_to_path,
                AVG(strike_distance) as avg_strike_distance
            FROM shots
            WHERE club = ?
            GROUP BY session_id, session_date
            ORDER BY COALESCE(session_date, date_added) ASC
        ''', conn, params=[club_name])
        conn.close()
        return df
    except Exception as e:
        print(f"Get Club Profile Error: {e}")
        return pd.DataFrame()


def get_rolling_averages(club=None, window=5):
    """Get rolling average baselines for comparison.

    Args:
        club: Optional club filter. None = all clubs.
        window: Number of most recent sessions to average.

    Returns:
        Dict with rolling avg metrics.
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        if club:
            cursor.execute('''
                SELECT
                    AVG(carry) as avg_carry,
                    AVG(ball_speed) as avg_ball_speed,
                    AVG(smash) as avg_smash,
                    AVG(face_angle) as avg_face,
                    AVG(club_path) as avg_path,
                    AVG(strike_distance) as avg_strike
                FROM (
                    SELECT carry, ball_speed, smash, face_angle, club_path, strike_distance
                    FROM shots
                    WHERE club = ?
                    ORDER BY COALESCE(session_date, date_added) DESC
                    LIMIT ?
                )
            ''', (club, window * 20))  # ~20 shots per session
        else:
            cursor.execute('''
                SELECT
                    AVG(avg_carry) as avg_carry,
                    AVG(avg_ball_speed) as avg_ball_speed,
                    AVG(avg_smash) as avg_smash,
                    AVG(avg_face_angle) as avg_face,
                    AVG(avg_club_path) as avg_path,
                    AVG(avg_strike_distance) as avg_strike
                FROM (
                    SELECT *
                    FROM session_stats
                    ORDER BY COALESCE(session_date, '9999-99-99') DESC
                    LIMIT ?
                )
            ''', (window,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'avg_carry': row[0],
                'avg_ball_speed': row[1],
                'avg_smash': row[2],
                'avg_face_angle': row[3],
                'avg_club_path': row[4],
                'avg_strike_distance': row[5],
            }
    except Exception as e:
        print(f"Get Rolling Averages Error: {e}")

    return {}


def batch_update_session_names():
    """
    Update session names for all imported sessions based on their shot data.

    Uses SessionNamer.generate_display_name() to create names in the format:
        "{YYYY-MM-DD} {SessionType} ({shot_count} shots)"

    Reads club data from the shots table and dates from sessions_discovered.

    Returns:
        Number of sessions updated.
    """
    from automation.naming_conventions import get_session_namer

    namer = get_session_namer()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Get all imported sessions with their dates
    cursor.execute('''
        SELECT sd.report_id, sd.session_date
        FROM sessions_discovered sd
        WHERE sd.import_status = 'imported'
    ''')
    sessions = cursor.fetchall()

    updated = 0
    for report_id, session_date in sessions:
        # Get clubs for this session from shots table
        cursor.execute('''
            SELECT club FROM shots
            WHERE session_id = ? AND club IS NOT NULL
        ''', (report_id,))
        clubs = [row[0] for row in cursor.fetchall()]

        if not clubs:
            continue

        new_name = namer.generate_display_name(session_date, clubs)

        cursor.execute('''
            UPDATE sessions_discovered
            SET session_name = ?
            WHERE report_id = ?
        ''', (new_name, report_id))

        if cursor.rowcount > 0:
            updated += 1

    conn.commit()

    # Log the batch update
    cursor.execute(
        "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
        ("BATCH_RENAME", "sessions_discovered", "multiple",
         f"Renamed {updated} sessions with display names")
    )
    conn.commit()
    conn.close()

    return updated


def get_sessions_missing_dates(limit: int = 100):
    """
    Get sessions that are missing session_date values.

    Args:
        limit: Maximum number of sessions to return

    Returns:
        List of dicts with session_id and shot_count
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                session_id,
                COUNT(*) as shot_count,
                MIN(date_added) as first_import
            FROM shots
            WHERE session_date IS NULL
            GROUP BY session_id
            ORDER BY first_import DESC
            LIMIT ?
        ''', (limit,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'session_id': row[0],
                'shot_count': row[1],
                'first_import': row[2]
            })

        conn.close()
        return results

    except Exception as e:
        print(f"Get Sessions Missing Dates Error: {e}")
        return []


def update_session_date_for_shots(session_id: str, session_date: str):
    """
    Update session_date for all shots in a session.

    Args:
        session_id: The session ID (report_id)
        session_date: ISO format date string (YYYY-MM-DD)

    Returns:
        Number of shots updated
    """
    parsed_date = datetime.strptime(session_date, "%Y-%m-%d")
    if parsed_date > datetime.now():
        raise ValueError("Session date cannot be in the future.")
    if parsed_date.year < 2020:
        raise ValueError("Session date cannot be before 2020.")

    updated = 0
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE shots SET session_date = ? WHERE session_id = ?",
            (session_date, session_id)
        )
        updated = cursor.rowcount
        conn.commit()

        # Log the update
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ("SET_SESSION_DATE", "session", session_id,
             f"Set session_date to {session_date} for {updated} shots")
        )
        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Update Session Date Error: {e}")

    # Also update in Supabase if available
    if supabase:
        try:
            supabase.table('shots').update(
                {'session_date': session_date}
            ).eq('session_id', session_id).execute()
        except Exception as e:
            print(f"Supabase Update Session Date Error: {e}")

    return updated


# ============================================================================
# SUPABASE SYNC FUNCTIONS
# ============================================================================

def get_detailed_sync_status() -> dict:
    """
    Get comprehensive sync status including drift detection.

    Returns:
        Dict with counts, drift detection, and last sync metadata.
    """
    status = {
        'local_count': 0,
        'supabase_count': 0,
        'local_only_count': 0,
        'last_sync': None,
        'drift_detected': False,
        'shots': {
            'sqlite': 0,
            'supabase': 0,
            'missing_in_supabase': [],
            'missing_in_sqlite': [],
        },
        'connected': supabase is not None,
        'error': None,
    }

    local_ids = set()
    conn = None
    try:
        # Get local shot IDs and count
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT shot_id FROM shots")
        local_ids = {row[0] for row in cursor.fetchall()}
        status['local_count'] = len(local_ids)
        status['shots']['sqlite'] = status['local_count']

        # Get last successful sync metadata
        cursor.execute("""
            SELECT completed_at, records_synced, records_failed
            FROM sync_audit
            WHERE sync_type = 'to_supabase' AND completed_at IS NOT NULL
            ORDER BY completed_at DESC
            LIMIT 1
        """)
        last_sync_row = cursor.fetchone()
        if last_sync_row:
            status['last_sync'] = {
                'timestamp': last_sync_row[0],
                'records_synced': last_sync_row[1],
                'records_failed': last_sync_row[2],
            }
    except Exception as e:
        status['error'] = str(e)
    finally:
        if conn is not None:
            conn.close()

    if not supabase:
        status['error'] = status['error'] or "Supabase not configured"
        status['local_only_count'] = max(0, status['local_count'] - status['supabase_count'])
        status['drift_detected'] = status['local_count'] != status['supabase_count']
        return status

    try:
        # Get remote shot IDs (paginated)
        remote_ids = set()
        offset = 0
        page_size = 1000
        while True:
            response = supabase.table('shots').select('shot_id').range(
                offset, offset + page_size - 1
            ).execute()
            data = response.data or []
            if not data:
                break
            remote_ids.update(row['shot_id'] for row in data)
            if len(data) < page_size:
                break
            offset += page_size

        status['supabase_count'] = len(remote_ids)
        status['shots']['supabase'] = status['supabase_count']

        # Find differences
        status['shots']['missing_in_supabase'] = list(local_ids - remote_ids)[:100]  # Cap at 100
        status['shots']['missing_in_sqlite'] = list(remote_ids - local_ids)[:100]
    except Exception as e:
        status['error'] = status['error'] or str(e)

    status['local_only_count'] = max(0, status['local_count'] - status['supabase_count'])
    status['drift_detected'] = status['local_count'] != status['supabase_count']

    return status


def sync_to_supabase(dry_run: bool = False, batch_size: int = 100) -> dict:
    """
    Push all local SQLite data to Supabase (local is source of truth).

    Args:
        dry_run: If True, report what would be synced without making changes
        batch_size: Number of records per batch upsert

    Returns:
        Dict with sync results: {'shots_synced': int, 'errors': list}
    """
    import json

    started_at = datetime.now().isoformat()
    records_synced = 0
    records_failed = 0
    errors = []
    results = {
        'shots_synced': 0,
        'shots_total': 0,
        'batches': 0,
        'errors': errors,
        'dry_run': dry_run,
    }

    conn = None

    try:
        if not supabase:
            error_msg = "Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY."
            errors.append(error_msg)
            records_failed += 1
            return results

        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all local shots
        cursor.execute("SELECT * FROM shots")
        rows = cursor.fetchall()
        results['shots_total'] = len(rows)

        if dry_run:
            results['message'] = f"Would sync {len(rows)} shots to Supabase"
            return results

        # Convert rows to dicts and batch upsert
        shots = [dict(row) for row in rows]

        for i in range(0, len(shots), batch_size):
            batch = shots[i:i + batch_size]
            try:
                # Clean datetime fields for JSON serialization
                for shot in batch:
                    for key, value in shot.items():
                        if hasattr(value, 'isoformat'):
                            shot[key] = value.isoformat()

                supabase.table('shots').upsert(batch).execute()
                results['shots_synced'] += len(batch)
                records_synced += len(batch)
                results['batches'] += 1
            except Exception as e:
                error_msg = f"Batch {results['batches'] + 1} error: {str(e)[:100]}"
                errors.append(error_msg)
                records_failed += len(batch)

    except Exception as e:
        error_msg = f"Sync error: {str(e)}"
        errors.append(error_msg)
        unsynced = results['shots_total'] - results['shots_synced']
        records_failed += unsynced if unsynced > 0 else 1

    finally:
        if conn is not None:
            conn.close()
        try:
            audit_conn = sqlite3.connect(SQLITE_DB_PATH)
            audit_cursor = audit_conn.cursor()
            audit_cursor.execute('''
                INSERT INTO sync_audit
                (sync_type, started_at, completed_at, records_synced, records_failed, error_message, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                'to_supabase',
                started_at,
                datetime.now().isoformat(),
                records_synced,
                records_failed,
                "; ".join(errors[:5]) if errors else None,
                json.dumps({
                    'dry_run': dry_run,
                    'shots_total': results['shots_total'],
                    'batches': results['batches'],
                    'errors': errors,
                })
            ))
            audit_conn.commit()
            audit_conn.close()
        except Exception as audit_error:
            errors.append(f"Audit log error: {str(audit_error)[:100]}")

    return results


def sync_from_supabase(dry_run: bool = False) -> dict:
    """
    Pull missing records from Supabase to local SQLite.

    Only syncs records that exist in Supabase but not locally.
    Does NOT overwrite existing local records.

    Args:
        dry_run: If True, report what would be synced without making changes

    Returns:
        Dict with sync results
    """
    results = {
        'shots_synced': 0,
        'errors': [],
        'dry_run': dry_run,
    }

    if not supabase:
        results['errors'].append("Supabase not configured")
        return results

    try:
        # Get local shot IDs
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT shot_id FROM shots")
        local_ids = {row[0] for row in cursor.fetchall()}

        # Fetch from Supabase in batches
        offset = 0
        page_size = 1000
        new_shots = []

        while True:
            response = supabase.table('shots').select('*').range(offset, offset + page_size - 1).execute()
            data = response.data or []
            if not data:
                break

            for shot in data:
                if shot['shot_id'] not in local_ids:
                    new_shots.append(shot)

            if len(data) < page_size:
                break
            offset += page_size

        if dry_run:
            results['message'] = f"Would sync {len(new_shots)} shots from Supabase"
            results['shots_to_sync'] = len(new_shots)
            conn.close()
            return results

        # Insert new shots
        for shot in new_shots:
            try:
                columns = ', '.join(shot.keys())
                placeholders = ', '.join(['?'] * len(shot))
                cursor.execute(
                    f"INSERT OR IGNORE INTO shots ({columns}) VALUES ({placeholders})",
                    list(shot.values())
                )
                results['shots_synced'] += 1
            except Exception as e:
                results['errors'].append(f"Insert error: {str(e)[:50]}")

        conn.commit()
        conn.close()

    except Exception as e:
        results['errors'].append(f"Sync error: {str(e)}")

    return results
