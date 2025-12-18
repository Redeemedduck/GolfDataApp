#!/usr/bin/env python3
"""
Automated sync and analysis script for golf data pipeline

This script:
1. Syncs new data from Supabase to BigQuery
2. Optionally runs AI analysis on recent sessions
3. Logs all operations for tracking
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import bigquery

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "golf_data")
BQ_TABLE_ID = os.getenv("BQ_TABLE_ID", "shots")
LOG_FILE = "logs/sync.log"

def log_message(message):
    """Write message to both console and log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)

    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    with open(LOG_FILE, "a") as f:
        f.write(log_entry + "\n")

def check_for_new_shots():
    """Check if there are new shots in Supabase since last BigQuery sync"""
    try:
        # Get latest timestamp from BigQuery
        bq_client = bigquery.Client(project=GCP_PROJECT_ID)
        table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

        query = f"SELECT MAX(date_added) as latest_date FROM `{table_id}`"
        result = bq_client.query(query).result()
        row = next(result)
        latest_bq_date = row.latest_date

        # Get count of shots in Supabase newer than BigQuery
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        if latest_bq_date:
            response = supabase.table("shots").select("shot_id", count="exact").gt("date_added", latest_bq_date.isoformat()).execute()
            new_shot_count = response.count
        else:
            response = supabase.table("shots").select("shot_id", count="exact").execute()
            new_shot_count = response.count

        return new_shot_count, latest_bq_date

    except Exception as e:
        log_message(f"Error checking for new shots: {e}")
        return None, None

def run_incremental_sync():
    """Run incremental sync from Supabase to BigQuery"""
    try:
        log_message("Starting incremental sync...")

        # Import the sync function
        from supabase_to_bigquery import sync_incremental

        sync_incremental()
        log_message("Incremental sync completed successfully")
        return True

    except Exception as e:
        log_message(f"Error during sync: {e}")
        return False

def get_recent_clubs(days=1):
    """Get list of clubs used in recent sessions"""
    try:
        bq_client = bigquery.Client(project=GCP_PROJECT_ID)
        table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

        query = f"""
        SELECT DISTINCT club, COUNT(*) as shot_count
        FROM `{table_id}`
        WHERE date_added >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY club
        ORDER BY shot_count DESC
        """

        df = bq_client.query(query).to_dataframe()
        return df

    except Exception as e:
        log_message(f"Error getting recent clubs: {e}")
        return None

def run_analysis(club=None):
    """Run AI analysis for specified club or all recent clubs"""
    try:
        log_message(f"Running AI analysis for {club if club else 'all clubs'}...")

        from gemini_analysis import create_analysis_prompt, analyze_with_gemini

        prompt = create_analysis_prompt(club=club)
        result = analyze_with_gemini(prompt)

        if result:
            log_message(f"AI analysis completed for {club if club else 'all clubs'}")
            return True
        else:
            log_message("AI analysis failed")
            return False

    except Exception as e:
        log_message(f"Error during analysis: {e}")
        return False

def main():
    """Main automation routine"""
    log_message("="*70)
    log_message("GOLF DATA PIPELINE - AUTO SYNC")
    log_message("="*70)

    # Check for new shots
    log_message("Checking for new shots...")
    new_shots, latest_date = check_for_new_shots()

    if new_shots is None:
        log_message("Failed to check for new shots. Exiting.")
        return 1

    if new_shots == 0:
        log_message(f"No new shots since {latest_date}. Nothing to sync.")
        return 0

    log_message(f"Found {new_shots} new shots to sync")

    # Run sync
    sync_success = run_incremental_sync()

    if not sync_success:
        log_message("Sync failed. Skipping analysis.")
        return 1

    # Check if we should run analysis
    if len(sys.argv) > 1 and sys.argv[1] == "--analyze":
        log_message("Analysis flag detected. Running AI analysis...")

        # Get recent clubs
        recent_clubs = get_recent_clubs(days=1)

        if recent_clubs is not None and not recent_clubs.empty:
            log_message(f"Recent clubs: {', '.join(recent_clubs['club'].tolist())}")

            # Analyze each recent club
            for club in recent_clubs['club'].tolist():
                log_message(f"\n{'='*70}")
                run_analysis(club=club)
        else:
            log_message("No recent sessions found to analyze")

    log_message("="*70)
    log_message("AUTO SYNC COMPLETE")
    log_message("="*70)

    return 0

if __name__ == "__main__":
    sys.exit(main())
