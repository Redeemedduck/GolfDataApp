# Golf Data Pipeline Setup Guide
## SQLite → Supabase → BigQuery → Vertex AI

This guide walks you through setting up the complete data pipeline for analyzing your golf shot data with Vertex AI.

---

## Prerequisites

- Python 3.8+
- Google Cloud account
- Supabase account
- Existing SQLite database with golf shot data

---

## Step 0: Local Environment & Uneekor Scraping

Before you can sync data to the cloud, you need a local environment to run the Streamlit dashboard and scrape data from Uneekor.

### 0.1 Clone the Repository & Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd GolfDataApp

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 0.2 Configure .env
Create a `.env` file in the root directory (use `.env.example` as a template):
```env
SUPABASE_URL="https://xxxxx.supabase.co"
SUPABASE_KEY="your-anon-key-here"
GCP_PROJECT_ID="your-project-id"
GCP_REGION="us-central1"
BQ_DATASET_ID="golf_data"
BQ_TABLE_ID="shots"
```

### 0.3 Run the Streamlit Dashboard
```bash
streamlit run app.py
```

### 0.4 Import Uneekor Data
1. Launch the **Uneekor View** software and locate your report.
2. Get the **Shareable URL** for the report.
3. In the Streamlit app sidebar, paste the URL and click **Run Import**.
4. The scraper will:
   - Request JSON data from the Uneekor API.
   - Convert metrics to Imperial (MPH, Yards).
   - Upload shot images to Supabase Storage.
   - Save shot metadata to the local SQLite database (`golf_stats.db`) and Supabase.
   - **Advanced Metrics**: Captured fields now include `optix_x`, `optix_y` (Impact location), `club_lie`, and `lie_angle`.

---

## Step 1: Install Dependencies

```bash
pip install supabase google-cloud-bigquery google-cloud-aiplatform pandas
```

---

## Step 2: Set Up Supabase

### 2.1 Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click "New Project"
3. Choose organization and fill in project details:
   - Name: `golf-data` (or your preference)
   - Database Password: (strong password)
   - Region: Choose closest to you
4. Wait for project creation (~2 minutes)

### 2.2 Get Supabase Credentials

1. In your project dashboard, go to **Settings** → **API**
2. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: Long string starting with `eyJ...`

### 2.3 Create Database Schema

1. In Supabase dashboard, click **SQL Editor**
2. Copy the entire contents of `supabase_schema.sql`
3. Paste into SQL Editor and click **Run**
4. Verify the `shots` table was created: **Database** → **Tables**

### 2.4 Set Environment Variables

```bash
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_KEY="your-anon-key-here"
```

For permanent setup, add to your `~/.bashrc` or `~/.zshrc`.

---

## Step 3: Migrate Data from SQLite to Supabase

### 3.1 Run Migration Script

```bash
python scripts/migrate_to_supabase.py
```

This will:
- Connect to your local `golf_stats.db`
- Upload all shots to Supabase in batches
- Verify the migration was successful

### 3.2 Verify Migration

```bash
python scripts/migrate_to_supabase.py verify
```

Or check in Supabase dashboard: **Database** → **Table Editor** → **shots**

---

## Step 4: Set Up Google Cloud Platform

### 4.1 Create GCP Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click project dropdown → **New Project**
3. Name: `golf-analysis` (or your preference)
4. Note your **Project ID** (e.g., `golf-analysis-123456`)

### 4.2 Enable Required APIs

In Cloud Console, enable these APIs:
- BigQuery API
- Vertex AI API

Or use gcloud CLI:
```bash
gcloud services enable bigquery.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

### 4.3 Set Up Authentication

**Option A: Service Account (Recommended for production)**

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. Name: `golf-data-pipeline`
4. Grant roles:
   - BigQuery Admin
   - Vertex AI User
5. Click **Create Key** → **JSON**
6. Save the JSON file securely (e.g., `~/gcp-credentials.json`)

Set environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/gcp-credentials.json"
```

**Option B: User Credentials (Easier for development)**

```bash
gcloud auth application-default login
```

### 4.4 Set GCP Environment Variables

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export BQ_DATASET_ID="golf_data"
export BQ_TABLE_ID="shots"
```

---

## Step 5: Create BigQuery Dataset and Table

### 5.1 Automatic Setup (Recommended)

The `supabase_to_bigquery.py` script will automatically create the dataset and table on first run.

### 5.2 Manual Setup (Optional)

Using `bq` CLI:
```bash
# Create dataset
bq mk --dataset --location=US ${GCP_PROJECT_ID}:golf_data

