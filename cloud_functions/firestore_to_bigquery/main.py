"""
Cloud Function: Firestore → BigQuery Auto-Sync

Triggers:
- Firestore document write (onCreate, onUpdate)
- Automatically syncs shot data to BigQuery

Architecture:
- Firestore: Primary cloud database
- BigQuery: Analytics data warehouse
- Real-time sync on every write

This function is triggered automatically when a shot is written to Firestore,
eliminating the need for manual sync scripts.
"""

import functions_framework
from google.cloud import bigquery, firestore
from cloudevents.http import CloudEvent
import os
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'valued-odyssey-474423-g1')
BQ_DATASET_ID = os.getenv('BQ_DATASET_ID', 'golf_data')
BQ_TABLE_ID = os.getenv('BQ_TABLE_ID', 'shots')
BQ_FULL_TABLE_ID = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

# Initialize clients
bq_client = bigquery.Client(project=GCP_PROJECT_ID)
firestore_db = firestore.Client(project=GCP_PROJECT_ID)


def transform_firestore_to_bigquery(shot_data):
    """
    Transform Firestore document to BigQuery-compatible format

    Args:
        shot_data: Firestore document data

    Returns:
        Transformed dictionary ready for BigQuery
    """
    # Copy data to avoid modifying original
    transformed = dict(shot_data)

    # Handle timestamps - convert to ISO strings
    for field in ['date_added', 'session_date', 'migrated_at']:
        if field in transformed and transformed[field]:
            if hasattr(transformed[field], 'isoformat'):
                transformed[field] = transformed[field].isoformat()
            elif not isinstance(transformed[field], str):
                transformed[field] = str(transformed[field])

    # Ensure numeric fields are properly typed
    numeric_fields = [
        'carry', 'total', 'ball_speed', 'club_speed', 'smash',
        'back_spin', 'side_spin', 'launch_angle', 'side_angle',
        'club_path', 'face_angle', 'dynamic_loft', 'attack_angle',
        'descent_angle', 'apex', 'flight_time', 'side_distance',
        'impact_x', 'impact_y', 'optix_x', 'optix_y',
        'club_lie', 'lie_angle'
    ]

    for field in numeric_fields:
        if field in transformed:
            if transformed[field] is None or transformed[field] == '':
                transformed[field] = None
            else:
                try:
                    transformed[field] = float(transformed[field])
                except (ValueError, TypeError):
                    transformed[field] = None

    return transformed


