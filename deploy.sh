#!/bin/bash
# Deployment script for GolfDataApp on Google Cloud Run

# 1. Configuration
PROJECT_ID="valued-odyssey-474423-g1"
SERVICE_NAME="golf-data-app"
REGION="us-central1"

# Load credentials from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "🚀 Starting deployment for project: $PROJECT_ID"

# 2. Set project
gcloud config set project $PROJECT_ID

# 3. Enable APIs
echo "🔧 Enabling required APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com

# 4. Create Secrets (if they don't exist)
echo "🔐 Setting up secrets in Secret Manager..."

function create_secret() {
    NAME=$1
    VALUE=$2
    if ! gcloud secrets describe $NAME &>/dev/null; then
        echo "Creating secret $NAME..."
        echo -n "$VALUE" | gcloud secrets create $NAME --data-file=-
    else
        echo "Secret $NAME already exists. Updating version..."
        echo -n "$VALUE" | gcloud secrets versions add $NAME --data-file=-
    fi
}

create_secret "SUPABASE_URL" "$SUPABASE_URL"
create_secret "SUPABASE_KEY" "$SUPABASE_KEY"
create_secret "GEMINI_API_KEY" "$GEMINI_API_KEY"

# 5. Grant permissions to Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "🛡️ Granting Secret Manager Access to $SERVICE_ACCOUNT..."
gcloud secrets add-iam-policy-binding SUPABASE_URL --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding SUPABASE_KEY --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding GEMINI_API_KEY --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/secretmanager.secretAccessor"

# 6. Build and Deploy
echo "📦 Building and deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --set-secrets="SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_KEY=SUPABASE_KEY:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest"

# 7. Final URL
echo "✨ Deployment complete!"
gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)'