# Create table with schema
bq mk --table \
  ${GCP_PROJECT_ID}:golf_data.shots \
  bigquery_schema.json
```

---

## Step 6: Export Data from Supabase to BigQuery

### 6.1 Initial Full Sync

```bash
python scripts/supabase_to_bigquery.py full
```

This will:
- Fetch all shots from Supabase
- Create BigQuery dataset and table (if needed)
- Upload all data to BigQuery

### 6.2 Incremental Sync (for ongoing updates)

After initial sync, use incremental mode to sync only new shots:

```bash
python scripts/supabase_to_bigquery.py incremental
```

### 6.3 Verify Data in BigQuery

In BigQuery Console:
```sql
SELECT
  club,
  COUNT(*) as shot_count,
  AVG(carry) as avg_carry,
  AVG(smash) as avg_smash
FROM `your-project-id.golf_data.shots`
GROUP BY club
ORDER BY shot_count DESC
```

---

## Step 7: Set Up Vertex AI Analysis

### 7.1 Verify Vertex AI Access

```bash
gcloud ai models list --region=us-central1
```

### 7.2 Run Performance Analysis

Get statistics for all clubs:
```bash
python scripts/vertex_ai_analysis.py stats
```

Get statistics for specific club:
```bash
python scripts/vertex_ai_analysis.py stats "Driver"
```

### 7.3 Generate AI Insights with Gemini

Analyze all shots:
```bash
python scripts/vertex_ai_analysis.py analyze
```

Analyze specific club:
```bash
python scripts/vertex_ai_analysis.py analyze "7 Iron"
```

This will:
- Query your BigQuery data
- Generate a comprehensive analysis prompt
- Send to Vertex AI Gemini for insights
- Display actionable recommendations

### 7.4 Export Data for Custom ML Models

If you want to train custom models in Vertex AI:
```bash
python scripts/vertex_ai_analysis.py export
```

This creates `golf_data_for_training.csv` with cleaned data and derived features.

---

## Step 8: Automate the Pipeline

### 8.1 Set Up Automated Sync (Cron)

Add to your crontab (`crontab -e`):

```bash
# Sync new shots from Supabase to BigQuery every hour
0 * * * * cd /path/to/GolfDataApp && python scripts/supabase_to_bigquery.py incremental >> logs/sync.log 2>&1
```

### 8.2 Set Up Streamlit App to Use Supabase

Modify `app.py` to read from Supabase instead of SQLite (optional):

```python
from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Replace golf_db.get_session_data() with:
response = supabase.table("shots").select("*").execute()
shots = response.data
```

---

## Step 9: Using Vertex AI for Advanced Analysis

### 9.1 Gemini Analysis (Natural Language Insights)

The `scripts/vertex_ai_analysis.py` script uses Gemini to provide:
- Swing mechanics analysis
- Shot dispersion patterns
- Comparison vs PGA Tour averages
- Actionable improvement recommendations
- Correlation analysis (club path vs face angle)

### 9.2 Custom ML Models (Advanced)

For predictive modeling:

1. Export training data:
   ```bash
   python scripts/vertex_ai_analysis.py export
   ```

2. Upload to GCS:
   ```bash
   gsutil cp golf_data_for_training.csv gs://your-bucket/training-data/
   ```

3. Use Vertex AI AutoML or custom training jobs

### 9.3 BigQuery ML (Alternative)

You can also train models directly in BigQuery:

```sql
-- Example: Predict carry distance based on swing metrics
CREATE OR REPLACE MODEL `golf_data.carry_predictor`
OPTIONS(
  model_type='linear_reg',
  input_label_cols=['carry']
) AS
SELECT
  ball_speed,
  club_speed,
  launch_angle,
  back_spin,
  attack_angle,
  carry
