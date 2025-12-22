# Quick Start Guide

## How to Add New Data from Uneekor

### Step 1: Go to Uneekor Portal
1. Go to https://my.uneekor.com
2. Log in to your account
3. Find your practice session
4. Open the session report
5. **Copy the entire URL from your browser** (looks like: `https://my.uneekor.com/report?id=12345&key=abc123`)

### Step 2: Run Streamlit App
```bash
cd "/Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My Drive/2025 Golf Season/GolfDataApp"

streamlit run app.py
```

### Step 3: Import Data
1. Browser will open to http://localhost:8501
2. Look at the sidebar on the left
3. Paste your Uneekor URL in the text box
4. Click "Import Data from Uneekor"
5. Wait 10-30 seconds (downloads shots + images + videos)
6. You'll see "✅ Successfully imported X shots"

### Step 4: Sync to BigQuery (for AI Chat)
```bash
# From the same directory
python scripts/supabase_to_bigquery.py incremental
```

Done! Your data is now in:
- SQLite (local database)
- Supabase (cloud backup)
- BigQuery (for AI analysis)

---

## How to Run Everything

### Option 1: Just Analyzing Existing Data

**Run Next.js Web App:**
```bash
cd /Users/duck/public/golf-data-app
npm run dev
open http://localhost:3000
```

This gives you:
- Clean professional UI
- AI chat with your BigQuery data
- Performance dashboards
- Club statistics

### Option 2: Adding New Data + Analysis

**Step 1 - Run Streamlit (for data import):**
```bash
cd "/Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My Drive/2025 Golf Season/GolfDataApp"
streamlit run app.py
```
- Opens at http://localhost:8501
- Import new Uneekor data here

**Step 2 - Sync to BigQuery:**
```bash
python scripts/supabase_to_bigquery.py incremental
```

**Step 3 - Run Next.js (for analysis):**
```bash
cd /Users/duck/public/golf-data-app
npm run dev
open http://localhost:3000
```

**Both apps can run at the same time!**
- Streamlit: http://localhost:8501 (data import)
- Next.js: http://localhost:3000 (analysis)

---

## Daily Workflow

### After Practice Session:

```bash
# 1. Import new data
cd "/Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My Drive/2025 Golf Season/GolfDataApp"
streamlit run app.py
# → Paste Uneekor URL in sidebar
# → Click Import

# 2. Sync to BigQuery
python scripts/supabase_to_bigquery.py incremental

# 3. Get AI insights
cd /Users/duck/public/golf-data-app
npm run dev
open http://localhost:3000
# → Chat with AI about your session
```

### Just Checking Stats:

```bash
cd /Users/duck/public/golf-data-app
npm run dev
open http://localhost:3000
# → View dashboards
# → Ask AI questions
```

---

## Environment Setup (First Time Only)

### 1. Get Gemini API Key

The Next.js app needs a Gemini API key to work:

```bash
# Visit https://ai.google.dev/
# Click "Get API Key"
# Copy your key

# Create .env.local file
cd /Users/duck/public/golf-data-app
nano .env.local
```

Add this content:
```bash
GCP_PROJECT_ID=valued-odyssey-474423-g1
GCP_REGION=us-central1
BQ_DATASET_ID=golf_data
BQ_TABLE_ID=shots
GEMINI_API_KEY=your-api-key-here
```

Save and exit (Ctrl+X, Y, Enter)

### 2. Authenticate Google Cloud

For BigQuery access:
```bash
gcloud auth application-default login
```

That's it! Now the Next.js app can access your golf data.

---

## What Each App Does

### Streamlit App
**Location**: `~/GoogleDrive/.../GolfDataApp/`
**URL**: http://localhost:8501
**Use for**:
- ✅ Importing new Uneekor data
- ✅ Viewing shot videos and images
- ✅ Detailed shot-by-shot analysis
- ✅ Multimodal AI coach with charts

### Next.js App
**Location**: `/Users/duck/public/golf-data-app`
**URL**: http://localhost:3000
**Use for**:
- ✅ Clean conversational AI chat
- ✅ Performance dashboards
- ✅ Trend analysis
- ✅ Cloud deployment (when ready)

---

## Troubleshooting

### "Can't connect to BigQuery"
```bash
gcloud auth application-default login
```

### "Gemini API error"
Check your `.env.local` file has the API key:
```bash
cd /Users/duck/public/golf-data-app
cat .env.local | grep GEMINI
```

### "Port already in use"
```bash
# Kill Streamlit
lsof -ti:8501 | xargs kill -9

# Kill Next.js
lsof -ti:3000 | xargs kill -9
```

### "Can't find Streamlit app"
Make sure you're in the right directory:
```bash
cd "/Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My Drive/2025 Golf Season/GolfDataApp"
ls app.py  # Should see the file
```

---

## Summary

**To add new Uneekor data:**
1. Run Streamlit: `streamlit run app.py`
2. Paste Uneekor URL
3. Click Import
4. Sync: `python scripts/supabase_to_bigquery.py incremental`

**To analyze data:**
1. Run Next.js: `cd /Users/duck/public/golf-data-app && npm run dev`
2. Open http://localhost:3000
3. Chat with AI

**Both apps work together** - use Streamlit for data entry, Next.js for analysis!
