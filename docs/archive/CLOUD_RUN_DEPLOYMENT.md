# Google Cloud Run Deployment Guide

This guide explains how to deploy the Golf Data App as a containerized service on Google Cloud Run.

## 📋 Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Google Cloud SDK (gcloud)** installed locally
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

3. **Docker** installed for local testing (optional but recommended)
   ```bash
   # Test Docker installation
   docker --version
   ```

> **Note**: The Docker image includes Playwright/Chromium for browser automation.
> This adds ~350MB to the image size but enables automated session discovery.

4. **Project Setup**
   ```bash
   # Set your GCP project ID
   export PROJECT_ID="your-project-id"
   gcloud config set project $PROJECT_ID

   # Enable required APIs
   gcloud services enable \
     cloudbuild.googleapis.com \
     run.googleapis.com \
     containerregistry.googleapis.com \
     artifactregistry.googleapis.com
   ```

---

## Quick Deployment (Recommended)

I've created an automated deployment script `deploy.sh` that handles the API enabling, secret management, building, and deployment in one go.

```bash
# Ensure the script is executable
chmod +x deploy.sh

# Run the deployment
./deploy.sh
```

> [!NOTE]
> The script will prompt for your GCP credentials if you aren't logged in. It securely maps your `.env` variables to **GCP Secret Manager**.

## Manual Deployment Methods

This method builds and deploys in one command using Cloud Build:

```bash
# Deploy directly from source
gcloud run deploy golf-data-app \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0
```

**What this does:**
- Builds the Docker image using Cloud Build
- Pushes to Artifact Registry
- Deploys to Cloud Run
- Allocates 1GB RAM and 1 CPU
- Allows public access (remove `--allow-unauthenticated` for private)

### Method 2: Build & Deploy Separately

For more control over the build and deploy process:

```bash
# 1. Set variables
export PROJECT_ID=$(gcloud config get-value project)
export SERVICE_NAME="golf-data-app"
export REGION="us-central1"
export IMAGE="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# 2. Build the Docker image locally (optional test)
docker build -t $IMAGE .

# 3. Submit build to Cloud Build
gcloud builds submit --tag $IMAGE

# 4. Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10
```

### Method 3: Using Artifact Registry (Recommended for Production)

Artifact Registry is the newer, recommended alternative to Container Registry:

```bash
# 1. Create Artifact Registry repository
export REGION="us-central1"
export REPO_NAME="golf-app-repo"

gcloud artifacts repositories create $REPO_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="Golf Data App container images"

# 2. Configure Docker auth
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 3. Build and tag image
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/golf-data-app:latest"

docker build -t $IMAGE .
docker push $IMAGE

# 4. Deploy to Cloud Run
gcloud run deploy golf-data-app \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1
```

---

## 🔐 Environment Variables & Secrets

### Option 1: Using Environment Variables (Not Recommended for Secrets)

```bash
gcloud run deploy golf-data-app \
  --set-env-vars="SUPABASE_URL=https://your-project.supabase.co" \
  --set-env-vars="SUPABASE_KEY=your-anon-key"
```

### Option 2: Using Secret Manager (Recommended)

```bash
# 1. Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# 2. Create secrets
echo -n "your-supabase-url" | \
  gcloud secrets create supabase-url --data-file=-

echo -n "your-supabase-anon-key" | \
  gcloud secrets create supabase-key --data-file=-

echo -n "your-gemini-api-key" | \
  gcloud secrets create gemini-api-key --data-file=-

# 3. Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding supabase-url \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Repeat for other secrets...

# 4. Deploy with secrets
gcloud run deploy golf-data-app \
  --set-secrets="SUPABASE_URL=supabase-url:latest" \
  --set-secrets="SUPABASE_KEY=supabase-key:latest" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest"
```

### Option 3: Automation Secrets (For Scraper Automation)

If using the browser automation feature for hands-free data import:

```bash
# Create automation secrets
echo -n "your-uneekor-email" | \
  gcloud secrets create uneekor-username --data-file=-

echo -n "your-uneekor-password" | \
  gcloud secrets create uneekor-password --data-file=-

echo -n "https://hooks.slack.com/services/..." | \
  gcloud secrets create slack-webhook --data-file=-

# Deploy with automation secrets
gcloud run deploy golf-data-app \
  --set-secrets="SUPABASE_URL=supabase-url:latest" \
  --set-secrets="SUPABASE_KEY=supabase-key:latest" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
  --set-secrets="UNEEKOR_USERNAME=uneekor-username:latest" \
  --set-secrets="UNEEKOR_PASSWORD=uneekor-password:latest" \
  --set-secrets="SLACK_WEBHOOK_URL=slack-webhook:latest"
```

> **Note**: Browser automation on Cloud Run runs in headless mode.
> Cookies cannot persist (ephemeral storage), so env credentials are required.

---

## 💾 Database Considerations

### ⚠️ Important: SQLite Limitations on Cloud Run

Cloud Run containers are **stateless** - any data written to the filesystem (including SQLite) will be lost when the container restarts.

### Solutions:

#### Option 1: Use Supabase Only (Recommended)

The app already has Supabase integration in `golf_db.py`. Configure it to use Supabase as the primary database:

```bash
# Deploy with Supabase credentials
gcloud run deploy golf-data-app \
  --set-secrets="SUPABASE_URL=supabase-url:latest" \
  --set-secrets="SUPABASE_KEY=supabase-key:latest"
```

**Modify `golf_db.py`** to use Supabase as primary instead of SQLite when running in Cloud Run:

