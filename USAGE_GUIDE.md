# Golf Data Platform - Complete Usage Guide

## Quick Start

### 1. Import New Uneekor Data

**Step 1: Get Your Uneekor URL**
- Go to your Uneekor web portal (my.uneekor.com)
- Complete a practice session
- Open the session report
- Copy the URL from your browser (it looks like: `https://my.uneekor.com/report?id=12345&key=abc123`)

**Step 2: Run the Streamlit Data Import App**

```bash
# Navigate to main project
cd "/Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My Drive/2025 Golf Season/GolfDataApp"

# Run with Docker (recommended)
./docker-quickstart.sh

# OR run locally
streamlit run app.py
```

**Step 3: Import Data**
1. Open http://localhost:8501 in your browser
2. Paste your Uneekor URL in the sidebar
3. Click "Import Data from Uneekor"
4. Data will be saved to:
   - SQLite database (`./data/golf_stats.db`)
   - Supabase (cloud backup)
   - Media files downloaded to `./media/`

**Step 4: Sync to BigQuery (Optional but Recommended)**

```bash
# From main project directory
python scripts/supabase_to_bigquery.py incremental
```

---

### 2. Analyze with AI Coach (Two Options)

#### Option A: Streamlit App (Local Analysis)
- Already running at http://localhost:8501
- Uses Gemini AI with code execution
- Can view shots, charts, and videos
- Best for: Interactive exploration and data entry

#### Option B: Next.js Web App (Cloud-Ready Analysis)
```bash
# Navigate to new web app
cd /Users/duck/public/golf-data-app

# Install dependencies (first time only)
npm install

# Start development server
npm run dev

# Open in browser
open http://localhost:3000
```

- Modern professional interface
- Conversational AI with BigQuery integration
- Performance dashboards
- Best for: Cleaner UI, cloud deployment

---

## Detailed Workflows

### Workflow 1: After Practice Session

```bash
# 1. Import new data
cd "/Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My Drive/2025 Golf Season/GolfDataApp"
streamlit run app.py
# → Paste Uneekor URL → Import

# 2. Sync to BigQuery
python scripts/supabase_to_bigquery.py incremental

# 3. Get AI insights (choose one):

# Option A: Streamlit app (already open)
# → Go to "AI Coach" tab
# → Ask questions about your session

# Option B: Next.js app
cd /Users/duck/public/golf-data-app
npm run dev
# → Open http://localhost:3000
# → Chat with AI coach
```

### Workflow 2: View Historical Analysis

**Streamlit App:**
```bash
cd "/Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My Drive/2025 Golf Season/GolfDataApp"
streamlit run app.py
```
- Select session from dropdown
- View shot-by-shot data
- Download videos/images
- Chat with AI coach

**Next.js App:**
```bash
cd /Users/duck/public/golf-data-app
npm run dev
open http://localhost:3000
```
- View performance dashboard
- Ask AI coach about trends
- See club-by-club stats

---

## Environment Setup

### Required Environment Variables

**For Streamlit App** (`.env` in main project):
```bash
# Supabase (Cloud Backup)
SUPABASE_URL=https://lhccrzxgnmynxmvoydkm.supabase.co
SUPABASE_KEY=your-supabase-key

# Google Cloud
GCP_PROJECT_ID=valued-odyssey-474423-g1
BQ_DATASET_ID=golf_data
BQ_TABLE_ID=shots

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key
```

**For Next.js App** (`.env.local` in `/Users/duck/public/golf-data-app`):
```bash
GCP_PROJECT_ID=valued-odyssey-474423-g1
GCP_REGION=us-central1
BQ_DATASET_ID=golf_data
BQ_TABLE_ID=shots
GEMINI_API_KEY=your-gemini-api-key
```

### Getting API Keys

**Gemini API Key:**
1. Go to https://ai.google.dev/
2. Click "Get API Key"
3. Copy key to `.env` files

**Google Cloud Authentication:**
```bash
# Authenticate for BigQuery access
gcloud auth application-default login
```

---

## Common Operations

### Add New Data from Uneekor

1. **Get URL**: Copy from Uneekor web portal after practice
2. **Import**: Paste in Streamlit sidebar → "Import Data"
3. **Verify**: Check "Session Browser" tab to see new shots
4. **Sync**: Run `python scripts/supabase_to_bigquery.py incremental`

### Query Your Data

**Streamlit App:**
- Use AI Coach tab
- Ask natural language questions
- Get charts and analysis

**Next.js App:**
- Chat interface at http://localhost:3000
- Conversational analysis with BigQuery data
- Performance dashboards

### Export Data

**CSV Export:**
```python
# In Streamlit app
# → "Session Browser" tab
# → "Export to CSV" button
```