def upsert_to_bigquery(shot_id, shot_data):
    """
    Upsert shot to BigQuery (insert or update if exists)

    Args:
        shot_id: Unique shot identifier
        shot_data: Shot data dictionary
    """
    try:
        # Transform data
        transformed = transform_firestore_to_bigquery(shot_data)

        # Ensure shot_id is in the data
        transformed['shot_id'] = shot_id

        # Build MERGE query (upsert)
        # This is more efficient than checking existence first
        query = f"""
        MERGE `{BQ_FULL_TABLE_ID}` T
        USING UNNEST([STRUCT(
            @shot_id AS shot_id,
            @session_id AS session_id,
            @club AS club,
            @carry AS carry,
            @total AS total,
            @ball_speed AS ball_speed,
            @club_speed AS club_speed,
            @smash AS smash,
            @back_spin AS back_spin,
            @side_spin AS side_spin,
            @launch_angle AS launch_angle,
            @side_angle AS side_angle,
            @club_path AS club_path,
            @face_angle AS face_angle,
            @dynamic_loft AS dynamic_loft,
            @attack_angle AS attack_angle,
            @descent_angle AS descent_angle,
            @apex AS apex,
            @flight_time AS flight_time,
            @side_distance AS side_distance,
            @impact_x AS impact_x,
            @impact_y AS impact_y,
            @optix_x AS optix_x,
            @optix_y AS optix_y,
            @club_lie AS club_lie,
            @lie_angle AS lie_angle,
            @shot_type AS shot_type,
            @impact_img AS impact_img,
            @swing_img AS swing_img,
            @video_frames AS video_frames,
            @date_added AS date_added,
            @session_date AS session_date
        )]) S
        ON T.shot_id = S.shot_id
        WHEN MATCHED THEN
            UPDATE SET
                session_id = S.session_id,
                club = S.club,
                carry = S.carry,
                total = S.total,
                ball_speed = S.ball_speed,
                club_speed = S.club_speed,
                smash = S.smash,
                back_spin = S.back_spin,
                side_spin = S.side_spin,
                launch_angle = S.launch_angle,
                side_angle = S.side_angle,
                club_path = S.club_path,
                face_angle = S.face_angle,
                dynamic_loft = S.dynamic_loft,
                attack_angle = S.attack_angle,
                descent_angle = S.descent_angle,
                apex = S.apex,
                flight_time = S.flight_time,
                side_distance = S.side_distance,
                impact_x = S.impact_x,
                impact_y = S.impact_y,
                optix_x = S.optix_x,
                optix_y = S.optix_y,
                club_lie = S.club_lie,
                lie_angle = S.lie_angle,
                shot_type = S.shot_type,
                impact_img = S.impact_img,
                swing_img = S.swing_img,
                video_frames = S.video_frames,
                session_date = S.session_date
        WHEN NOT MATCHED THEN
            INSERT (
                shot_id, session_id, club, carry, total, ball_speed,
                club_speed, smash, back_spin, side_spin, launch_angle,
                side_angle, club_path, face_angle, dynamic_loft,
                attack_angle, descent_angle, apex, flight_time,
                side_distance, impact_x, impact_y, optix_x, optix_y,
                club_lie, lie_angle, shot_type, impact_img, swing_img,
                video_frames, date_added, session_date
            )
            VALUES (
                S.shot_id, S.session_id, S.club, S.carry, S.total,
                S.ball_speed, S.club_speed, S.smash, S.back_spin,
                S.side_spin, S.launch_angle, S.side_angle, S.club_path,
                S.face_angle, S.dynamic_loft, S.attack_angle,
                S.descent_angle, S.apex, S.flight_time, S.side_distance,
                S.impact_x, S.impact_y, S.optix_x, S.optix_y,
                S.club_lie, S.lie_angle, S.shot_type, S.impact_img,
                S.swing_img, S.video_frames, S.date_added, S.session_date
            )
        """

        # Configure query job with parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("shot_id", "STRING", transformed.get('shot_id')),
                bigquery.ScalarQueryParameter("session_id", "STRING", transformed.get('session_id')),
                bigquery.ScalarQueryParameter("club", "STRING", transformed.get('club')),
                bigquery.ScalarQueryParameter("carry", "FLOAT64", transformed.get('carry')),
                bigquery.ScalarQueryParameter("total", "FLOAT64", transformed.get('total')),
                bigquery.ScalarQueryParameter("ball_speed", "FLOAT64", transformed.get('ball_speed')),
                bigquery.ScalarQueryParameter("club_speed", "FLOAT64", transformed.get('club_speed')),
                bigquery.ScalarQueryParameter("smash", "FLOAT64", transformed.get('smash')),
                bigquery.ScalarQueryParameter("back_spin", "FLOAT64", transformed.get('back_spin')),
                bigquery.ScalarQueryParameter("side_spin", "FLOAT64", transformed.get('side_spin')),
                bigquery.ScalarQueryParameter("launch_angle", "FLOAT64", transformed.get('launch_angle')),
                bigquery.ScalarQueryParameter("side_angle", "FLOAT64", transformed.get('side_angle')),
                bigquery.ScalarQueryParameter("club_path", "FLOAT64", transformed.get('club_path')),
                bigquery.ScalarQueryParameter("face_angle", "FLOAT64", transformed.get('face_angle')),
                bigquery.ScalarQueryParameter("dynamic_loft", "FLOAT64", transformed.get('dynamic_loft')),
                bigquery.ScalarQueryParameter("attack_angle", "FLOAT64", transformed.get('attack_angle')),
                bigquery.ScalarQueryParameter("descent_angle", "FLOAT64", transformed.get('descent_angle')),
                bigquery.ScalarQueryParameter("apex", "FLOAT64", transformed.get('apex')),
                bigquery.ScalarQueryParameter("flight_time", "FLOAT64", transformed.get('flight_time')),
                bigquery.ScalarQueryParameter("side_distance", "FLOAT64", transformed.get('side_distance')),
                bigquery.ScalarQueryParameter("impact_x", "FLOAT64", transformed.get('impact_x')),
                bigquery.ScalarQueryParameter("impact_y", "FLOAT64", transformed.get('impact_y')),
                bigquery.ScalarQueryParameter("optix_x", "FLOAT64", transformed.get('optix_x')),
                bigquery.ScalarQueryParameter("optix_y", "FLOAT64", transformed.get('optix_y')),
                bigquery.ScalarQueryParameter("club_lie", "FLOAT64", transformed.get('club_lie')),
                bigquery.ScalarQueryParameter("lie_angle", "FLOAT64", transformed.get('lie_angle')),
                bigquery.ScalarQueryParameter("shot_type", "STRING", transformed.get('shot_type')),
                bigquery.ScalarQueryParameter("impact_img", "STRING", transformed.get('impact_img')),
                bigquery.ScalarQueryParameter("swing_img", "STRING", transformed.get('swing_img')),
                bigquery.ScalarQueryParameter("video_frames", "STRING", transformed.get('video_frames')),
                bigquery.ScalarQueryParameter("date_added", "STRING", transformed.get('date_added')),
                bigquery.ScalarQueryParameter("session_date", "STRING", transformed.get('session_date')),
            ]
        )

        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        query_job.result()  # Wait for completion

        logger.info(f"Successfully synced shot {shot_id} to BigQuery")
        return True

    except Exception as e:
        logger.error(f"Failed to sync shot {shot_id} to BigQuery: {e}", exc_info=True)
        raise


