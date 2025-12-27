# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Recent Updates (December 2024)

### Latest Changes

**Data Expansion Complete (December 27, 2024)**
- ✅ **Expanded Schema** - 32 → 42 fields with 10 new high-value metrics
- ✅ **Ball Compression Tracking** - Capture ball type (SOFT/MEDIUM/FIRM) for performance analysis
- ✅ **Launch Monitor Identification** - Track sensor model (EYEXO, QED) for accuracy comparison
- ✅ **Impact Position Data** - Club face strike location (impact_x, impact_y in mm)
- ✅ **Low Point Calculation** - Estimated swing arc bottom from attack angle
- ✅ **Data Cleaning** - Convert invalid 99999 markers to null for cleaner analytics
- ✅ **Service Layer Updated** - ImportService with data cleaning + low point calculation
- ✅ **Repository Layer Updated** - ShotRepository with expanded schema migration
- ✅ **BigQuery Synced** - 606 shots with all expanded fields in data warehouse
- ✅ **Impact Analysis Guide** - Comprehensive documentation for strike pattern analysis

**Phase 3: Professional Web App (December 22, 2024)**
- ✅ **Next.js Web Application** - Modern React/Next.js app with professional UI at `/Users/duck/public/golf-data-app`
- ✅ **Gemini AI Integration** - Real-time AI coach with BigQuery data integration
- ✅ **Performance Dashboards** - Interactive charts with Recharts showing club stats
- ✅ **Conversation Memory** - Multi-turn dialogues with context retention
- ✅ **Cloud Run Ready** - Dockerized and ready for deployment
- ✅ **Dual Applications** - Streamlit (data entry) + Next.js (analysis) working together

**Phase 2: Cloud Automation (December 22, 2024)**
- ✅ **Phase 2 Cloud Automation Deployed** - All Cloud Functions operational with secure authentication
- ✅ **Cloud Functions Live** - auto-sync (HTTP + Pub/Sub) and daily-insights (HTTP + Scheduled) deployed
- ✅ **Cloud Scheduler Active** - Daily AI insights at 8:00 AM UTC

**Phase 1: Core Features**
- ✅ **Gemini 2.0 Flash Integration** - Replaced Claude API with Google Gemini for AI Coach
- ✅ **Session Date Tracking** - Extract actual practice dates from Uneekor API
- ✅ **Video Frame Support** - Download and display swing video sequences (24 frames per shot)
- ✅ **BigQuery Sync** - 555 shots synced with updated schema
- ✅ **Docker Authentication** - Google Cloud credentials mounted for BigQuery + Gemini access
- ✅ **Multimodal AI Coach** - Code execution, Plotly charts, image/video awareness

### Breaking Changes
- **Database Schema**: Expanded from 32 → 42 fields (10 new columns added December 2024)
- **Data Cleaning**: 99999 invalid markers now converted to 0.0/null (affects legacy data)
- **Cloud Functions**: Now require authentication (use `gcloud auth print-identity-token`)
- **Dependencies**: Added pandas and db-dtypes to daily_insights requirements
- **AI Coach Model**: Changed from Claude to Gemini (`gemini-2.0-flash-exp`)
- **Docker Volumes**: Added gcloud credentials mount at `/app/.gcloud`

---

## Project Overview

This is a golf data analysis platform with a **local-first hybrid architecture** and **dual application design**:

### Applications

1. **Streamlit App** (this directory - `app.py`):
   - **Purpose**: Data import and detailed exploration
   - **Port**: http://localhost:8501
   - **Features**: Import from Uneekor API, SQLite storage, media viewer, multimodal AI coach with code execution
   - **Best for**: Adding new data, viewing shot videos/images, detailed analysis

2. **Next.js Web App** (`/Users/duck/public/golf-data-app`):
   - **Purpose**: Modern conversational AI analysis
   - **Port**: http://localhost:3000
   - **Features**: Professional UI, BigQuery integration, Gemini AI chat, performance dashboards
   - **Best for**: Daily insights, trend analysis, cloud deployment
   - **Status**: ✅ Built and ready to deploy to Cloud Run

### Data Flow

1. **Data Import**: Uneekor API → Streamlit app → SQLite (local-first) + Supabase (cloud backup)
2. **Cloud Sync**: Supabase → BigQuery (data warehouse via scripts/supabase_to_bigquery.py)
3. **AI Analysis**:
   - Streamlit: SQLite/Supabase → Gemini 2.0 (code execution, charts)
   - Next.js: BigQuery → Gemini 1.5 (conversational insights)
