# Data Sync Architecture & Why BigQuery Doesn't Auto-Update

## Current Status

### Data Distribution
- **Local SQLite**: 380 shots (local-first, includes new schema with session_date, video_frames columns)
- **Supabase (Cloud)**: 555 shots (cloud backup, missing new columns)
- **BigQuery (Warehouse)**: 555 shots (analytics warehouse, schema updated but data doesn't have new columns yet)

### Key Finding
**The new columns (session_date, video_frames) exist in local SQLite schema but have NO DATA** because all 380 shots were imported before we added those features. You need to re-import sessions to get those new fields populated.

## Why BigQuery Doesn't Auto-Update

### Architecture Design (By Intent)

```
┌─────────────────┐
│  Uneekor API    │ (External data source)
└────────┬────────┘
         │ Manual import via Streamlit UI
         ▼
┌─────────────────┐
│ LOCAL SQLite    │ ← PRIMARY DATABASE (local-first)
│  golf_stats.db  │   - Offline access
│                 │   - Fast queries
└────────┬────────┘   - No auth needed
         │
         │ Auto-sync during import (if Supabase configured)
         ▼
┌─────────────────┐
│   SUPABASE      │ ← CLOUD BACKUP
│   PostgreSQL    │   - Multi-device access
│                 │   - Image storage (Supabase Storage bucket)
└────────┬────────┘   - Optional (works without it)
         │
         │ MANUAL sync only (scripts/supabase_to_bigquery.py)
         ▼
┌─────────────────┐
│   BIGQUERY      │ ← DATA WAREHOUSE
│  golf_data.shots│   - Historical analysis
│                 │   - Complex SQL queries
└─────────────────┘   - Gemini AI analysis
```

### Why Manual Sync?

**1. BigQuery is a Data Warehouse, Not a Realtime Database**
- Designed for batch processing and analytics
- Not optimized for real-time updates
- Each write operation has cost and latency

**2. Cost Optimization**
- BigQuery charges per query and storage
- Real-time sync would increase costs significantly
- Batch syncing is more economical

**3. Flexibility**
- You control when data syncs (after practice, daily, weekly)
- Can choose full sync (replace all) or incremental (add new only)
- Gives you time to clean/edit data locally before syncing

**4. Local-First Philosophy**
- App works offline without cloud dependencies
- Supabase is optional backup
- BigQuery is optional analytics layer

## How to Sync Data

### Option 1: Manual Sync (Current Approach)

```bash
# Full sync (replace all data - recommended for schema changes)
python scripts/supabase_to_bigquery.py full

# Incremental sync (add only new shots since last sync)
python scripts/supabase_to_bigquery.py incremental
```

### Option 2: Automated Scheduled Sync

Set up a cron job (Mac/Linux) or Task Scheduler (Windows):

```bash
# Run the setup wizard
./setup_cron.sh

# Or manually add to crontab
crontab -e

# Add this line for daily sync at 11 PM:
0 23 * * * cd /path/to/GolfDataApp && python scripts/auto_sync.py
```

### Option 3: Post-Session Workflow

```bash
# Interactive post-session analysis (prompts for sync)
python scripts/post_session.py
```

## The Schema Mismatch Issue

### Current Problem

1. **Local SQLite**: Has session_date, video_frames columns (schema only, no data)
2. **Supabase**: Missing those columns entirely
3. **BigQuery**: Has those columns (we just added them) but no data

### Why It Happened

1. We added new features (session_date, video_frames) to the code
2. SQLite auto-migrated schema (added columns to existing table)
3. But existing 380 shots were imported BEFORE those features existed
4. Supabase schema wasn't updated (requires database migration)
5. BigQuery schema we manually updated, but source data (Supabase) doesn't have the values

### How to Fix

**Step 1: Update Supabase Schema**
Add the missing columns to Supabase database:

```sql
-- Run in Supabase SQL Editor
ALTER TABLE shots ADD COLUMN session_date TEXT;
ALTER TABLE shots ADD COLUMN video_frames TEXT;
```

**Step 2: Re-Import Practice Sessions**
- Go to Streamlit app
- Paste Uneekor URL for a session you want video data for
- Click "Run Scraper"
- New imports will include session_date and video_frames

**Step 3: Sync to BigQuery**
```bash
python scripts/supabase_to_bigquery.py full
```

## Docker Container Authentication Issue

### The Problem

The Docker container can't access Google Cloud (BigQuery, Gemini API) because:
- Container is isolated from host machine
- Your gcloud credentials are on the host at `~/.config/gcloud/`
- Container doesn't have access to those credentials

### Solution Options

#### Option 1: Mount Credentials (Simplest for Development)

Update `docker-compose.yml`:

```yaml
services:
  golf-app:
    volumes:
      - ./data:/app/data
      - ./media:/app/media
      - ./logs:/app/logs
      - ~/.config/gcloud:/root/.config/gcloud:ro  # ADD THIS LINE
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json  # ADD THIS
```

Then rebuild:
```bash
docker-compose down
docker-compose up -d
```

#### Option 2: Service Account (Better for Production)

1. **Create Service Account**:
   ```bash
   gcloud iam service-accounts create golf-data-app \
       --display-name="Golf Data App"
   ```

2. **Grant Permissions**:
   ```bash
   gcloud projects add-iam-policy-binding valued-odyssey-474423-g1 \
       --member="serviceAccount:golf-data-app@valued-odyssey-474423-g1.iam.gserviceaccount.com" \
       --role="roles/bigquery.user"
   ```

3. **Download Key**:
   ```bash
   gcloud iam service-accounts keys create service-account-key.json \
       --iam-account=golf-data-app@valued-odyssey-474423-g1.iam.gserviceaccount.com
   ```

4. **Update docker-compose.yml**:
   ```yaml
   services:
     golf-app:
       volumes:
         - ./service-account-key.json:/app/service-account-key.json:ro
       environment:
         - GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json
   ```

## Recommended Workflow

### After Each Practice Session

1. **Import Data** (Streamlit UI):
   - Paste Uneekor URL
   - Data goes to: Local SQLite → Auto-syncs to Supabase (if configured)

2. **Review & Clean** (Streamlit UI):
   - Use "Manage Data" tab to rename clubs, delete bad shots
   - Changes apply to both local SQLite and Supabase

3. **Sync to BigQuery** (Terminal - Optional):
   ```bash
   python scripts/supabase_to_bigquery.py incremental
   ```

4. **AI Analysis** (Terminal - Optional):
   ```bash
   python scripts/gemini_analysis.py summary
   python scripts/gemini_analysis.py analyze Driver
   ```

### Weekly/Monthly

```bash
# Full sync to ensure consistency
python scripts/supabase_to_bigquery.py full

# Comprehensive analysis
python scripts/post_session.py
```

## Summary

**Q: Why doesn't BigQuery auto-update?**
A: By design - BigQuery is a data warehouse for batch analytics, not a real-time database. Manual/scheduled syncing gives you control, reduces costs, and maintains local-first architecture.

**Q: How often should I sync?**
A: It depends on your needs:
- Daily: If you use BigQuery for AI analysis frequently
- Weekly: If you just want historical trends
- Manual: After each session if you want immediate insights

**Q: Can I make it automatic?**
A: Yes! Use `setup_cron.sh` to schedule automatic daily syncs, or run `scripts/auto_sync.py` from any scheduler.

**Q: What about the Docker authentication?**
A: Use Option 1 (mount credentials) for development. We'll implement that next.
