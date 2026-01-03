#!/usr/bin/env python3
"""
Export data from Supabase to BigQuery for Vertex AI analysis
"""
import os
from supabase import create_client, Client
from google.cloud import bigquery
from google.oauth2 import service_account
import json
from datetime import datetime
import time
from dotenv import load_dotenv
import observability

# Load environment variables from .env file
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "golf_data")
BQ_TABLE_ID = os.getenv("BQ_TABLE_ID", "shots")
GCP_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Please set SUPABASE_URL and SUPABASE_KEY environment variables")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_bigquery_client():
    """Initialize BigQuery client"""
    if not GCP_PROJECT_ID:
        raise ValueError("Please set GCP_PROJECT_ID environment variable")

    if GCP_CREDENTIALS_PATH and os.path.exists(GCP_CREDENTIALS_PATH):
        credentials = service_account.Credentials.from_service_account_file(GCP_CREDENTIALS_PATH)
        return bigquery.Client(project=GCP_PROJECT_ID, credentials=credentials)
    else:
        # Use default credentials (e.g., from gcloud auth)
        return bigquery.Client(project=GCP_PROJECT_ID)

def create_bigquery_dataset_and_table(client: bigquery.Client):
    """Create BigQuery dataset and table if they don't exist"""
    # Create dataset
    dataset_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}"
    try:
        client.get_dataset(dataset_id)
        print(f"Dataset {dataset_id} already exists")
    except Exception:
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        dataset.description = "Golf shot data from Uneekor launch monitor"
        client.create_dataset(dataset)
        print(f"Created dataset {dataset_id}")

    # Create table with schema
    table_id = f"{dataset_id}.{BQ_TABLE_ID}"
    try:
        client.get_table(table_id)
        print(f"Table {table_id} already exists")
    except Exception:
        # Load schema from JSON file
        with open("bigquery_schema.json", "r") as f:
            schema_json = json.load(f)

        schema = []
        for field in schema_json:
            schema.append(bigquery.SchemaField(
                name=field["name"],
                field_type=field["type"],
                mode=field["mode"],
                description=field.get("description", "")
            ))

        table = bigquery.Table(table_id, schema=schema)
        table.description = "Golf shot data with detailed metrics for AI analysis"
        client.create_table(table)
        print(f"Created table {table_id}")

    return table_id

def fetch_shots_from_supabase():
    """Fetch all shots from Supabase"""
    supabase = get_supabase_client()
    print("Fetching shots from Supabase...")

    # Fetch all shots (paginated if needed)
    all_shots = []
    page_size = 1000
    offset = 0

    while True:
        shots = []
        for attempt in range(1, 4):
            try:
                response = supabase.table("shots").select("*").range(offset, offset + page_size - 1).execute()
                shots = response.data
                break
            except Exception as e:
                if attempt == 3:
                    raise
                print(f"Retrying Supabase fetch (attempt {attempt}/3): {e}")
                time.sleep(1.5 * attempt)

        if not shots:
            break

        all_shots.extend(shots)
        offset += page_size

        print(f"Fetched {len(all_shots)} shots so far...")

        if len(shots) < page_size:
            break

    print(f"Total shots fetched: {len(all_shots)}")
    return all_shots

def export_to_bigquery(shots, mode="append"):
    """
    Export shots to BigQuery

    Args:
        shots: List of shot dictionaries
        mode: 'append' (add new rows) or 'replace' (truncate and load)
    """
    if not shots:
        print("No shots to export")
        return 0

    bq_client = get_bigquery_client()
    table_id = create_bigquery_dataset_and_table(bq_client)

    print(f"Exporting {len(shots)} shots to BigQuery...")

    # Configure load job
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND if mode == "append" else bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION] if mode == "append" else None
    )

    # Load data
    try:
        load_job = bq_client.load_table_from_json(
            shots,
            table_id,
            job_config=job_config
        )
        load_job.result()  # Wait for job to complete

        # Get table info
        table = bq_client.get_table(table_id)
        print(f"✅ Successfully exported {len(shots)} shots to BigQuery")
        print(f"Table {table_id} now contains {table.num_rows} total rows")
        return len(shots)

    except Exception as e:
        print(f"❌ Error exporting to BigQuery: {e}")
        raise

def sync_incremental():
    """
    Sync only new shots from Supabase to BigQuery (incremental update)
    """
    bq_client = get_bigquery_client()
    supabase = get_supabase_client()

    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

    # Get latest timestamp from BigQuery
    query = f"""
        SELECT MAX(date_added) as latest_date
        FROM `{table_id}`
    """

    try:
        result = bq_client.query(query).result()
        row = next(result)
        latest_date = row.latest_date

        if latest_date:
            print(f"Latest shot in BigQuery: {latest_date}")

            # Fetch only newer shots from Supabase
            new_shots = []
            for attempt in range(1, 4):
                try:
                    response = supabase.table("shots").select("*").gt("date_added", latest_date.isoformat()).execute()
                    new_shots = response.data
                    break
                except Exception as e:
                    if attempt == 3:
                        raise
                    print(f"Retrying Supabase incremental fetch (attempt {attempt}/3): {e}")
                    time.sleep(1.5 * attempt)

            if new_shots:
                print(f"Found {len(new_shots)} new shots to sync")
                return export_to_bigquery(new_shots, mode="append")
            else:
                print("No new shots to sync")
                return 0
        else:
            print("BigQuery table is empty, doing full sync")
            shots = fetch_shots_from_supabase()
            return export_to_bigquery(shots, mode="replace")

    except Exception as e:
        print(f"Error during incremental sync: {e}")
        print("Falling back to full sync...")
        shots = fetch_shots_from_supabase()
        return export_to_bigquery(shots, mode="replace")

def main():
    import sys
    start_time = time.time()
    mode = "full"
    status = "success"
    shot_count = 0

    try:
        if len(sys.argv) > 1:
            command = sys.argv[1]
            if command == "full":
                mode = "full"
                print("Running FULL sync (replace all data)...")
                shots = fetch_shots_from_supabase()
                shot_count = export_to_bigquery(shots, mode="replace")
            elif command == "incremental":
                mode = "incremental"
                print("Running INCREMENTAL sync (add new shots only)...")
                shot_count = sync_incremental()
            else:
                print(f"Unknown command: {command}")
                print("Usage: python supabase_to_bigquery.py [full|incremental]")
                sys.exit(1)
        else:
            # Default to full sync
            mode = "full"
            print("Running FULL sync (replace all data)...")
            shots = fetch_shots_from_supabase()
            shot_count = export_to_bigquery(shots, mode="replace")
    except Exception as e:
        status = "failed"
        observability.append_event(
            "sync_runs.jsonl",
            {
                "status": status,
                "mode": mode,
                "shots": shot_count,
                "duration_sec": round(time.time() - start_time, 2),
                "error": str(e),
            },
        )
        raise
    else:
        observability.append_event(
            "sync_runs.jsonl",
            {
                "status": status,
                "mode": mode,
                "shots": shot_count,
                "duration_sec": round(time.time() - start_time, 2),
            },
        )

if __name__ == "__main__":
    main()