FROM `golf_data.shots`
WHERE carry > 0 AND ball_speed > 0
```

---

## Troubleshooting

### Supabase Connection Issues

- Verify URL and key are correct
- Check if your IP is allowed in Supabase dashboard
- Ensure RLS policies allow your key to access data

### BigQuery Permission Errors

- Verify service account has BigQuery Admin role
- Check `GOOGLE_APPLICATION_CREDENTIALS` path
- Try `gcloud auth application-default login`

### Vertex AI Errors

- Ensure Vertex AI API is enabled
- Verify you're using a supported region
- Check quota limits in GCP Console

---

## Next Steps

- Set up real-time sync using Supabase webhooks
- Create custom Vertex AI models for shot prediction
- Build dashboards in Looker Studio connected to BigQuery
- Integrate AI insights back into Streamlit app

---

## Architecture Diagram

```
┌─────────────────┐
│  Uneekor API    │
│  (Shot Data)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  golf_scraper   │─────▶│  SQLite (local)  │
│  (Python)       │      │  golf_stats.db   │
└─────────────────┘      └────────┬─────────┘
                                  │
                                   │ scripts/migrate_to_supabase.py
                                   ▼
                          ┌─────────────────┐
                          │    Supabase     │
                          │   (PostgreSQL)  │
                          └────────┬────────┘
                                   │
                                   │ scripts/supabase_to_bigquery.py
                                   ▼
                          ┌─────────────────┐
                          │    BigQuery     │
                          │  (Data Warehouse)│
                          └────────┬────────┘
                                   │
                                   │ scripts/vertex_ai_analysis.py
                                  ▼
                         ┌─────────────────┐
                         │   Vertex AI     │
                         │  (Gemini / ML)  │
                         └─────────────────┘
                                  │
                                  ▼
                         📊 AI Insights & Predictions
```

---

## Environment Variables Summary

```bash
# Supabase
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_KEY="eyJhbG..."

# Google Cloud
export GCP_PROJECT_ID="golf-analysis-123456"
export GCP_REGION="us-central1"
export BQ_DATASET_ID="golf_data"
export BQ_TABLE_ID="shots"
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/gcp-credentials.json"
```

Save these to `~/.bashrc` or `~/.zshrc` for persistence.

---

## Cost Estimates

**Supabase:**
- Free tier: Up to 500MB database
- Pro: $25/month (8GB)

**Google Cloud:**
- BigQuery: First 1TB queries/month free
- Storage: $0.02/GB/month
- Vertex AI Gemini: ~$0.00025 per 1K characters
- Typical monthly cost: < $5 for personal use

---

## Step 10: MCP Database Control Plane (Advanced AI Integration)

The **MCP Toolbox for Databases** allows you to connect your databases (SQLite, BigQuery, etc.) directly to AI agents (like Claude or Antigravity) as a shared "Control Plane."

### 10.1 Global Installation
1.  **Download Binary**: Install the `toolbox` binary to a global location (e.g., `~/.mcp/database-toolbox/`).
2.  **Configuration**: Create a `tools.yaml` file to define your sources.
    ```yaml
    sources:
      local-sqlite:
        kind: sqlite
        database: /absolute/path/to/golf_stats.db
      google-bigquery:
        kind: bigquery
        project: your-project-id
    ```
3.  **Modular Power**: Drop individual YAML files into the `tools/` folder for multi-project management.

### 10.2 Features
- **Conversational Analytics**: Chat with your BigQuery data directly without SQL.
- **Autonomous Discovery**: AI agents can independently explore schemas using `list-tables` and `get-table-schema`.
- **Hybrid Support**: Manage local and cloud data from a single high-level interface.

---

## 🔧 Maintenance: Schema Updates
The architecture is designed to be **Self-Healing**. 
- **SQLite**: The `golf_db.py` script automatically adds missing columns to your local database on startup.
- **Cloud**: If you add new metrics, remember to update `supabase_schema.sql` and `bigquery_schema.json` accordingly.

---

## Architecture Diagram (Updated)
```
┌─────────────────┐
│  Uneekor API    │
│  (Advanced Optix)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  golf_scraper   │─────▶│  SQLite (local)  │
│  (Auto-Migrate) │      │  golf_stats.db   │
└─────────────────┘      └────────┬─────────┘
                                  │
                                   │ scripts/migrate_to_supabase.py
                                   ▼
                          ┌─────────────────┐
                          │    Supabase     │◀───┐
                          │   (PostgreSQL)  │    │
                          └────────┬────────┘    │
                                   │             │  MCP CONTROL PLANE
                                   │             │  (Shared AI Brain)
                                   ▼             │
                          ┌─────────────────┐    │
                          │    BigQuery     │◀───┘
                          │ (Warehouse)     │
                          └────────┬────────┘
                                   │
                                   │ scripts/vertex_ai_analysis.py
                                  ▼
                         ┌─────────────────┐
                         │   Vertex AI     │
                         │  (Gemini / ML)  │
                         └─────────────────┘
```

---

## Resources
- [MCP Toolbox Documentation](https://github.com/googleapis/genai-toolbox)
- [Supabase Documentation](https://supabase.com/docs)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