4. **Automation**: Cloud Functions (auto-sync, daily insights) + Cloud Scheduler
5. **MCP Control Plane**: Direct database access (SQLite + BigQuery) via MCP Database Toolbox

The platform is designed for high-altitude golf analysis (Denver) and captures 30+ shot metrics including ball speed, spin rates, launch angles, impact location (Optix data), club lie angles, and swing videos.

---

## Development Commands

### Running the Application

**Docker (Recommended):**
```bash
# Quick start
./docker-quickstart.sh

# Or manually
docker-compose up -d
open http://localhost:8501

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

**Local (Non-Docker):**
```bash
streamlit run app.py
```

### Installing Dependencies

**Docker (Recommended):**
Dependencies are automatically installed in the container. No manual installation needed.

**Local:**
```bash
pip install -r requirements.txt
```

### Database Locations

- **Local**: SQLite database at `./data/golf_stats.db` (606 shots with expanded schema)
- **Cloud**: Firestore `valued-odyssey-474423-g1/shots` (606 shots, migrated from Supabase)
- **Data Warehouse**: BigQuery `valued-odyssey-474423-g1.golf_data.shots` (606 shots, 42 fields)
- **Media Storage**: Supabase Storage bucket "shot-images" (impact images, swing videos)
- **Media files**: `./media/` directory (Docker volume mounted)
- **Logs**: `./logs/` directory (Docker volume mounted)

### Cloud Pipeline Commands

**Local Scripts:**
```bash
# Sync Supabase → BigQuery
python scripts/supabase_to_bigquery.py full          # Full sync (replace all)
python scripts/supabase_to_bigquery.py incremental   # Sync only new shots

# AI Analysis with Gemini
python scripts/gemini_analysis.py summary            # Show club performance summary
python scripts/gemini_analysis.py analyze Driver     # AI insights for specific club
python scripts/gemini_analysis.py analyze            # Analyze all clubs

# Automation
python scripts/post_session.py                       # Interactive post-session analysis
python scripts/auto_sync.py                          # Background sync (for cron)
python scripts/auto_sync.py --analyze                # Background sync + AI analysis

# Testing
python legacy/test_connection.py                     # Test all connections
```

**Cloud Functions (Phase 2 - Deployed):**
```bash
# Deploy all functions (secure mode - requires authentication)
cd cloud_functions
./deploy_secure.sh

# Test auto-sync function
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://us-central1-valued-odyssey-474423-g1.cloudfunctions.net/auto-sync-http

# Test daily insights function
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://us-central1-valued-odyssey-474423-g1.cloudfunctions.net/daily-insights-http

# View function logs
gcloud functions logs read auto-sync-http --region=us-central1 --limit=50
gcloud functions logs read daily-insights-http --region=us-central1 --limit=50

# View scheduler jobs
gcloud scheduler jobs list --location=us-central1
gcloud scheduler jobs describe golf-daily-insights --location=us-central1

# Manually trigger scheduled job
gcloud scheduler jobs run golf-daily-insights --location=us-central1
```

---

## Architecture

### Current Architecture (Local-First Hybrid)

```
┌─────────────────┐
│  Uneekor API    │ (External data source)
└────────┬────────┘
         │ Manual import via Streamlit UI
         ▼
┌─────────────────┐
│ LOCAL SQLite    │ ← PRIMARY DATABASE (local-first)
│  golf_stats.db  │   - 380 shots
│                 │   - Offline access, fast queries
└────────┬────────┘   - No auth needed
         │
         │ Auto-sync during import (if Supabase configured)
         ▼
┌─────────────────┐
│   SUPABASE      │ ← CLOUD BACKUP
│   PostgreSQL    │   - 555 shots
│   + Storage     │   - Multi-device access
└────────┬────────┘   - Image/video storage
         │
         │ MANUAL sync (scripts/supabase_to_bigquery.py)
         ▼
