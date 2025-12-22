# Golf Data Platform - AI-Powered Analysis

A professional React/Next.js web application for golf performance analysis, powered by Vertex AI and BigQuery.

## Features

- **AI Golf Coach**: Conversational interface powered by Vertex AI Agent Builder
- **Real-time Data Access**: Direct integration with BigQuery golf shot database (555+ shots)
- **Performance Visualization**: Interactive charts and statistics
- **Session Tracking**: Historical performance across multiple practice sessions
- **Cloud-Native**: Containerized and deployed on Google Cloud Run

## Tech Stack

- **Frontend**: Next.js 16 + React 19 + TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Icons**: Lucide React
- **AI**: Vertex AI Agent Builder
- **Data**: BigQuery
- **Deployment**: Docker + Google Cloud Run

## Project Structure

```
golf-data-app/
├── src/
│   ├── app/
│   │   ├── api/chat/          # Vertex AI chat endpoint
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Main dashboard
│   │   └── globals.css         # Global styles
│   ├── components/
│   │   ├── ChatInterface.tsx   # AI chat component
│   │   └── ClubStatsChart.tsx  # Data visualization
│   └── types/
│       └── golf.ts             # TypeScript definitions
├── Dockerfile                  # Multi-stage Docker build
├── deploy.sh                   # Cloud Run deployment script
└── package.json                # Dependencies
```

## Local Development

### Prerequisites

- Node.js 20+
- npm or yarn
- Google Cloud SDK (for deployment)
- Docker (for containerization)

### Setup

1. **Clone and install dependencies:**
   ```bash
   cd /Users/duck/public/golf-data-app
   npm install
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your GCP credentials
   ```

3. **Run development server:**
   ```bash
   npm run dev
   ```

4. **Open in browser:**
   ```
   http://localhost:3000
   ```

## Deployment to Google Cloud Run

### Prerequisites

- Google Cloud Project: `valued-odyssey-474423-g1`
- APIs enabled:
  - Cloud Run API
  - Container Registry API
  - Vertex AI API
  - BigQuery API

### Deploy

1. **Authenticate with Google Cloud:**
   ```bash
   gcloud auth login
   gcloud config set project valued-odyssey-474423-g1
   ```

2. **Configure Docker for GCR:**
   ```bash
   gcloud auth configure-docker
   ```

3. **Run deployment script:**
   ```bash
   ./deploy.sh
   ```

The script will:
- Build Docker image
- Push to Google Container Registry
- Deploy to Cloud Run
- Output the public URL

### Manual Deployment

```bash
# Build image
docker build -t gcr.io/valued-odyssey-474423-g1/golf-data-app:latest .

# Push to GCR
docker push gcr.io/valued-odyssey-474423-g1/golf-data-app:latest

# Deploy to Cloud Run
gcloud run deploy golf-data-app \
  --image=gcr.io/valued-odyssey-474423-g1/golf-data-app:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --set-env-vars="GCP_PROJECT_ID=valued-odyssey-474423-g1,GCP_REGION=us-central1"
```

## Architecture

### Data Flow

```
User Browser
    ↓
Next.js Frontend (Cloud Run)
    ↓
/api/chat endpoint
    ↓
Vertex AI Agent Builder
    ↓
BigQuery (golf_data.shots table)
    ↓
AI-generated insights returned to user
```

### Integration with Existing System

This application integrates with:
- **BigQuery**: Reads shot data from `valued-odyssey-474423-g1.golf_data.shots`
- **Vertex AI Agent**: Uses Phase 1 agent for conversational analysis
- **Cloud Functions**: Can trigger auto-sync and daily insights functions

## Next Steps

### Phase 3A: Vertex AI Integration (In Progress)

The current implementation uses a mock API response. Next steps:

1. **Integrate Vertex AI Agent SDK** in `src/app/api/chat/route.ts`:
   ```typescript
   import { DiscoveryEngineClient } from '@google-cloud/aiplatform';
   // Connect to Phase 1 Vertex AI agent
   ```

2. **Add BigQuery data fetching** for real-time statistics

3. **Implement conversation memory** for multi-turn dialogues

### Phase 3B: Enhanced Features

- [ ] Session browser with filtering
- [ ] Advanced data visualizations (scatter plots, heatmaps)
- [ ] Export reports (PDF generation)
- [ ] Mobile-responsive design improvements
- [ ] Dark mode toggle

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GCP_PROJECT_ID` | Google Cloud Project ID | `valued-odyssey-474423-g1` |
| `GCP_REGION` | Cloud Run region | `us-central1` |
| `BQ_DATASET_ID` | BigQuery dataset | `golf_data` |
| `BQ_TABLE_ID` | BigQuery table | `shots` |
| `VERTEX_AI_LOCATION` | Vertex AI region | `us-central1` |

## Monitoring

- **Cloud Run Logs**: `gcloud run services logs read golf-data-app --region=us-central1`
- **Service Status**: `gcloud run services describe golf-data-app --region=us-central1`

## Cost Estimates

- **Cloud Run**: ~$0-5/month (minimal traffic)
- **BigQuery**: Already covered by existing usage
- **Vertex AI**: ~$0.001 per conversation
- **Container Registry**: <$1/month storage

**Total estimated cost**: **~$5-10/month** for low-moderate usage

## Support

For issues or questions, refer to:
- Phase 1 Documentation: `PHASE1_AGENT_BUILDER_GUIDE.md`
- Phase 2 Documentation: `PHASE2_AUTOMATION_GUIDE.md`
- Main project: `/Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My Drive/2025 Golf Season/GolfDataApp`