```python
# Add this check at the top of golf_db.py
import os

# Detect Cloud Run environment
IS_CLOUD_RUN = os.getenv('K_SERVICE') is not None

# Use Supabase as primary in Cloud Run
if IS_CLOUD_RUN and not supabase:
    raise Exception("Supabase credentials required for Cloud Run deployment")
```

#### Option 2: Cloud Storage for SQLite (Not Recommended)

Mount Cloud Storage as a volume:

```bash
# Create bucket
gsutil mb -l us-central1 gs://golf-data-app-db

# Deploy with volume mount
gcloud run deploy golf-data-app \
  --add-volume name=golf-db,type=cloud-storage,bucket=golf-data-app-db \
  --add-volume-mount volume=golf-db,mount-path=/app/data
```

**Note**: Cloud Storage is not ideal for SQLite due to locking issues.

#### Option 3: Cloud SQL for PostgreSQL

For production workloads, consider migrating to Cloud SQL:

```bash
# Create Cloud SQL instance
gcloud sql instances create golf-data-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Connect Cloud Run to Cloud SQL
gcloud run deploy golf-data-app \
  --add-cloudsql-instances=PROJECT_ID:us-central1:golf-data-db
```

---

## 🧪 Local Testing

Test the Docker container locally before deploying:

```bash
# 1. Build the image
docker build -t golf-data-app .

# 2. Run locally
docker run -p 8080:8080 \
  -e SUPABASE_URL="your-url" \
  -e SUPABASE_KEY="your-key" \
  golf-data-app

# 3. Open browser
open http://localhost:8080
```

### Test with .env file:

```bash
# Create .env file with credentials
cat > .env << EOF
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
GEMINI_API_KEY=your-gemini-key
EOF

# Run with env file
docker run -p 8080:8080 --env-file .env golf-data-app
```

---

## 📊 Monitoring & Logs

### View Logs

```bash
# Stream logs in real-time
gcloud run services logs tail golf-data-app --region us-central1

# View recent logs
gcloud run services logs read golf-data-app --region us-central1 --limit 50
```

### Monitoring Dashboard

1. Go to [Cloud Console](https://console.cloud.google.com/run)
2. Select your service
3. View metrics: Request count, latency, memory usage, CPU utilization

### Set Up Alerts

```bash
# Create alert for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Golf App Errors" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=60s
```

---

## 🔄 CI/CD with Cloud Build

Create `cloudbuild.yaml` for automated deployments:

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/golf-data-app:$COMMIT_SHA', '.']

  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/golf-data-app:$COMMIT_SHA']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'golf-data-app'
      - '--image=gcr.io/$PROJECT_ID/golf-data-app:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/golf-data-app:$COMMIT_SHA'
```

### Trigger on Git Push

```bash
# Connect repository and create trigger
gcloud builds triggers create github \
  --repo-name=GolfDataApp \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

---

## 💰 Cost Optimization

### Free Tier

Cloud Run offers generous free tier:
- 2 million requests/month
- 360,000 GB-seconds memory
- 180,000 vCPU-seconds compute

### Cost Reduction Tips

```bash
# 1. Set min instances to 0 (scale to zero)
gcloud run services update golf-data-app \
  --min-instances 0

# 2. Reduce memory allocation
gcloud run services update golf-data-app \
  --memory 512Mi

# 3. Set max instances to prevent runaway costs
gcloud run services update golf-data-app \
  --max-instances 5

# 4. Set request timeout
gcloud run services update golf-data-app \
  --timeout 60
```

### Monitor Costs

```bash
# View billing
gcloud billing accounts list

# Set budget alerts in Cloud Console
```

---

## 🔒 Security Best Practices

### 1. Require Authentication

```bash
# Remove public access
gcloud run services remove-iam-policy-binding golf-data-app \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region us-central1

# Add specific users
gcloud run services add-iam-policy-binding golf-data-app \
  --member="user:your-email@gmail.com" \
  --role="roles/run.invoker" \
  --region us-central1
```

### 2. Use Identity-Aware Proxy (IAP)

For authenticated access with Google accounts:

```bash
# Enable IAP
gcloud run services update golf-data-app \
  --ingress internal-and-cloud-load-balancing

# Configure Load Balancer with IAP
# (See Google Cloud IAP documentation)
```

### 3. Custom Domain with HTTPS

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service golf-data-app \
  --domain golf.yourdomain.com \
  --region us-central1

# SSL certificate is automatically provisioned
```

---

## 🐛 Troubleshooting

### Container Fails to Start

```bash
# Check build logs
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')

# Check service logs
gcloud run services logs read golf-data-app --region us-central1 --limit 100
```

### Port Binding Issues

Ensure Streamlit is configured for port 8080 (already done in Dockerfile and config.toml).

### Memory Issues

```bash
# Increase memory allocation
gcloud run services update golf-data-app --memory 2Gi
```

### Database Connection Issues

```bash
# Verify secrets are set
gcloud run services describe golf-data-app --region us-central1 --format=yaml | grep -A 10 env
```

---

## 📚 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Streamlit Cloud Run Guide](https://docs.streamlit.io/knowledge-base/tutorials/deploy/docker)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)

---

## 🎯 Quick Start Summary

```bash
# 1. Set project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# 2. Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com

# 3. Deploy (builds automatically)
gcloud run deploy golf-data-app \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi

# 4. Get the URL
gcloud run services describe golf-data-app \
  --region us-central1 \
  --format='value(status.url)'
```

**That's it!** Your Golf Data App should now be running on Cloud Run.

---

**Last Updated**: 2026-01-25
**For**: Branch `production-no-ml` with Playwright automation
