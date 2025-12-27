"""
Shared configuration for Cloud Functions

Environment variables should be set in Cloud Function deployment config
"""
import os

# Google Cloud Project
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'valued-odyssey-474423-g1')
GCP_REGION = os.getenv('GCP_REGION', 'us-central1')

# BigQuery
BQ_DATASET_ID = os.getenv('BQ_DATASET_ID', 'golf_data')
BQ_TABLE_ID = os.getenv('BQ_TABLE_ID', 'shots')
BQ_FULL_TABLE_ID = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

# Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Pub/Sub Topics
PUBSUB_DATA_IMPORT_TOPIC = 'golf-data-imported'
PUBSUB_SYNC_COMPLETE_TOPIC = 'golf-sync-complete'
PUBSUB_ANALYSIS_TOPIC = 'golf-analysis-ready'

# Email settings (optional)
NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL', 'matt@coloradolawclassic.org')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')  # Optional for email notifications
