"""
Sync Quality Flags to Supabase.

This script pushes the shot_quality_flags data and is_warmup column values
from the local SQLite database to Supabase. Run this AFTER the Supabase
migration SQL (supabase_quality_migration.sql) has been applied.

Usage:
    python sync_quality_flags.py              # Full sync (flags + warmup)
    python sync_quality_flags.py --dry-run    # Preview what would be synced
    python sync_quality_flags.py --flags-only # Only sync quality flags
    python sync_quality_flags.py --warmup-only # Only sync is_warmup column

Prerequisites:
    1. Run supabase_quality_migration.sql in Supabase SQL Editor first
    2. .env file must have SUPABASE_URL and SUPABASE_KEY set
    3. pip install supabase (already installed if you've used the app)
"""

import sqlite3
import os
import sys
import argparse


def load_env():
    """
    Load environment variables from the .env file.
    Returns a dict of {key: value} for all SUPABASE-related vars.

    We manually parse .env instead of using dotenv because the
    dotenv library can have issues in certain execution contexts.
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    env_vars = {}

    if not os.path.exists(env_path):
        print(f"ERROR: .env file not found at {env_path}")
        print("Create a .env file with SUPABASE_URL and SUPABASE_KEY")
        sys.exit(1)

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")

    return env_vars


def get_supabase_client(env_vars):
    """
    Create and return a Supabase client using credentials from env_vars.
    Exits with an error message if credentials are missing or connection fails.
    """
    url = env_vars.get('SUPABASE_URL', '')
    key = env_vars.get('SUPABASE_KEY', '')

    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    try:
        from supabase import create_client
        return create_client(url, key)
    except ImportError:
        print("ERROR: supabase package not installed.")
        print("Run: pip install supabase")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to connect to Supabase: {e}")
        sys.exit(1)


def get_sqlite_connection():
    """
    Connect to the local SQLite database.
    The database is expected to be in the same directory as this script.
    """
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'golf_stats.db')

    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    return sqlite3.connect(db_path)


def sync_quality_flags(sb, conn, dry_run=False):
    """
    Sync shot_quality_flags from SQLite to Supabase.

    Strategy:
    1. Clear all existing flags in Supabase (full replace, not incremental)
    2. Read all flags from SQLite
    3. Insert in batches of 500 (Supabase has row limits per request)

    Args:
        sb: Supabase client
        conn: SQLite connection
        dry_run: If True, only preview what would be synced
    """
    cursor = conn.cursor()

    # Read all flags from SQLite
    cursor.execute('''
        SELECT shot_id, category, severity, reason, session_id, club
        FROM shot_quality_flags
        ORDER BY flag_id
    ''')
    flags = cursor.fetchall()

    print(f"\nQuality Flags: {len(flags)} flags to sync")

    # Show breakdown by severity
    cursor.execute('''
        SELECT severity, COUNT(*)
        FROM shot_quality_flags
        GROUP BY severity
        ORDER BY severity
    ''')
    for sev, cnt in cursor.fetchall():
        print(f"  {sev}: {cnt}")

    if dry_run:
        print("  [DRY RUN] Would delete all existing flags and insert fresh")
        return

    # Step 1: Clear existing flags in Supabase
    try:
        # Delete all rows (Supabase requires a filter, so we use a condition
        # that matches everything: flag_id > 0)
        sb.table('shot_quality_flags').delete().gt('flag_id', 0).execute()
        print("  Cleared existing Supabase flags.")
    except Exception as e:
        print(f"  WARNING: Could not clear existing flags: {e}")
        print("  This is OK if the table is empty or was just created.")

    # Step 2: Insert in batches
    # Each flag is a dict matching the Supabase table columns.
    # We skip flag_id (auto-generated) and flagged_at (defaults to NOW()).
    batch_size = 500
    total_inserted = 0

    for i in range(0, len(flags), batch_size):
        batch = flags[i:i + batch_size]
        rows = [
            {
                'shot_id': shot_id,
                'category': category,
                'severity': severity,
                'reason': reason,
                'session_id': session_id or '',
                'club': club or '',
            }
            for shot_id, category, severity, reason, session_id, club in batch
        ]

        try:
            sb.table('shot_quality_flags').insert(rows).execute()
            total_inserted += len(rows)
            print(f"  Inserted batch {i // batch_size + 1}: {len(rows)} flags (total: {total_inserted})")
        except Exception as e:
            print(f"  ERROR inserting batch {i // batch_size + 1}: {e}")
            print(f"  First row in failed batch: {rows[0]}")
            break

    print(f"  Done: {total_inserted}/{len(flags)} flags synced to Supabase.")


def sync_warmup_tags(sb, conn, dry_run=False):
    """
    Sync is_warmup values from SQLite to Supabase.

    Strategy:
    1. Get all shot_ids where is_warmup = 1
    2. Update those shots in Supabase in batches
    3. Also set is_warmup = 0 for all other shots (to ensure consistency)

    Args:
        sb: Supabase client
        conn: SQLite connection
        dry_run: If True, only preview what would be synced
    """
    cursor = conn.cursor()

    # Get warmup shot IDs
    cursor.execute("SELECT shot_id FROM shots WHERE is_warmup = 1")
    warmup_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) FROM shots WHERE is_warmup = 0")
    non_warmup_count = cursor.fetchone()[0]

    print(f"\nWarmup Tags: {len(warmup_ids)} warmup shots, {non_warmup_count} non-warmup")

    if dry_run:
        print("  [DRY RUN] Would update is_warmup column for all shots")
        return

    # Step 1: Set all shots to is_warmup = 0 first (clean slate)
    try:
        sb.table('shots').update({'is_warmup': 0}).neq('shot_id', '').execute()
        print("  Reset all shots to is_warmup = 0")
    except Exception as e:
        print(f"  ERROR resetting warmup flags: {e}")
        print("  Make sure the is_warmup column exists (run the migration SQL first)")
        return

    # Step 2: Set is_warmup = 1 for warmup shots in batches
    batch_size = 100
    total_updated = 0

    for i in range(0, len(warmup_ids), batch_size):
        batch = warmup_ids[i:i + batch_size]
        try:
            # Update each shot in the batch individually
            # (Supabase .in_() filter works for select but update needs
            # individual calls or a workaround)
            for shot_id in batch:
                sb.table('shots').update({'is_warmup': 1}).eq('shot_id', shot_id).execute()
                total_updated += 1

            print(f"  Updated batch {i // batch_size + 1}: {len(batch)} shots (total: {total_updated})")
        except Exception as e:
            print(f"  ERROR updating batch {i // batch_size + 1}: {e}")
            break

    print(f"  Done: {total_updated}/{len(warmup_ids)} warmup tags synced to Supabase.")


def main():
    """
    Main entry point. Parses arguments and runs the appropriate sync.
    """
    parser = argparse.ArgumentParser(
        description='Sync golf data quality flags and warmup tags to Supabase'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview what would be synced without making changes'
    )
    parser.add_argument(
        '--flags-only', action='store_true',
        help='Only sync quality flags (not warmup tags)'
    )
    parser.add_argument(
        '--warmup-only', action='store_true',
        help='Only sync warmup tags (not quality flags)'
    )

    args = parser.parse_args()

    # Load environment and create clients
    env_vars = load_env()
    sb = get_supabase_client(env_vars)
    conn = get_sqlite_connection()

    print("=" * 60)
    print("Golf Data Quality: Supabase Sync")
    print("=" * 60)

    if args.dry_run:
        print("[DRY RUN MODE — no changes will be made]")

    # Verify Supabase connection
    try:
        result = sb.table('shots').select('shot_id', count='exact').limit(1).execute()
        print(f"Supabase connected: {result.count} shots in cloud database")
    except Exception as e:
        print(f"ERROR: Could not connect to Supabase: {e}")
        sys.exit(1)

    # Run syncs based on flags
    if not args.warmup_only:
        sync_quality_flags(sb, conn, dry_run=args.dry_run)

    if not args.flags_only:
        sync_warmup_tags(sb, conn, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("Sync complete!")
    print("=" * 60)

    conn.close()


if __name__ == '__main__':
    main()
