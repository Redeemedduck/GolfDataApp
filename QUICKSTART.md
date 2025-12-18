# Quick Start: Supabase → BigQuery → Vertex AI

Since you already have Supabase set up, here's the streamlined process to get your golf data into BigQuery and start analyzing with Vertex AI.

---

## 0. Initial Data Capture (Streamlit)

Before you can sync data to BigQuery, you need to capture it from Uneekor using the local Streamlit dashboard.

1. **Setup Local Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

2. **Run Streamlit Server**:
   ```bash
   streamlit run app.py
   ```

3. **Scrape Uneekor Data**:
   - Open your browser to `http://localhost:8501`.
   - Paste your **Uneekor Report URL** in the sidebar.
   - Click **Run Import** to download shots and images to Supabase.

For a detailed setup guide including Supabase and GCP configuration, see [SETUP_GUIDE.md](file:///Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My%20Drive/2025%20Golf%20Season/GolfDataApp/SETUP_GUIDE.md).

---

## 1. Install Dependencies

bash
pip install supabase google-cloud-bigquery google-cloud-aiplatform pandas```
```

---

## 2. Set Up Google Cloud

### Create/Select Project
```bash
# Set your project
gcloud config set project valued-odyssey-474423-g1

# Enable required APIs
gcloud services enable bigquery.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

### Authenticate
```bash
gcloud auth application-default login
```

---

## 3. Configure Environment Variables

Create a `.env` file or export these:

```bash
# Your existing Supabase project
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_KEY="your-key-here"

# Your GCP project
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export BQ_DATASET_ID="golf_data"
export BQ_TABLE_ID="shots"
```

---

## 4. Export to BigQuery

### First-time full sync:
```bash
python scripts/supabase_to_bigquery.py full
```

This will automatically:
- Create the BigQuery dataset
- Create the table with proper schema
- Export all your Supabase data

### Ongoing incremental updates:
```bash
python scripts/supabase_to_bigquery.py incremental
```

---

## 5. Analyze with Vertex AI

### Get performance statistics:
```bash
python scripts/vertex_ai_analysis.py stats
python scripts/vertex_ai_analysis.py stats "Driver"
```

### Get AI-powered insights:
```bash
python scripts/vertex_ai_analysis.py analyze
python scripts/vertex_ai_analysis.py analyze "7 Iron"
```

### Export for ML training:
```bash
python scripts/vertex_ai_analysis.py export
```

---

## 6. Query Your Data

In BigQuery Console or CLI:

```sql
-- Summary by club
SELECT
  club,
  COUNT(*) as shots,
  AVG(carry) as avg_carry,
  AVG(smash) as avg_smash,
  AVG(ball_speed) as avg_ball_speed
FROM `your-project-id.golf_data.shots`
GROUP BY club
ORDER BY avg_carry DESC
```

---

## Automate Syncs

Add to crontab for hourly updates:
```bash
0 * * * * cd /path/to/GolfDataApp && python scripts/supabase_to_bigquery.py incremental
```

---

## Files You Need

- ✅ `supabase_to_bigquery.py` - Export pipeline
- ✅ `vertex_ai_analysis.py` - AI analysis tools
- ✅ `bigquery_schema.json` - Table schema (auto-created)

You can ignore:
- ❌ `migrate_to_supabase.py` - You already have Supabase
-   ❌ `migrate_to_supabase.py` - You already have Supabase
-   ❌ `supabase_schema.sql` - Your schema is already set up

---

## What Each Script Does

**scripts/supabase_to_bigquery.py**
-   Fetches data from your existing Supabase project
-   Creates BigQuery infrastructure automatically
-   Syncs data (full or incremental)
-   Handles schema mapping

**scripts/vertex_ai_analysis.py**
-   Connects to BigQuery
-   Generates comprehensive analysis prompts
-   Uses Gemini for AI insights
-   Exports data for ML training

---

## Verification

After running the sync, verify in BigQuery:
```bash
bq query --use_legacy_sql=false "SELECT COUNT(*) FROM \`${GCP_PROJECT_ID}.golf_data.shots\`"
```

---

## Costs

Typical monthly cost for personal use: **< $5**
- BigQuery: First 1TB queries free
- Storage: ~$0.02/GB/month
- Vertex AI Gemini: ~$0.00025 per 1K characters