**BigQuery Direct:**
```sql
-- Query in BigQuery console
SELECT * FROM `valued-odyssey-474423-g1.golf_data.shots`
WHERE club = 'Driver'
ORDER BY date_added DESC
LIMIT 100
```

---

## Architecture Overview

### Data Storage

```
Uneekor API
    ↓
Streamlit App (import)
    ↓
├─→ SQLite (local-first)         → 380 shots
│   └─ /Users/.../GolfDataApp/data/golf_stats.db
│
└─→ Supabase (cloud backup)      → 555 shots
    └─ https://lhccrzxgnmynxmvoydkm.supabase.co
        ↓
    BigQuery (data warehouse)    → 555 shots
    └─ valued-odyssey-474423-g1.golf_data.shots
        ↓
    AI Analysis
    ├─→ Streamlit AI Coach (Gemini 2.0)
    └─→ Next.js AI Coach (Gemini 1.5)
```

### Applications

**1. Streamlit App** (Main Project)
- **Location**: `~/GoogleDrive/.../GolfDataApp/`
- **Port**: http://localhost:8501
- **Purpose**: Data import, detailed analysis, media viewing
- **Best for**: Data entry and exploration

**2. Next.js App** (New Professional UI)
- **Location**: `/Users/duck/public/golf-data-app`
- **Port**: http://localhost:3000
- **Purpose**: Modern AI chat interface, dashboards
- **Best for**: Daily analysis and cloud deployment

**3. Cloud Functions** (Automation)
- Auto-sync: Supabase → BigQuery
- Daily insights: Automated AI reports
- Deployed to Google Cloud

---

## Troubleshooting

### "Can't connect to BigQuery"

**Solution:**
```bash
# Re-authenticate
gcloud auth application-default login

# Verify credentials
gcloud auth list
```

### "Gemini API error"

**Check API key:**
```bash
# Verify .env file has key
cat .env | grep GEMINI_API_KEY

# Test API key works
curl -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=YOUR_API_KEY"
```

### "Streamlit won't start"

**Solution:**
```bash
# Kill existing process
lsof -ti:8501 | xargs kill -9

# Restart
streamlit run app.py
```

### "Next.js build errors"

**Solution:**
```bash
cd /Users/duck/public/golf-data-app

# Clean build
rm -rf .next node_modules
npm install
npm run dev
```

---

## Cloud Deployment (Optional)

### Deploy Next.js App to Cloud Run

```bash
cd /Users/duck/public/golf-data-app

# Configure Docker for GCP
gcloud auth configure-docker

# Deploy
./deploy.sh
```

This will:
- Build Docker image
- Push to Google Container Registry
- Deploy to Cloud Run
- Provide public URL

**Cost**: ~$5-10/month for low usage

---

## Data Import Details

### What Gets Imported from Uneekor

When you paste a Uneekor URL and import:

**Shot Data (30+ fields):**
- Ball metrics: speed, launch angle, spin rates
- Club metrics: speed, path, face angle, attack angle
- Flight: carry, total, apex, flight time
- Impact: location (X/Y), Optix data, club lie
- Classification: shot type (straight/draw/fade/hook/slice)

**Media Files:**
- Impact images (face view)
- Swing videos (24 frames per shot)
- Saved to `./media/{session_id}/`

**Session Metadata:**
- Session date (actual practice date)
- Club used
- Session ID
- Shot ID

### Where Data is Stored

1. **SQLite** (`./data/golf_stats.db`):
   - Primary local database
   - 380 shots currently
   - Works offline

2. **Supabase** (cloud backup):
   - 555 shots
   - Accessible from anywhere
   - Includes image URLs

3. **BigQuery** (data warehouse):
   - 555 shots (synced from Supabase)
   - Used by AI coach
   - SQL analytics

---

## Quick Reference Commands

```bash
# Import new Uneekor data
cd "/Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My Drive/2025 Golf Season/GolfDataApp"
streamlit run app.py
# → Paste URL → Import

# Sync to BigQuery
python scripts/supabase_to_bigquery.py incremental

# View in Streamlit
# → Already open at http://localhost:8501

# View in Next.js
cd /Users/duck/public/golf-data-app
npm run dev
# → Open http://localhost:3000

# Get AI insights
# → Chat in either app

# Deploy to cloud
cd /Users/duck/public/golf-data-app
./deploy.sh
```

---

## Next Steps

1. **Import your latest practice session** using the Streamlit app
2. **Sync to BigQuery** for AI analysis
3. **Try both apps** to see which interface you prefer
4. **Deploy to Cloud Run** for mobile access (optional)

---

**Need Help?**
- Streamlit app issues → Check main project `CLAUDE.md`
- Next.js app issues → Check `/Users/duck/public/golf-data-app/README.md`
- Cloud deployment → Check deployment guides in both projects
