"""
Cloud Function: Auto-Sync Supabase to BigQuery

Triggers:
- HTTP request
- Pub/Sub message on 'golf-data-imported' topic
- Cloud Scheduler (periodic)

Functionality:
- Fetches new shots from Supabase since last sync
- Uploads to BigQuery (incremental)
- Publishes completion event to Pub/Sub
"""

import functions_framework
from google.cloud import bigquery, pubsub_v1
from supabase import create_client, Client
import os
import json
from datetime import datetime, timezone
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'valued-odyssey-474423-g1')
BQ_DATASET_ID = os.getenv('BQ_DATASET_ID', 'golf_data')
BQ_TABLE_ID = os.getenv('BQ_TABLE_ID', 'shots')
BQ_FULL_TABLE_ID = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize clients
bq_client = bigquery.Client(project=GCP_PROJECT_ID)
publisher = pubsub_v1.PublisherClient()


def get_last_sync_timestamp():
    """Get the timestamp of the most recent shot in BigQuery"""
    try:
        query = f"""
        SELECT MAX(date_added) as last_sync
        FROM `{BQ_FULL_TABLE_ID}`
        """
        result = bq_client.query(query).to_dataframe()

        if result.empty or result['last_sync'].iloc[0] is None:
            return None

        return result['last_sync'].iloc[0]
    except Exception as e:
        logger.warning(f"Could not get last sync timestamp: {e}")
        return None


def fetch_new_shots_from_supabase(since_timestamp=None):
    """Fetch shots from Supabase that are newer than the given timestamp"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials not configured")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Build query
    query = supabase.table('shots').select('*')

    if since_timestamp:
        # Filter for shots after last sync
        query = query.gt('date_added', since_timestamp.isoformat())

    # Order by date
    query = query.order('date_added', desc=False)

    # Execute query (with pagination for large datasets)
    all_shots = []
    page_size = 1000
    offset = 0

    while True:
        response = query.range(offset, offset + page_size - 1).execute()
        shots = response.data

        if not shots:
            break

        all_shots.extend(shots)
        offset += page_size

        if len(shots) < page_size:
            break

    logger.info(f"Fetched {len(all_shots)} new shots from Supabase")
    return all_shots


def upload_to_bigquery(shots):
    """Upload shots to BigQuery"""
    if not shots:
        logger.info("No shots to upload")
        return 0

    # Convert shots to BigQuery-compatible format
    # Handle timestamp conversion
    for shot in shots:
        if 'date_added' in shot and shot['date_added']:
            # Ensure timestamp is in ISO format
            if isinstance(shot['date_added'], str):
                shot['date_added'] = shot['date_added']
            else:
                shot['date_added'] = shot['date_added'].isoformat()

    # Configure load job
    job_config = bigquery.LoadJobConfig(
        schema=[],  # Auto-detect schema
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    # Load data
    job = bq_client.load_table_from_json(
        shots,
        BQ_FULL_TABLE_ID,
        job_config=job_config
    )

    # Wait for job to complete
    job.result()

    logger.info(f"Uploaded {len(shots)} shots to BigQuery")
    return len(shots)


def publish_sync_complete_event(shots_synced):
    """Publish event to Pub/Sub indicating sync is complete"""
    try:
        topic_path = publisher.topic_path(GCP_PROJECT_ID, 'golf-sync-complete')

        message_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'shots_synced': shots_synced,
            'table': BQ_FULL_TABLE_ID
        }

        future = publisher.publish(
            topic_path,
            json.dumps(message_data).encode('utf-8')
        )

        future.result()
        logger.info(f"Published sync complete event: {shots_synced} shots")
    except Exception as e:
        logger.warning(f"Could not publish sync event: {e}")


@functions_framework.http
def auto_sync_http(request):
    """
    HTTP-triggered function for manual or webhook-triggered sync

    Usage:
        curl -X POST https://REGION-PROJECT_ID.cloudfunctions.net/auto-sync \\
             -H "Content-Type: application/json" \\
             -d '{"full_sync": false}'
    """
    try:
        # Parse request
        request_json = request.get_json(silent=True)
        full_sync = False

        if request_json and 'full_sync' in request_json:
            full_sync = request_json['full_sync']

        # Get last sync timestamp (unless full sync requested)
        last_sync = None if full_sync else get_last_sync_timestamp()

        logger.info(f"Starting sync (full_sync={full_sync}, last_sync={last_sync})")

        # Fetch new shots
        new_shots = fetch_new_shots_from_supabase(since_timestamp=last_sync)

        # Upload to BigQuery
        shots_synced = upload_to_bigquery(new_shots)

        # Publish completion event
        publish_sync_complete_event(shots_synced)

        return {
            'status': 'success',
            'shots_synced': shots_synced,
            'full_sync': full_sync,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }, 200

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }, 500


@functions_framework.cloud_event
def auto_sync_pubsub(cloud_event):
    """
    Pub/Sub-triggered function for event-driven sync

    Triggered by 'golf-data-imported' topic when new data is added to Supabase
    """
    try:
        # Decode Pub/Sub message
        import base64
        message_data = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        logger.info(f"Received Pub/Sub message: {message_data}")

        # Parse message (optional: can contain metadata about what was imported)
        try:
            event_data = json.loads(message_data)
        except:
            event_data = {}

        # Get last sync timestamp
        last_sync = get_last_sync_timestamp()
        logger.info(f"Starting Pub/Sub-triggered sync (last_sync={last_sync})")

        # Fetch new shots
        new_shots = fetch_new_shots_from_supabase(since_timestamp=last_sync)

        # Upload to BigQuery
        shots_synced = upload_to_bigquery(new_shots)

        # Publish completion event
        publish_sync_complete_event(shots_synced)

        logger.info(f"Sync complete: {shots_synced} shots")

    except Exception as e:
        logger.error(f"Pub/Sub sync failed: {e}", exc_info=True)
        raise
