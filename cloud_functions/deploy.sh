#!/bin/bash

# Cloud Functions Deployment Script
# Deploys both auto-sync and daily-insights functions to Google Cloud

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
echo "Deploying Golf Data Cloud Functions"
echo "============================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Create Pub/Sub topics if they don't exist
echo "📡 Creating Pub/Sub topics..."
gcloud pubsub topics create golf-data-imported --project=$PROJECT_ID 2>/dev/null || echo "  ✓ golf-data-imported already exists"
gcloud pubsub topics create golf-sync-complete --project=$PROJECT_ID 2>/dev/null || echo "  ✓ golf-sync-complete already exists"
gcloud pubsub topics create golf-analysis-ready --project=$PROJECT_ID 2>/dev/null || echo "  ✓ golf-analysis-ready already exists"
echo ""

# Deploy Auto-Sync Function
echo "🔄 Deploying Auto-Sync Function..."
cd auto_sync

# HTTP-triggered version
gcloud functions deploy auto-sync-http \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=auto_sync_http \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,BQ_DATASET_ID=$BQ_DATASET_ID,BQ_TABLE_ID=$BQ_TABLE_ID,SUPABASE_URL=$SUPABASE_URL,SUPABASE_KEY=$SUPABASE_KEY" \
    --timeout=540s \
    --memory=512MB \
    --project=$PROJECT_ID

# Pub/Sub-triggered version
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
echo "  ✅ Auto-Sync deployed!"
echo ""

# Deploy Daily Insights Function
echo "🤖 Deploying Daily Insights Function..."
cd daily_insights

# HTTP-triggered version
gcloud functions deploy daily-insights-http \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=daily_insights_http \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,BQ_DATASET_ID=$BQ_DATASET_ID,BQ_TABLE_ID=$BQ_TABLE_ID,GEMINI_API_KEY=$GEMINI_API_KEY,NOTIFICATION_EMAIL=$NOTIFICATION_EMAIL" \
    --timeout=540s \
    --memory=1024MB \
    --project=$PROJECT_ID

# Scheduled version (Cloud Scheduler will trigger this)
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
echo "  ✅ Daily Insights deployed!"
echo ""

# Create Cloud Scheduler job for daily insights
echo "⏰ Setting up Cloud Scheduler..."

# Create Pub/Sub topic for scheduler
gcloud pubsub topics create golf-daily-trigger --project=$PROJECT_ID 2>/dev/null || echo "  ✓ golf-daily-trigger already exists"

# Create or update scheduler job (runs daily at 8:00 AM)
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
echo "🧪 Test commands:"
echo ""
echo "# Test auto-sync:"
echo "curl -X POST https://$REGION-$PROJECT_ID.cloudfunctions.net/auto-sync-http"
echo ""
echo "# Test daily insights:"
echo "curl -X POST https://$REGION-$PROJECT_ID.cloudfunctions.net/daily-insights-http"
echo ""
echo "# Test with email:"
echo 'curl -X POST https://'$REGION'-'$PROJECT_ID'.cloudfunctions.net/daily-insights-http -H "Content-Type: application/json" -d '"'"'{"send_email": true}'"'"
echo ""
echo "============================================"
