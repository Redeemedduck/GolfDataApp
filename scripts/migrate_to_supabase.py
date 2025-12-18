#!/usr/bin/env python3
"""
Migration script to transfer golf shot data from SQLite to Supabase
"""
import sqlite3
import os
from supabase import create_client, Client
from datetime import datetime

# Configuration - Set these as environment variables or update directly
SUPABASE_URL = os.getenv("SUPABASE_URL", "")  # e.g., https://xxxxx.supabase.co
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # Your anon/service_role key
SQLITE_DB_PATH = "golf_stats.db"

def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "Please set SUPABASE_URL and SUPABASE_KEY environment variables\n"
            "Example:\n"
            "export SUPABASE_URL='https://xxxxx.supabase.co'\n"
            "export SUPABASE_KEY='your-anon-or-service-key'"
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_sqlite_data():
    """Fetch all shots from SQLite database"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM shots ORDER BY date_added")
    rows = cursor.fetchall()

    # Convert rows to dictionaries
    shots = []
    for row in rows:
        shot = dict(row)
        shots.append(shot)

    conn.close()
    return shots

def migrate_to_supabase(batch_size=50):
    """Migrate all shots from SQLite to Supabase"""
    print("Starting migration from SQLite to Supabase...")

    # Get Supabase client
    supabase = get_supabase_client()
    print(f"Connected to Supabase at {SUPABASE_URL}")

    # Get SQLite data
    shots = get_sqlite_data()
    print(f"Found {len(shots)} shots in SQLite database")

    if len(shots) == 0:
        print("No shots to migrate!")
        return

    # Migrate in batches
    total_migrated = 0
    failed = []

    for i in range(0, len(shots), batch_size):
        batch = shots[i:i + batch_size]

        try:
            # Use upsert to handle duplicates gracefully
            response = supabase.table("shots").upsert(batch).execute()
            total_migrated += len(batch)
            print(f"Migrated batch {i//batch_size + 1}: {len(batch)} shots (Total: {total_migrated}/{len(shots)})")
        except Exception as e:
            print(f"Error migrating batch {i//batch_size + 1}: {e}")
            failed.extend([shot['shot_id'] for shot in batch])

    # Summary
    print("\n" + "="*50)
    print("MIGRATION SUMMARY")
    print("="*50)
    print(f"Total shots in SQLite: {len(shots)}")
    print(f"Successfully migrated: {total_migrated}")
    print(f"Failed: {len(failed)}")

    if failed:
        print(f"\nFailed shot IDs:")
        for shot_id in failed:
            print(f"  - {shot_id}")
    else:
        print("\nAll shots migrated successfully!")

    # Verify migration
    try:
        result = supabase.table("shots").select("shot_id", count="exact").execute()
        print(f"\nVerification: Supabase now contains {result.count} shots")
    except Exception as e:
        print(f"Could not verify migration: {e}")

def verify_migration():
    """Verify that SQLite and Supabase have the same data"""
    print("\nVerifying migration...")

    # Get counts from SQLite
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM shots")
    sqlite_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT session_id) FROM shots")
    sqlite_sessions = cursor.fetchone()[0]
    conn.close()

    # Get counts from Supabase
    supabase = get_supabase_client()
    shots_result = supabase.table("shots").select("shot_id", count="exact").execute()
    sessions_result = supabase.table("shots").select("session_id").execute()
    supabase_sessions = len(set([s['session_id'] for s in sessions_result.data]))

    print(f"\nSQLite: {sqlite_count} shots, {sqlite_sessions} sessions")
    print(f"Supabase: {shots_result.count} shots, {supabase_sessions} sessions")

    if sqlite_count == shots_result.count and sqlite_sessions == supabase_sessions:
        print("\n✅ Migration verified successfully!")
        return True
    else:
        print("\n⚠️  Warning: Counts don't match!")
        return False

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_migration()
    else:
        migrate_to_supabase()
        verify_migration()
