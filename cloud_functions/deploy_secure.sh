#!/bin/bash

# Cloud Functions Deployment Script (Secure)
# Deploys with authentication required (more secure)

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-valued-odyssey-474423-g1}"
REGION="${GCP_REGION:-us-central1}"

# Load environment variables from .env file
if [ -f "../.env" ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' ../.env | xargs)
fi

echo "============================================"
echo "Deploying Golf Data Cloud Functions (Secure)"
echo "============================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Note: Functions require authentication"
echo ""

# Create Pub/Sub topics if they don't exist
echo "📡 Creating Pub/Sub topics..."
gcloud pubsub topics create golf-data-imported --project=$PROJECT_ID 2>/dev/null || echo "  ✓ golf-data-imported already exists"
gcloud pubsub topics create golf-sync-complete --project=$PROJECT_ID 2>/dev/null || echo "  ✓ golf-sync-complete already exists"
gcloud pubsub topics create golf-analysis-ready --project=$PROJECT_ID 2>/dev/null || echo "  ✓ golf-analysis-ready already exists"
gcloud pubsub topics create golf-daily-trigger --project=$PROJECT_ID 2>/dev/null || echo "  ✓ golf-daily-trigger already exists"
echo ""

# Deploy Auto-Sync Function (HTTP)
echo "🔄 Deploying Auto-Sync Function (HTTP)..."
cd auto_sync

gcloud functions deploy auto-sync-http \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=auto_sync_http \
    --trigger-http \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,BQ_DATASET_ID=$BQ_DATASET_ID,BQ_TABLE_ID=$BQ_TABLE_ID,SUPABASE_URL=$SUPABASE_URL,SUPABASE_KEY=$SUPABASE_KEY" \
    --timeout=540s \
    --memory=512MB \
    --project=$PROJECT_ID

cd ..
echo "  ✅ Auto-Sync HTTP deployed!"
echo ""

# Deploy Auto-Sync Function (Pub/Sub)
echo "🔄 Deploying Auto-Sync Function (Pub/Sub)..."
cd auto_sync

gcloud functions deploy auto-sync-pubsub \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=auto_sync_pubsub \
    --trigger-topic=golf-data-imported \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,BQ_DATASET_ID=$BQ_DATASET_ID,BQ_TABLE_ID=$BQ_TABLE_ID,SUPABASE_URL=$SUPABASE_URL,SUPABASE_KEY=$SUPABASE_KEY" \
    --timeout=540s \
    --memory=512MB \
    --project=$PROJECT_ID

cd ..
echo "  ✅ Auto-Sync Pub/Sub deployed!"
echo ""

# Deploy Daily Insights Function (HTTP)
echo "🤖 Deploying Daily Insights Function (HTTP)..."
cd daily_insights

gcloud functions deploy daily-insights-http \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=daily_insights_http \
    --trigger-http \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,BQ_DATASET_ID=$BQ_DATASET_ID,BQ_TABLE_ID=$BQ_TABLE_ID,GEMINI_API_KEY=$GEMINI_API_KEY,NOTIFICATION_EMAIL=$NOTIFICATION_EMAIL" \
    --timeout=540s \
    --memory=1024MB \
    --project=$PROJECT_ID

cd ..
echo "  ✅ Daily Insights HTTP deployed!"
echo ""

# Deploy Daily Insights Function (Scheduled)
echo "🤖 Deploying Daily Insights Function (Scheduled)..."
cd daily_insights

gcloud functions deploy daily-insights-scheduled \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=daily_insights_scheduled \
    --trigger-topic=golf-daily-trigger \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,BQ_DATASET_ID=$BQ_DATASET_ID,BQ_TABLE_ID=$BQ_TABLE_ID,GEMINI_API_KEY=$GEMINI_API_KEY,NOTIFICATION_EMAIL=$NOTIFICATION_EMAIL,AUTO_SEND_EMAIL=false" \
    --timeout=540s \
    --memory=1024MB \
    --project=$PROJECT_ID

cd ..
echo "  ✅ Daily Insights Scheduled deployed!"
echo ""

# Create Cloud Scheduler job for daily insights
echo "⏰ Setting up Cloud Scheduler..."
gcloud scheduler jobs create pubsub golf-daily-insights \
    --location=$REGION \
    --schedule="0 8 * * *" \
    --topic=golf-daily-trigger \
    --message-body='{"trigger":"scheduled"}' \
    --project=$PROJECT_ID \
    2>/dev/null || gcloud scheduler jobs update pubsub golf-daily-insights \
    --location=$REGION \
    --schedule="0 8 * * *" \
    --topic=golf-daily-trigger \
    --message-body='{"trigger":"scheduled"}' \
    --project=$PROJECT_ID

echo "  ✅ Scheduler configured (daily at 8:00 AM)"
echo ""

echo "============================================"
echo "✅ Deployment Complete!"
echo "============================================"
echo ""
echo "📝 Function URLs:"
echo ""
echo "Auto-Sync (HTTP):"
echo "  https://$REGION-$PROJECT_ID.cloudfunctions.net/auto-sync-http"
echo ""
echo "Daily Insights (HTTP):"
echo "  https://$REGION-$PROJECT_ID.cloudfunctions.net/daily-insights-http"
echo ""
echo "📅 Scheduled Jobs:"
echo "  Daily Insights: Every day at 8:00 AM"
echo ""
echo "🔐 Authentication Required"
echo "  Functions require authentication. Use:"
echo ""
echo "  curl -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" \\"
echo "       https://$REGION-$PROJECT_ID.cloudfunctions.net/auto-sync-http"
echo ""
echo "============================================"