@functions_framework.cloud_event
def firestore_to_bigquery_sync(cloud_event: CloudEvent):
    """
    Firestore-triggered function for automatic BigQuery sync

    Triggered when a document is written to the 'shots' collection in Firestore.
    Automatically syncs the data to BigQuery.

    For Gen2 Firestore triggers, the document path is in the 'document' attribute.
    """
    try:
        # Get document path from CloudEvent attributes
        # For Firestore events, the document path is in attributes['document']
        document_path = cloud_event.get('document')

        if not document_path:
            logger.error(f"No document path in event. Available attributes: {cloud_event.get_attributes()}")
            return

        logger.info(f"Processing Firestore event for document: {document_path}")

        # Extract shot_id from document path
        # Path format: projects/PROJECT/databases/(default)/documents/shots/SHOT_ID
        path_parts = document_path.split('/')

        if len(path_parts) < 2:
            logger.error(f"Invalid document path format: {document_path}")
            return

        # Get document ID (shot_id) - it's the last part of the path
        shot_id = path_parts[-1]

        # Verify it's from the 'shots' collection
        if 'shots' not in document_path:
            logger.info(f"Ignoring event for non-shots collection: {document_path}")
            return

        logger.info(f"Syncing shot {shot_id} from Firestore to BigQuery")

        # Get document data from Firestore directly
        # (fetching directly is more reliable than parsing event payload)
        doc_ref = firestore_db.collection('shots').document(shot_id)
        doc = doc_ref.get()

        if not doc.exists:
            logger.warning(f"Document {shot_id} not found in Firestore (may have been deleted)")
            return

        shot_data = doc.to_dict()

        # Sync to BigQuery
        upsert_to_bigquery(shot_id, shot_data)

        logger.info(f"Successfully synced shot {shot_id} to BigQuery")

    except Exception as e:
        logger.error(f"Firestore sync function failed: {e}", exc_info=True)
        # Re-raise to mark function as failed (allows retries)
        raise
