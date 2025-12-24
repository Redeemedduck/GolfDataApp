#!/usr/bin/env python3
"""
Sync golf shot data from SQLite directly to BigQuery
Eliminates Supabase middleman for simplified architecture
"""
import os
import sys
from google.cloud import bigquery
from dotenv import load_dotenv

# Add parent directory to path to import golf_db
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import golf_db

# Load environment variables
load_dotenv()

# Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "valued-odyssey-474423-g1")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "golf_data")
BQ_TABLE_ID = os.getenv("BQ_TABLE_ID", "shots")

def get_bigquery_client():
    """Initialize BigQuery client"""
    try:
        return bigquery.Client(project=GCP_PROJECT_ID)
    except Exception as e:
        print(f"Error initializing BigQuery client: {e}")
        print("Make sure you're authenticated with: gcloud auth application-default login")
        sys.exit(1)

def sync_to_bigquery(mode='full'):
    """
    Sync data from SQLite to BigQuery

    Args:
        mode: 'full' (WRITE_TRUNCATE) or 'incremental' (WRITE_APPEND)
    """
    print(f"🔄 Starting {mode} sync: SQLite → BigQuery")

    # Get BigQuery client
    bq_client = get_bigquery_client()
    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

    # Fetch all shots from SQLite
    print("📊 Fetching data from SQLite...")
    df = golf_db.get_all_shots_for_sync()

    if df.empty:
        print("❌ No data found in SQLite database")
        return

    print(f"✅ Found {len(df)} shots in SQLite")

    # Convert timestamp to datetime for BigQuery compatibility
    if 'date_added' in df.columns:
        df['date_added'] = pd.to_datetime(df['date_added'])

    # Configure load job
    job_config = bigquery.LoadJobConfig(
        write_disposition=(
            bigquery.WriteDisposition.WRITE_TRUNCATE if mode == 'full'
            else bigquery.WriteDisposition.WRITE_APPEND
        ),
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
        autodetect=True
    )

    # Load data to BigQuery
    print(f"☁️  Uploading to BigQuery ({mode} mode)...")
    try:
        job = bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()  # Wait for completion

        # Verify
        table = bq_client.get_table(table_id)
        print(f"✅ Success! BigQuery table now has {table.num_rows:,} rows")

    except Exception as e:
        print(f"❌ Error uploading to BigQuery: {e}")
        sys.exit(1)

def verify_sync():
    """Verify data consistency between SQLite and BigQuery"""
    print("\n🔍 Verifying sync...")

    bq_client = get_bigquery_client()
    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

    # Get counts
    sqlite_df = golf_db.get_all_shots_for_sync()
    sqlite_count = len(sqlite_df)

    query = f"SELECT COUNT(*) as count FROM `{table_id}`"
    bq_count = bq_client.query(query).to_dataframe()['count'].iloc[0]

    print(f"  SQLite: {sqlite_count:,} shots")
    print(f"  BigQuery: {bq_count:,} shots")

    if sqlite_count == bq_count:
        print("✅ Counts match!")
    else:
        print("⚠️  Warning: Counts don't match. Consider running full sync.")

def show_stats():
    """Show summary statistics from both databases"""
    print("\n📊 Database Statistics\n")

    # SQLite stats
    sqlite_df = golf_db.get_all_shots_for_sync()
    print("SQLite Database:")
    print(f"  Total shots: {len(sqlite_df):,}")
    print(f"  Sessions: {sqlite_df['session_id'].nunique()}")
    print(f"  Clubs: {', '.join(sqlite_df['club'].unique())}")

    # BigQuery stats
    bq_client = get_bigquery_client()
    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

    query = f"""
    SELECT
        COUNT(*) as total_shots,
        COUNT(DISTINCT session_id) as sessions,
        COUNT(DISTINCT club) as clubs
    FROM `{table_id}`
    """
    bq_stats = bq_client.query(query).to_dataframe()

    print("\nBigQuery Database:")
    print(f"  Total shots: {bq_stats['total_shots'].iloc[0]:,}")
    print(f"  Sessions: {bq_stats['sessions'].iloc[0]}")
    print(f"  Clubs: {bq_stats['clubs'].iloc[0]}")

if __name__ == "__main__":
    import pandas as pd

    if len(sys.argv) < 2:
        print("""
Golf Data Sync: SQLite → BigQuery

Usage:
  python sqlite_to_bigquery.py full          # Full sync (replace all data)
  python sqlite_to_bigquery.py incremental   # Incremental sync (append new data)
  python sqlite_to_bigquery.py verify        # Verify data consistency
  python sqlite_to_bigquery.py stats         # Show database statistics

Notes:
  - Full sync: Replaces all BigQuery data with current SQLite data
  - Incremental: Appends SQLite data to BigQuery (may create duplicates)
  - Use 'full' sync for most reliable results
        """)
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == 'full':
        sync_to_bigquery(mode='full')
        verify_sync()
    elif command == 'incremental':
        sync_to_bigquery(mode='incremental')
        verify_sync()
    elif command == 'verify':
        verify_sync()
    elif command == 'stats':
        show_stats()
    else:
        print(f"Unknown command: {command}")
        print("Use: full, incremental, verify, or stats")
        sys.exit(1)
