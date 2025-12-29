import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "golf_stats.db")

# Detect environment
IS_CLOUD_RUN = os.getenv('K_SERVICE') is not None

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

    conn.commit()
    conn.close()

# --- Hybrid Save (Local + Cloud) ---
def save_shot(data):
    """Save shot data to local SQLite and Supabase (hybrid)."""
    
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
        # New advanced metrics
        'optix_x': clean_value(data.get('optix_x')),
        'optix_y': clean_value(data.get('optix_y')),
        'club_lie': clean_value(data.get('club_lie')),
        'lie_angle': data.get('lie_angle') if data.get('lie_angle') else None
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
    """Get session data from local SQLite database, with fallback to Supabase."""
    df = pd.DataFrame()
    
    # 1. Try Local SQLite
    try:
        if os.path.exists(SQLITE_DB_PATH):
            conn = sqlite3.connect(SQLITE_DB_PATH)
            query = "SELECT * FROM shots"
            if session_id:
                query += " WHERE session_id = ?"
                df = pd.read_sql_query(query, conn, params=[session_id])
            else:
                df = pd.read_sql_query(query, conn)
            conn.close()
    except Exception as e:
        print(f"SQLite Read Error: {e}")

    # 2. Hybrid Fallback: If SQLite is empty (e.g. fresh container) or in Cloud Run, check Supabase
    if df.empty and supabase:
        try:
            # Note: pagination might be needed for very large datasets (>1000 shots)
            query = supabase.table('shots').select('*')
            if session_id:
                query = query.eq('session_id', session_id)
            
            response = query.execute()
            if response.data:
                df = pd.DataFrame(response.data)
                # Cleanup date format if needed
                if 'date_added' in df.columns:
                    df['date_added'] = pd.to_datetime(df['date_added'])
        except Exception as e:
            print(f"Supabase Read Error: {e}")
            
    return df

def get_unique_sessions():
    """Get unique sessions from local SQLite, fallback to Supabase."""
    sessions = []
    
    # 1. Try Local SQLite
    try:
        if os.path.exists(SQLITE_DB_PATH):
            conn = sqlite3.connect(SQLITE_DB_PATH)
            query = "SELECT DISTINCT session_id, MAX(date_added) as date_added FROM shots GROUP BY session_id ORDER BY date_added DESC"
            df = pd.read_sql_query(query, conn)
            conn.close()
            if not df.empty:
                sessions = df.to_dict('records')
    except Exception as e:
        print(f"SQLite Session Error: {e}")

    # 2. Hybrid Fallback: Use Supabase
    if not sessions and supabase:
        try:
            # Fetch all shot headers to determine unique sessions
            response = supabase.table('shots').select('session_id, date_added').execute()
            if response.data:
                df = pd.DataFrame(response.data)
                if not df.empty:
                    df['date_added'] = pd.to_datetime(df['date_added'])
                    # Group by session_id and get latest date_added
                    sessions_df = df.groupby('session_id')['date_added'].max().reset_index()
                    sessions_df = sessions_df.sort_values('date_added', ascending=False)
                    sessions = sessions_df.to_dict('records')
        except Exception as e:
            print(f"Supabase Session Error: {e}")
            
    return sessions

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
# BULK EDITING FUNCTIONS (Phase 2)
# ============================================================================

def update_shot_metadata(shot_ids, field, value):
    """
    Bulk update a specific field for multiple shots.

    Args:
        shot_ids: List of shot IDs to update
        field: Column name to update
        value: New value for the field

    Returns:
        Number of shots updated
    """
    # Local
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        placeholders = ','.join(['?'] * len(shot_ids))
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
    shots_updated = 0

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        for _, shot in df.iterrows():
            # Recalculate smash factor
            club_speed = shot.get('club_speed', 0)
            ball_speed = shot.get('ball_speed', 0)
            new_smash = round(ball_speed / club_speed, 2) if club_speed > 0 else 0.0

            # Clean invalid values (99999 → 0)
            updates = {}
            for col in df.columns:
                if col not in ['shot_id', 'session_id', 'date_added', 'club', 'shot_type', 'impact_img', 'swing_img', 'lie_angle']:
                    val = shot[col]
                    if val == 99999 or (pd.isna(val) and col != 'smash'):
                        updates[col] = 0

            updates['smash'] = new_smash

            # Build update query
            if updates:
                set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
                values = list(updates.values()) + [shot['shot_id']]
                cursor.execute(f"UPDATE shots SET {set_clause} WHERE shot_id = ?", values)
                shots_updated += cursor.rowcount

        conn.commit()

        # Log the recalculation
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

    outliers = []

    for _, shot in df.iterrows():
        reasons = []

        # Check carry distance
        if shot.get('carry', 0) > 400:
            reasons.append(f"Carry too high: {shot['carry']:.0f} yds")

        # Check smash factor
        if shot.get('smash', 0) > 1.6:
            reasons.append(f"Smash too high: {shot['smash']:.2f}")
        elif shot.get('smash', 0) > 0 and shot.get('smash', 0) < 0.8:
            reasons.append(f"Smash too low: {shot['smash']:.2f}")

        # Check ball speed
        if shot.get('ball_speed', 0) > 200:
            reasons.append(f"Ball speed too high: {shot['ball_speed']:.0f} mph")

        # Check spin rates
        if shot.get('back_spin', 0) > 10000:
            reasons.append(f"Back spin too high: {shot['back_spin']:.0f} rpm")
        if abs(shot.get('side_spin', 0)) > 5000:
            reasons.append(f"Side spin excessive: {shot['side_spin']:.0f} rpm")

        if reasons:
            outliers.append({
                'shot_id': shot['shot_id'],
                'session_id': shot['session_id'],
                'club': shot['club'],
                'carry': shot.get('carry', 0),
                'smash': shot.get('smash', 0),
                'ball_speed': shot.get('ball_speed', 0),
                'reasons': '; '.join(reasons)
            })

    return pd.DataFrame(outliers)


def validate_shot_data():
    """
    Find shots missing critical fields.

    Returns:
        DataFrame of invalid shots with missing fields
    """
    df = get_session_data()

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

def restore_deleted_shots(shot_ids):
    """
    Restore previously deleted shots from archive.

    Args:
        shot_ids: List of shot IDs to restore

    Returns:
        Number of shots restored
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

                # Restore to shots table
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