┌─────────────────┐
│   BIGQUERY      │ ← DATA WAREHOUSE
│  golf_data.shots│   - 606 shots (42 columns)
│                 │   - Historical analysis
│                 │   - Complex SQL queries
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Gemini API     │ ← AI ANALYSIS
│  (Code Exec)    │   - Full CSV data access
│                 │   - BigQuery historical data
│                 │   - Plotly visualizations
└─────────────────┘   - Image/video awareness
```

### Local Application (Four-Module Structure)

**1. app.py** (Streamlit UI Layer)
   - Main entry point and user interface
   - **Tabs**:
     - **Import Data**: URL input + scraper trigger
     - **Shot Viewer**: Interactive table, metrics, images, video player
     - **Manage Data**: Rename clubs, delete shots/sessions
     - **AI Coach**: Conversational AI with code execution + BigQuery access
   - **Recent Features**:
     - Session dates show actual practice date (not import date)
     - Video frame scrubber (slider to view swing sequences)
     - AI Coach with full data access (not just summaries)
     - Plotly chart generation
     - Historical data toggle (BigQuery integration)

**2. golf_scraper.py** (API Data Fetcher)
   - **API-Based**: Uses Uneekor's REST API (fast, reliable)
   - API endpoint: `https://api-v2.golfsvc.com/v2/oldmyuneekor/report/{report_id}/{key}`
   - **Unit Conversions**: Metric → Imperial (m/s → mph, meters → yards)
   - **Smash Factor**: Calculated locally (ball_speed / club_speed)
   - **Video Frames**: Downloads swing sequences with configurable strategy:
     - `none`: First frame only (minimal storage)
     - `keyframes`: 5 key frames (0, 6, 12, 18, 23) - DEFAULT
     - `half`: Every other frame (12 frames)
     - `full`: All 24 frames (maximum detail)
   - **Image Upload**: Uploads to Supabase Storage bucket "shot-images"
   - **Session Dates**: Extracts `client_created_date` (actual practice date)

**3. golf_db.py** (Database Layer - Hybrid Local/Cloud)
   - **Local-First**: SQLite as primary database for offline access
   - **Dual Sync**: Automatically manages SQLite + Supabase (when configured)
   - **Self-Healing Schema**: Auto-migrates new columns on startup
   - **Expanded Schema** (42 columns):
     - Identifiers: shot_id (PK), session_id, date_added, session_date
     - Basic: club, carry, total, smash
     - Speed: ball_speed, club_speed
     - Spin: side_spin, back_spin
     - Angles: launch_angle, side_angle, club_path, face_angle, dynamic_loft, attack_angle, descent_angle
     - Impact: impact_x, impact_y, optix_x, optix_y
     - Club Geometry: club_lie, lie_angle
     - Flight: apex, flight_time, side_distance
     - Classification: shot_type
     - Media: impact_img, swing_img, video_frames (comma-separated URLs)
     - **NEW (Dec 2024)**: sensor_name, client_shot_id, server_timestamp, is_deleted, ball_name, ball_type, club_name_std, club_type, client_session_id, low_point
   - **Data Cleaning**: Converts 99999 invalid markers to 0.0/null
   - **Low Point Calculation**: `low_point = -(attack_angle / 2.0)` inches
   - **Idempotent**: Uses upsert to prevent duplicates

