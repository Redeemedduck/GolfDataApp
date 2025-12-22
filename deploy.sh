#!/bin/bash

# Cloud Run Deployment Script for Golf Data Platform
set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-valued-odyssey-474423-g1}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="golf-data-app"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "============================================"
echo "Deploying Golf Data Platform to Cloud Run"
echo "============================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Build the Docker image
echo "🐳 Building Docker image..."
docker build -t $IMAGE_NAME:latest .

# Push to Google Container Registry
echo "📤 Pushing image to GCR..."
docker push $IMAGE_NAME:latest

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE_NAME:latest \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,BQ_DATASET_ID=golf_data,BQ_TABLE_ID=shots" \
  --max-instances=10 \
  --min-instances=0

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format='value(status.url)')

echo ""
echo "============================================"
echo "✅ Deployment Complete!"
echo "============================================"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "You can now access your golf data platform at the URL above!"
echo ""
