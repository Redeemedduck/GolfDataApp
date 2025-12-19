#!/usr/bin/env python3
"""
Post-session analysis script

Run this after each practice session to:
1. Sync new data to BigQuery
2. Show session summary
3. Get AI insights on your performance
"""
import os
import sys
from dotenv import load_dotenv
from google.cloud import bigquery
from supabase_to_bigquery import sync_incremental
from gemini_analysis import create_analysis_prompt, analyze_with_gemini, get_club_summary

# Load environment variables
load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "golf_data")
BQ_TABLE_ID = os.getenv("BQ_TABLE_ID", "shots")

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(text.center(70))
    print("="*70 + "\n")

def get_todays_sessions():
    """Get all shots from today's sessions"""
    bq_client = bigquery.Client(project=GCP_PROJECT_ID)
    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

    query = f"""
    SELECT
        club,
        COUNT(*) as shots,
        ROUND(AVG(carry), 1) as avg_carry,
        ROUND(AVG(total), 1) as avg_total,
        ROUND(AVG(smash), 2) as avg_smash,
        ROUND(AVG(ball_speed), 1) as avg_ball_speed,
        ROUND(AVG(club_speed), 1) as avg_club_speed,
        MIN(date_added) as session_start
    FROM `{table_id}`
    WHERE DATE(date_added) = CURRENT_DATE()
    GROUP BY club
    ORDER BY session_start DESC
    """

    df = bq_client.query(query).to_dataframe()
    return df

def main():
    print_header("POST-SESSION ANALYSIS")

    # Step 1: Sync new data
    print("📊 Step 1: Syncing new data from Supabase to BigQuery...")
    try:
        sync_incremental()
        print("✅ Sync complete!\n")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return 1

    # Step 2: Show today's summary
    print_header("TODAY'S SESSION SUMMARY")

    try:
        todays_data = get_todays_sessions()

        if todays_data.empty:
            print("No shots recorded today. Make sure your Supabase data is up to date.")
            return 0

        print(todays_data.to_string(index=False))
        print(f"\n📈 Total shots today: {todays_data['shots'].sum()}")
        print(f"🏌️  Clubs practiced: {', '.join(todays_data['club'].tolist())}")

    except Exception as e:
        print(f"❌ Error getting session summary: {e}")
        return 1

    # Step 3: Ask if user wants AI analysis
    print("\n" + "-"*70)
    response = input("\n🤖 Would you like AI analysis of today's session? (y/n): ").strip().lower()

    if response == 'y' or response == 'yes':
        print("\n" + "="*70)
        print("Generating AI insights...")
        print("="*70 + "\n")

        # Analyze each club from today
        for club in todays_data['club'].tolist():
            print(f"\n{'='*70}")
            print(f"Analyzing {club}...".center(70))
            print('='*70 + "\n")

            try:
                prompt = create_analysis_prompt(club=club)
                # Filter prompt to only include today's data
                # (The query already filtered by date, so this will work)
                analyze_with_gemini(prompt)

            except Exception as e:
                print(f"❌ Error analyzing {club}: {e}")

    # Step 4: Overall summary
    print_header("OVERALL STATS (ALL TIME)")

    try:
        all_time_summary = get_club_summary()
        print(all_time_summary.to_string(index=False))

    except Exception as e:
        print(f"❌ Error getting overall summary: {e}")

    print_header("SESSION ANALYSIS COMPLETE")
    print("\n💡 Tips:")
    print("  • Run 'python post_session.py' after each practice session")
    print("  • Check logs/sync.log for automation history")
    print("  • Use 'python gemini_analysis.py analyze <club>' for detailed club analysis")
    print("\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