**4. scripts/** (Cloud Pipeline & Automation)
   - `supabase_to_bigquery.py`: Manual sync (Supabase → BigQuery)
   - `gemini_analysis.py`: AI analysis via Gemini API
   - `auto_sync.py`: Scheduled sync (cron/Task Scheduler)
   - `post_session.py`: Interactive post-session workflow

---

## Data Flow

### Import Flow (Uneekor → Local → Cloud)

```
1. User pastes Uneekor URL in Streamlit
2. golf_scraper.extract_url_params() → report_id, key
3. golf_scraper.run_scraper() → HTTP GET to Uneekor API
4. For each shot:
   - Convert units (metric → imperial)
   - Calculate smash factor
   - Extract session_date (client_created_date)
   - Download video frames (keyframes strategy)
   - Upload images/videos to Supabase Storage
5. golf_db.save_shot() → SQLite (local-first)
6. golf_db.save_shot_to_supabase() → Supabase (cloud backup, if configured)
7. app.py → Display in UI with video scrubber
```

### Sync Flow (Supabase → BigQuery)

```
1. Manual: python scripts/supabase_to_bigquery.py full
2. Fetch all shots from Supabase (paginated, 1000/page)
3. Transform to BigQuery schema
4. WRITE_TRUNCATE or WRITE_APPEND
5. BigQuery ready for SQL + AI analysis
```

### AI Analysis Flow (BigQuery → Gemini)

```
1. User asks question in AI Coach tab
2. Optional: Fetch historical data from BigQuery (500 shots)
3. Convert to CSV format (efficient token usage)
4. Send to Gemini API with:
   - Full CSV data (not summaries)
   - Code execution enabled
   - System prompt with capabilities
   - Image/video URL awareness
5. Gemini executes Python code to analyze
6. Returns insights + visualizations (Plotly)
```

---

## AI Coach Features (Gemini 3 Flash)

### Capabilities

✅ **Full Data Access**: Entire CSV (all columns, all shots) - no more guessing
✅ **Code Execution**: Writes and runs Python to analyze data
✅ **Plotly Charts**: Creates interactive visualizations
✅ **BigQuery Access**: Optional toggle for 500 historical shots
✅ **Image Awareness**: Knows which shots have impact/swing images
✅ **Video Awareness**: Knows which shots have swing sequences
✅ **Multimodal Ready**: Can reference specific frame URLs

### Model Configuration

- **Model**: `gemini-2.0-flash-exp` (latest, fastest)
- **Tools**: `code_execution` enabled
- **Temperature**: 0.7 (balanced creativity)
- **Context**: Full session CSV + optional BigQuery historical data

### Example Questions

**Data Analysis:**
- "What's my average carry distance by club?"
- "Show me shots where club path was more than 3° out-to-in"
- "Calculate standard deviation of my Driver shots"

**Visualizations:**
- "Create a scatter plot of launch angle vs carry distance"
- "Show me a dispersion chart for my 7-iron"
- "Plot club speed vs smash factor with trend line"

**Coaching:**
- "What's my biggest weakness based on the data?"
- "Compare my Driver stats to PGA Tour averages"
- "Which club has the most consistent dispersion?"

**Historical:**
- "How has my Driver carry improved over time?" (requires BigQuery toggle)
- "Compare this session to my average from last month"

### System Prompt Structure

```python
system_instruction = f"""You are an expert golf coach with 20+ years of experience.

**IMPORTANT: You have Python code execution capabilities AND data visualization tools.**

Context: Practicing at Denver altitude (5,280 ft) - 10-15% more carry than sea level.

**Current Session Data ({len(df)} shots):**
```csv
{csv_data}  # Full CSV with all 42 columns
```

**Available Media:**
- Impact Images: {count} shots
- Swing Images: {count} shots
- Video Frames: {count} shots with complete sequences
- URLs in 'impact_img', 'swing_img', 'video_frames' columns

**Your capabilities:**
1. Data Analysis: Write Python code to calculate statistics, find patterns
2. Visualization: Create Plotly charts (import plotly.graph_objects as go)
3. Image Analysis: Reference specific image URLs from data
4. Video Analysis: Access swing sequences via video_frames column
5. Specific Insights: Reference actual shot numbers
6. Show Your Work: Display code results and visualizations

**When asked a question:**
1. Write Python code to analyze the data
2. Execute the code
3. Interpret results
4. Provide coaching insights
5. Create visualizations if helpful
"""
```

---

## Video Frame Implementation

### Discovery

Uneekor API provides swing videos as **24 individual JPG frames**:
- 1 `ballimpact` image
- 24 `topview00` through `topview23` frames (complete swing sequence)

### Storage Strategies

| Strategy | Frames | Storage/Shot | 380 Shots Total |
|----------|--------|--------------|-----------------|
| **none** | 1 | ~400KB | ~152MB |
| **keyframes** (DEFAULT) | 5 | ~1.2MB | ~456MB |
| **half** | 12 | ~2.5MB | ~950MB |
| **full** | 24 | ~5MB | ~1.9GB |

**Recommendation**: `keyframes` provides best balance (3x storage for key swing moments)

### Video Playback UI

**Location**: Shot Viewer tab → Click shot → Scroll to "📹 Swing Video Frames"

**Features**:
- **Slider**: Scrub through frames manually
- **Frame counter**: "Frame 5/5"
- **Full-width display**: Each frame at maximum size
- **Play button**: Placeholder for future auto-play

### Implementation Files

- `golf_scraper.py:155-257` - Video download logic
- `golf_db.py:89, 133` - video_frames column
- `app.py:298-331` - Video playback UI
- `app.py:476-535` - AI Coach video awareness

---

## BigQuery Sync Architecture

### Why Manual Sync?

BigQuery is a **data warehouse**, not a real-time database:
- ✅ Designed for batch analytics (not real-time updates)
- ✅ Cost optimization (batch vs per-record writes)
- ✅ Flexibility (sync on your schedule)
- ✅ Local-first philosophy (app works offline)

### Current Data State

- **Local SQLite**: 380 shots (includes new schema, but fields empty - imported before features added)
- **Supabase**: 555 shots (missing session_date, video_frames columns)
- **BigQuery**: 555 shots (schema updated, but data doesn't have new columns yet)

### How to Fix Schema Mismatch

**Step 1**: Add columns to Supabase
```sql
-- Run in Supabase SQL Editor
ALTER TABLE shots ADD COLUMN session_date TEXT;
ALTER TABLE shots ADD COLUMN video_frames TEXT;
```

**Step 2**: Re-import sessions (to populate new fields)
```
1. Go to Streamlit app
2. Paste Uneekor URL
3. New imports will include session_date and video_frames
```

**Step 3**: Sync to BigQuery
```bash
python scripts/supabase_to_bigquery.py full
```

### Sync Options

**Manual (Current)**:
```bash
python scripts/supabase_to_bigquery.py full          # Replace all data
python scripts/supabase_to_bigquery.py incremental   # Add new only
```

**Automated (Optional)**:
```bash
./setup_cron.sh  # Interactive wizard

# Or add to crontab:
0 23 * * * cd /path/to/GolfDataApp && python scripts/auto_sync.py
```

---

## Docker Authentication (Google Cloud)

### Problem Solved

Docker container now has access to:
- ✅ **BigQuery** (555 shots accessible)
- ✅ **Gemini API** (AI Coach fully functional)

### Solution Implemented

**docker-compose.yml**:
```yaml
environment:
  - GOOGLE_APPLICATION_CREDENTIALS=/app/.gcloud/application_default_credentials.json

volumes:
  - ~/.config/gcloud:/app/.gcloud:ro  # Read-only mount
```

**How It Works**:
1. Host machine has gcloud credentials at `~/.config/gcloud/`
2. Volume mount makes them available in container
3. Mounted to `/app/.gcloud` (accessible by golfuser, not root)
4. Environment variable tells Google libraries where to find them

### Testing

```bash
# Test BigQuery
docker exec golf-data-app python -c "
from google.cloud import bigquery
client = bigquery.Client(project='valued-odyssey-474423-g1')
print('Shots:', client.query('SELECT COUNT(*) FROM \`valued-odyssey-474423-g1.golf_data.shots\`').to_dataframe())
"

# Test Gemini
docker exec golf-data-app python -c "
from google import genai
import os
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
print(client.models.generate_content(model='gemini-2.0-flash-exp', contents='Hello').text)
"
```

### Troubleshooting

**If credentials expire**:
```bash
gcloud auth application-default login
docker-compose restart
```

---

## Architecture Upgrade Plan

### Current Limitations

⚠️ **Single-user** (no collaboration)
⚠️ **Web-only** (no mobile app)
⚠️ **Manual syncing** (not automatic)
⚠️ **Streamlit can be slow** with complex interactions
⚠️ **AI requires page reloads** (no conversational memory)

### Recommended Upgrades (Phased Approach)

### Phase 1: **Vertex AI Agent Builder** (2 days - BIGGEST AI UPGRADE)

**What Changes:**
```
Current: Gemini API → Direct function calls → One-shot responses

Upgraded: Vertex AI Agent Builder → Multi-turn conversations → Persistent memory
```

**What You Gain:**
- ✅ **Conversational Memory**: "Show me Driver data. Now compare to last week." (agent remembers context)
- ✅ **Direct BigQuery Access**: Agent queries database without your code
- ✅ **Tool Calling**: Agent executes functions like `analyze_session()`, `compare_clubs()`
- ✅ **Proactive Insights**: "I noticed your club path changed after shot 15..."
- ✅ **Grounding**: Agent searches web for swing tips from pros
- ✅ **RAG**: Retrieve relevant historical data automatically
- ✅ **Function Calling**: Custom Python execution

**Architecture:**
```
┌───────────────────────────────────────────────────┐
│        Vertex AI Agent Builder                    │
│  ┌─────────────────────────────────────────────┐  │
│  │  Agent with Tools:                          │  │
│  │  - query_bigquery(club, date_range)         │  │
│  │  - analyze_shot(shot_id)                    │  │
│  │  - compare_sessions(session1, session2)     │  │
│  │  - generate_visualization(data, chart_type) │  │
│  │  - search_web(query)                        │  │
│  └─────────────────────────────────────────────┘  │
│           ↓                                        │
│  Multi-turn conversation history                  │
│  Persistent context across questions              │
└───────────────────────────────────────────────────┘
            ↓
┌───────────────────────────────────────────────────┐
│         Your Streamlit App (Keep It!)             │
│  - Chat interface with message history            │
│  - Agent directly queries BigQuery                │
│  - Agent analyzes images/videos                   │
│  - Agent executes complex pipelines               │
└───────────────────────────────────────────────────┘
```

**Cost**: ~$0.10/1K tokens (probably <$5/month)
**Effort**: 2 days implementation

### Phase 2: **Cloud Functions** (1 day - AUTOMATION)

**What Changes:**
```
Current: Manual sync scripts

Upgraded: Event-driven automation
```

**What You Gain:**
- ✅ **Auto-sync**: Firestore → BigQuery happens automatically on new data
- ✅ **Background Processing**: Video frame extraction in parallel
- ✅ **Scheduled Analysis**: Weekly summary emails
- ✅ **Real-time Triggers**: AI analysis when practice session completes

**Architecture:**
```
┌─────────────────┐
│  Streamlit App  │
│  (Import Data)  │
└────────┬────────┘
         │ Publishes event to Pub/Sub
         ▼
┌─────────────────────────────────────────┐
│      Cloud Functions (Triggers)         │
│  ┌───────────────────────────────────┐  │
│  │ on_shot_import():                 │  │
│  │   - Sync to BigQuery              │  │
│  │   - Process video frames          │  │
│  │   - Update analytics cache        │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ on_session_complete():            │  │
│  │   - Run AI analysis               │  │
│  │   - Generate summary report       │  │
│  │   - Email insights                │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Cost**: Free tier (2M invocations/month)
**Effort**: 1 day implementation

### Phase 3: **Cloud Run Deployment** (1 day - ACCESS ANYWHERE)

**What Changes:**
```
Current: localhost:8501 (only on your machine)

Upgraded: golf-data-app.run.app (access from any device)
```

**What You Gain:**
- ✅ **Global Access**: Phone, tablet, laptop, anywhere
- ✅ **Automatic HTTPS**: Secure by default
- ✅ **Auto-scaling**: Handles traffic spikes
- ✅ **Zero maintenance**: No server management

**Deployment:**
```bash
# Build and push
gcloud builds submit --tag gcr.io/valued-odyssey-474423-g1/golf-data-app

# Deploy
gcloud run deploy golf-data-app \
  --image gcr.io/valued-odyssey-474423-g1/golf-data-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="$(cat .env)"
```

**Cost**: Free tier (2M requests/month), then $0.40/million requests
**Effort**: 1 day (mostly configuration)

### Phase 4 (Optional): **Real-time with Firestore**

**What Changes:**
```
Current: SQLite → Supabase → Manual sync → BigQuery

Upgraded: Firestore → Real-time sync → BigQuery (automatic)
```

**What You Gain:**
- ✅ **Real-time updates**: See data instantly across all devices
- ✅ **Offline support**: Native offline-first database
- ✅ **No manual sync**: Firestore → BigQuery happens automatically
- ✅ **Simpler stack**: One database instead of SQLite + Supabase

**Architecture:**
```
┌─────────────────┐
│  Streamlit App  │
│  (Any Device)   │
└────────┬────────┘
         │ Real-time sync
         ▼
┌─────────────────┐      Auto-sync       ┌─────────────┐
│   Firestore     │ ─────────────────→   │  BigQuery   │
│  (Real-time)    │  (Cloud Function)    │  (Analytics)│
└─────────────────┘                      └─────────────┘
         ↕
  All devices see updates instantly
```

**Cost**: Free tier (1GB storage, 50K reads/day)
**Effort**: 2 days (migration)

---

## Implementation Roadmap

### Quick Wins (Week 1)

**Day 1-2**: Vertex AI Agent Builder
- Replace Gemini API calls with Agent Builder
- Define tools: `query_bigquery()`, `analyze_shot()`, `compare_sessions()`
- Add conversational memory
- Test multi-turn interactions

**Day 3**: Cloud Functions for automation
- `on_shot_import()` - Auto-sync to BigQuery
- `on_session_complete()` - Run AI analysis
- Deploy to GCP

**Day 4**: Cloud Run deployment
- Build Docker image for cloud
- Deploy to Cloud Run
- Configure custom domain (optional)
- Test from mobile device

**Day 5**: Testing & refinement
- End-to-end testing
- Performance optimization
- Documentation updates

### Medium-term (Month 1)

- Mobile PWA (progressive web app)
- Scheduled weekly summaries (email)
- Video frame analysis with Gemini Vision
- Custom model training (shot classification)

### Long-term (Month 2-3)

- Firestore migration (real-time sync)
- Native mobile app (React Native or Flutter)
- Multi-user support (share with coach)
- Advanced analytics dashboard (Looker Studio)

---

## Cost Estimates

### Current (Local-First)
- Infrastructure: $0/month
- Supabase: Free tier
- BigQuery: <$1/month (storage + queries)
- **Total**: ~$1/month

### After Upgrades (Cloud-First)
- **Vertex AI Agent**: ~$5/month (personal use, 50 conversations)
- **Cloud Functions**: $0 (free tier sufficient)
- **Cloud Run**: $0-5/month (free tier + minimal overage)
- **Firestore**: $0 (free tier sufficient)
- **BigQuery**: <$1/month (unchanged)
- **Cloud Storage**: $1/month (videos)
- **Total**: ~$7-12/month

### If Scaling (Multi-user)
- 100 users: ~$50-100/month
- 1000 users: ~$300-500/month

---

## Key Technical Details

### API Endpoints

**Uneekor API**:
- Report: `https://api-v2.golfsvc.com/v2/oldmyuneekor/report/{report_id}/{key}`
- Images/Video: `https://api-v2.golfsvc.com/v2/oldmyuneekor/report/shotimage/{report_id}/{key}/{session_id}/{shot_id}`

**URL Parsing**:
- Report ID: `r'id=(\d+)'`
- Key: `r'key=([^&]+)'`

**Shot ID Format**: `{report_id}_{session_id}_{shot_id}`

### Unit Conversions

API returns metric, converted to imperial:
- Speed: `m/s × 2.23694 = mph`
- Distance: `meters × 1.09361 = yards`

### Invalid Data Handling

Uneekor uses `99999` for missing data → converted to `0`

### Smash Factor

Calculated locally: `ball_speed / club_speed`

### Database Schema (42 Columns)

**Identifiers**: shot_id, session_id, date_added, session_date
**Basic**: club, carry, total, smash
**Speed**: ball_speed, club_speed
**Spin**: back_spin, side_spin
**Angles**: launch_angle, side_angle, club_path, face_angle, dynamic_loft, attack_angle, descent_angle
**Impact**: impact_x, impact_y, optix_x, optix_y
**Club Geometry**: club_lie, lie_angle
**Flight**: apex, flight_time, side_distance
**Classification**: shot_type
**Media**: impact_img, swing_img, video_frames
**NEW (Dec 2024)**: sensor_name, client_shot_id, server_timestamp, is_deleted, ball_name, ball_type, club_name_std, club_type, client_session_id, low_point

**Key Enhancements**:
- **Data Cleaning**: 99999 invalid markers converted to 0.0/null
- **Low Point**: Calculated as `-(attack_angle / 2.0)` inches
- **Ball Tracking**: Capture ball compression (SOFT/MEDIUM/FIRM)
- **Sensor ID**: Track launch monitor model (EYEXO, QED, etc.)
- **Strike Analysis**: Club face impact position (impact_x, impact_y in mm)

---

## Files Structure

```
GolfDataApp/
├── Core Application
│   ├── app.py                          # Streamlit UI with AI Coach
│   ├── golf_scraper.py                 # Uneekor API + video download
│   ├── golf_db.py                      # SQLite + Firestore hybrid
│   └── bigquery_schema.json            # BigQuery schema (42 columns)
│
├── Services (New Architecture)
│   ├── services/
│   │   ├── import_service.py           # Data import with cleaning
│   │   ├── data_service.py             # Data access layer
│   │   └── media_service.py            # Media processing
│   └── repositories/
│       ├── shot_repository.py          # Shot data persistence
│       └── media_repository.py         # Media storage
│
├── Docker
│   ├── Dockerfile                      # Multi-stage build
│   ├── docker-compose.yml              # With gcloud credentials mount
│   ├── .dockerignore                   # Excludes sensitive files
│   ├── data/                           # SQLite volume
│   ├── media/                          # Images/videos volume
│   └── logs/                           # Application logs
│
├── scripts/
│   ├── sync_firestore_to_bigquery.py   # Firestore → BigQuery sync
│   ├── migrate_supabase_to_firestore.py # One-time migration
│   ├── gemini_analysis.py              # AI analysis (Gemini API)
│   ├── auto_sync.py                    # Scheduled automation
│   └── post_session.py                 # Interactive analysis
│
├── cloud_functions/
│   └── firestore_to_bigquery/          # Auto-sync function
│       ├── main.py                     # Cloud Function code
│       └── requirements.txt            # Function dependencies
│
├── legacy/
│   ├── golf_scraper_selenium_backup.py # Old scraper (backup)
│   ├── test_connection.py              # Connection testing
│   └── debug_scraper*.py               # Debug scripts
│
└── Documentation
    ├── README.md                       # Quick start
    ├── CLAUDE.md                       # This file (project guide)
    ├── DOCKER_GUIDE.md                 # Docker setup
    ├── VIDEO_IMPLEMENTATION.md         # Video features
    ├── SYNC_ARCHITECTURE.md            # Why manual sync
    ├── DOCKER_AUTH_FIX.md              # Google Cloud auth
    ├── IMPACT_ANALYSIS.md              # NEW: Strike pattern analysis guide
    ├── DATA_EXPANSION_COMPLETE.md      # NEW: Schema expansion summary
    ├── UNEEKOR_DATA_ANALYSIS.md        # Data field analysis
    └── changelog.md                    # Version history
```

---

## Environment Variables

```bash
# Supabase (Cloud Database)
SUPABASE_URL=https://lhccrzxgnmynxmvoydkm.supabase.co
SUPABASE_KEY=your-anon-key

# Google Cloud Platform
GCP_PROJECT_ID=valued-odyssey-474423-g1
GCP_REGION=us-central1
BQ_DATASET_ID=golf_data
BQ_TABLE_ID=shots
GOOGLE_APPLICATION_CREDENTIALS=/app/.gcloud/application_default_credentials.json

# AI Analysis
GEMINI_API_KEY=your-gemini-api-key

# Optional
ANTHROPIC_API_KEY=your-anthropic-key  # Not used (legacy)
```

---

## Common Workflows

### After Practice Session

```bash
# 1. Import data (Streamlit UI)
# Paste Uneekor URL → Run Scraper

# 2. Review in Shot Viewer
# Click shots to see videos/images

# 3. Ask AI Coach questions
# "What's my biggest weakness today?"

# 4. Sync to BigQuery (optional)
python scripts/supabase_to_bigquery.py incremental
```

### Weekly Analysis

```bash
# Full sync to ensure consistency
python scripts/supabase_to_bigquery.py full

# Comprehensive AI analysis
python scripts/gemini_analysis.py summary
python scripts/gemini_analysis.py analyze Driver
```

### Troubleshooting

```bash
# Test connections
python legacy/test_connection.py

# View logs
docker-compose logs -f

# Check BigQuery
gcloud auth application-default login
python -c "from google.cloud import bigquery; print(bigquery.Client().query('SELECT COUNT(*) FROM \`valued-odyssey-474423-g1.golf_data.shots\`').to_dataframe())"
```

---

## Code Architecture Insights

### Design Patterns

- **Local-First**: SQLite primary, cloud optional
- **Self-Healing**: Auto-migrates schema on startup
- **Idempotent**: Upsert prevents duplicate imports
- **Separation of Concerns**: UI / API / Database / Scripts cleanly separated
- **Hybrid Sync**: Automatic (Uneekor→SQLite→Supabase) + Manual (Supabase→BigQuery)

### Critical Code Locations

- **Unit conversions**: `golf_scraper.py:87-88`
- **Video download**: `golf_scraper.py:155-257`
- **Session date extraction**: `golf_scraper.py:73`
- **Schema migration**: `golf_db.py:79-94`
- **AI Coach system prompt**: `app.py:512-565`
- **Video playback UI**: `app.py:298-331`
- **BigQuery sync**: `scripts/supabase_to_bigquery.py:110-140`

---

## Performance Notes

**Image Size**: ~450MB (Docker, optimized)
**Build Time**: 3-5 min (first), 30 sec (cached)
**Memory**: ~200MB (idle), ~500MB (analysis)
**Import Speed**: 10x faster than old Selenium scraper
**Video Storage**: Keyframes = 3x current, Full = 12x current

---

## Security Best Practices

✅ **Implemented**:
- Non-root user in Docker (golfuser)
- Secrets via environment variables
- .dockerignore excludes sensitive files
- Read-only credential mount
- Minimal base image

⚠️ **Remember**:
- Never commit .env
- Rotate API keys regularly
- Use Secret Manager for production

---

## Next Steps

### Immediate (This Week)
1. ✅ Test AI Coach with BigQuery historical data
2. ✅ Re-import a session to populate session_date and video_frames
3. ✅ Test video scrubber in Shot Viewer
4. Add Supabase columns: `ALTER TABLE shots ADD COLUMN session_date TEXT, video_frames TEXT;`

### Short-term (Next Week)
1. Implement Vertex AI Agent Builder (biggest AI upgrade)
2. Deploy Cloud Functions for auto-sync
3. Deploy to Cloud Run (access anywhere)

### Medium-term (Next Month)
1. Mobile PWA for on-course data entry
2. Weekly automated email summaries
3. Video frame analysis with Gemini Vision
4. Custom shot classification model

---

## Additional Documentation

See these files for detailed information:

- **DOCKER_GUIDE.md** - Comprehensive Docker setup
- **VIDEO_IMPLEMENTATION.md** - Video frame details
- **SYNC_ARCHITECTURE.md** - Why BigQuery doesn't auto-update
- **DOCKER_AUTH_FIX.md** - Google Cloud authentication
- **VALIDATION_CHECKLIST.md** - Testing procedures
- **PIPELINE_COMPLETE.md** - Complete pipeline reference
- **QUICKSTART.md** - Command reference
- **changelog.md** - Version history

---

**Last Updated**: December 22, 2024
**Version**: 2.0 (Gemini + Video + Vertex AI Roadmap)
**Status**: Production-ready with Docker, Cloud-ready architecture planned
