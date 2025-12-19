# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a golf data analysis platform with a **local-first hybrid architecture**:

1. **Local Streamlit App** (app.py): Fetches shot data from Uneekor API → stores in SQLite (local-first) → optionally syncs to Supabase (cloud backup) → displays in interactive UI
2. **Cloud Pipeline**: Supabase (cloud DB) → BigQuery (data warehouse) → Gemini AI (analysis)
3. **MCP Control Plane** (NEW): Direct conversational access to databases (SQLite + BigQuery) via MCP Database Toolbox for autonomous AI-driven data discovery

The app is designed for high-altitude golf analysis (Denver) and captures detailed shot metrics including ball speed, spin rates, launch angles, impact location (Optix data), club lie angles, and more.

## Development Commands

### Running the Application
```bash
streamlit run app.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Database Locations
- **Local**: SQLite database `golf_stats.db` (created automatically on first run)
- **Cloud**: Supabase PostgreSQL database at `https://lhccrzxgnmynxmvoydkm.supabase.co`
- **Data Warehouse**: BigQuery `valued-odyssey-474423-g1.golf_data.shots`
- **Media files**: `media/{session_id}/` (created per session)

### Cloud Pipeline Commands

```bash
# Sync Supabase → BigQuery
python scripts/supabase_to_bigquery.py full          # Full sync (replace all)
python scripts/supabase_to_bigquery.py incremental   # Sync only new shots

# AI Analysis with Gemini
python scripts/gemini_analysis.py summary            # Show club performance summary
python scripts/gemini_analysis.py analyze Driver     # AI insights for specific club
python scripts/gemini_analysis.py analyze            # Analyze all clubs

# Alternative AI Analysis (Vertex AI)
python scripts/vertex_ai_analysis.py analyze Driver  # Vertex AI-based analysis

# Automation
python scripts/post_session.py                       # Interactive post-session analysis
python scripts/auto_sync.py                          # Background sync (for cron)
python scripts/auto_sync.py --analyze                # Background sync + AI analysis

# Testing
python legacy/test_connection.py                     # Test all connections
```

## Architecture

### Local Application (Three-Module Structure)

1. **app.py** (Streamlit UI Layer)
   - Main entry point and user interface
   - Sidebar for data import (URL input + scraper trigger)
   - Main dashboard with session selector, metrics, AI prompt generator, and shot viewer
   - Interactive table with row selection triggers media display (impact/swing images)

2. **golf_scraper.py** (API Data Fetcher)
   - **NEW**: Uses Uneekor's REST API instead of browser scraping (much faster and more reliable)
   - Parses report_id and key from URL query parameters (`?id=...&key=...`)
   - API endpoint: `https://api-v2.golfsvc.com/v2/oldmyuneekor/report/{report_id}/{key}`
   - Returns JSON with complete shot data including:
     - Ball flight: ball_speed, club_speed, launch_angle, apex, flight_time
     - Spin: back_spin, side_spin
     - Club data: club_path, club_face_angle, attack_angle, dynamic_loft
     - Impact: impact_x, impact_y
     - Distances: carry_distance, total_distance, side_distance
     - Shot classification: type (straight, hookslice, etc.)
   - Automatically calculates smash factor (ball_speed / club_speed)
   - Handles invalid data (Uneekor uses 99999 for missing values)
   - Image downloading function available but not yet integrated
   - **Backup**: Old Selenium-based scraper saved as `golf_scraper_selenium_backup.py`

3. **golf_db.py** (Database Layer - Hybrid Local/Cloud)
   - **Local-First Architecture**: SQLite for offline access with optional Supabase cloud sync
   - **Dual Database Support**: Automatically manages both SQLite and Supabase (when configured)
   - **Self-Healing Schema**: Auto-migrates new columns to existing SQLite databases
   - **Expanded Schema**: `shots` table now includes 30 fields:
     - Identifiers: shot_id (PK), session_id, date_added
     - Basic: club, carry, total, smash
     - Speed: ball_speed, club_speed
     - Spin: side_spin, back_spin
     - Angles: launch_angle, side_angle, club_path, face_angle, dynamic_loft, attack_angle
     - Impact: impact_x, impact_y, **optix_x, optix_y** (NEW: Uneekor Optix impact location)
     - Flight: side_distance, descent_angle, apex, flight_time
     - Classification: shot_type
     - Club Geometry: **club_lie, lie_angle** (NEW: Club position at impact)
     - Media: impact_img, swing_img
   - `init_db()` creates database and table if not exists, auto-adds missing columns
   - `save_shot()` uses upsert for both SQLite and Supabase, idempotent imports
   - `save_shot_to_supabase()` optional cloud backup with image upload to Supabase Storage
   - Includes helper function to clean invalid values (converts 99999 to 0)
   - `get_session_data()` supports filtering by session_id or returning all shots
   - `get_unique_sessions()` returns distinct sessions ordered by date

### Data Flow

**Local Application Flow (Local-First Hybrid):**
```
User pastes Uneekor URL → golf_scraper parses report_id & key →
HTTP GET to Uneekor API → Receives JSON with all sessions/shots →
For each session (club):
  For each shot:
    Calculate smash factor →
    Clean invalid values (99999 → 0) →
    golf_db.save_shot() → SQLite storage (local-first) →
    golf_db.save_shot_to_supabase() → Optional cloud backup (if configured) →
app.py loads data from SQLite → Displays in interactive table with detailed shot metrics
```

**Cloud Pipeline Flow:**
```
Uneekor API → app.py (Streamlit) → Supabase (PostgreSQL + Cloud Storage for images) →
scripts/supabase_to_bigquery.py → BigQuery (data warehouse) →
scripts/gemini_analysis.py → Gemini API (google-genai SDK) → AI Insights

Optional Automation:
├─ scripts/auto_sync.py (scheduled via cron) → checks for new data → syncs automatically
└─ scripts/post_session.py (manual) → interactive analysis after practice sessions
```

### Key Technical Details

- **API Endpoint**: `https://api-v2.golfsvc.com/v2/oldmyuneekor/report/{report_id}/{key}`
- **URL Parameter Extraction**:
  - Report ID: Regex pattern `r'id=(\d+)'`
  - Key: Regex pattern `r'key=([^&]+)'`
- **Shot ID Format**: `{report_id}_{session_id}_{shot_id}` (e.g., "40945_84428_1283266")
- **Invalid Data Handling**: Uneekor API uses `99999` to indicate missing/invalid measurements
- **Smash Factor Calculation**: `ball_speed / club_speed` (only calculated if club_speed > 0)
- **API Response Structure**:
  - Top level: Array of session objects (one per club)
  - Each session contains: id, name (club), created date, array of shots
  - Each shot contains: 20+ measurement fields plus metadata
- **Image API** (not yet implemented):
  - Endpoint: `https://api-v2.golfsvc.com/v2/oldmyuneekor/report/shotimage/{report_id}/{key}/{session_id}/{shot_id}`
  - Returns array of images with name and path
  - Full URL: `https://api-v2.golfsvc.com/v2{image_path}`

## Important Notes

- **Database Architecture**: Local-first hybrid model with SQLite as primary database for offline access, optional Supabase sync for cloud backup and multi-device access
- **Self-Healing Schema**: SQLite database auto-migrates new columns (optix_x, optix_y, club_lie, lie_angle) on startup
- **API-Based Architecture**: Uses Uneekor's REST API instead of web scraping for faster, more reliable data collection
- **Unit Conversions**: API returns metric units (m/s, meters) which are automatically converted to imperial (mph, yards) in golf_scraper.py:
  - Speed: m/s × 2.23694 = mph
  - Distance: meters × 1.09361 = yards
- **Invalid Data Handling**: API returns `99999` for missing measurements - these are cleaned to 0 in both golf_scraper.py and golf_db.py
- **Smash Factor**: Calculated locally (not provided by API) as ball_speed / club_speed
- **High Altitude Context**: App configured for Denver altitude golf analysis (affects carry distance expectations)
- **Image Storage**: Shot images are uploaded to Supabase Storage bucket "shot-images" and referenced by public URL
- **Legacy Code**: Old Selenium-based scraper and debug scripts moved to `legacy/` directory

## Dependencies

### Local Application
- **streamlit**: UI framework for the web application
- **requests**: HTTP client for API calls and image downloads
- **pandas**: Data manipulation and CSV export for AI analysis
- **sqlite3**: Database (Python stdlib)
- **selenium** (optional): Only needed for legacy backup scraper
- **webdriver-manager** (optional): Only needed for legacy backup scraper

### Cloud Pipeline (install via `pip install -r requirements_cloud.txt`)
- **python-dotenv**: Environment variable management
- **supabase**: Supabase Python client for database access
- **google-cloud-bigquery**: BigQuery client for data warehousing
- **google-cloud-aiplatform**: Vertex AI integration (infrastructure only, not actively used for analysis)
- **google-genai**: Gemini API client for AI analysis (primary analysis engine)
- **db-dtypes**: BigQuery data type support for pandas
- **pandas**: Data manipulation and analysis

## Performance Improvements

### Data Collection
The switch from Selenium-based scraping to API-based fetching provides:
- **10x faster imports**: No browser overhead or wait times for React rendering
- **100% data capture**: Access to all 20+ measurement fields vs 2-3 from HTML scraping
- **More reliable**: No breakage from UI changes, no JavaScript timing issues
- **Cleaner code**: Simple HTTP requests vs complex DOM navigation

### Cloud Pipeline Benefits
- **Scalable storage**: Supabase PostgreSQL handles unlimited shots with indexing
- **Advanced queries**: BigQuery enables complex SQL analytics across all historical data
- **AI insights**: Gemini API provides personalized swing analysis and recommendations
- **Automation**: Scheduled syncing keeps data fresh without manual intervention
- **Multi-device access**: BigQuery accessible from any device with GCP credentials

---

## Cloud Pipeline Architecture Details

### Analysis Engine: Gemini API vs Vertex AI

**Current Implementation:**
- **Primary**: Gemini API via `google-genai` SDK
  - Model: `gemini-3-pro-preview` (used in gemini_analysis.py with code execution)
  - Note: Documentation references `gemini-2.0-flash-exp` but actual implementation uses gemini-3-pro-preview
- **Alternative**: Vertex AI SDK (in vertex_ai_analysis.py)
- **Infrastructure**: Vertex AI enabled for future ML features
- **Why Direct API**: Faster iteration, simpler authentication, direct access to latest models

**Analysis Sources:**
1. **Python Orchestration Scripts** (in `scripts/`):
   - `gemini_analysis.py`: Main analysis tool, queries BigQuery and calls Gemini API (model: gemini-3-pro-preview with code execution)
   - `vertex_ai_analysis.py`: Alternative Vertex AI-based analysis (uses Vertex AI SDK)
   - `auto_sync.py`: Automated sync with optional analysis
   - `post_session.py`: Interactive post-session workflow

2. **Gemini API** (via google-genai SDK):
   - Receives shot data statistics from BigQuery
   - Generates personalized swing analysis
   - Compares against PGA Tour averages (adjusted for Denver altitude)
   - Provides actionable recommendations
   - Identifies patterns in club path, face angle, spin rates, etc.

3. **BigQuery**:
   - Data aggregation and statistical queries
   - Session summaries and trend analysis
   - Historical comparisons
   - Supports complex SQL for custom analysis

**Future Vertex AI Integration Opportunities:**
- AutoML for shot prediction models
- Custom training jobs for swing classification
- Vertex AI Workbench for Jupyter notebook analysis
- Model deployment for real-time shot recommendations
- BigQuery ML for in-database machine learning

### Files Structure

```
GolfDataApp/
├── Core Application
│   ├── app.py                              # Streamlit UI (main entry point)
│   ├── golf_scraper.py                     # Uneekor API client (data fetching + image upload)
│   ├── golf_db.py                          # Supabase database operations
│   └── bigquery_schema.json                # BigQuery table schema definition
│
├── scripts/                                # Cloud Pipeline & Automation
│   ├── supabase_to_bigquery.py             # Sync Supabase → BigQuery
│   ├── gemini_analysis.py                  # AI analysis via Gemini API ⭐
│   ├── vertex_ai_analysis.py               # Alternative Vertex AI-based analysis
│   ├── auto_sync.py                        # Scheduled sync script
│   ├── post_session.py                     # Interactive post-session analysis
│   └── migrate_to_supabase.py              # Migration utility (SQLite → Supabase)
│
├── legacy/                                 # Debug tools & backup implementations
│   ├── test_connection.py                  # Connection testing utility
│   ├── golf_scraper_selenium_backup.py     # Old Selenium-based scraper
│   ├── debug_scraper*.py                   # Debug scripts for API testing
│   ├── inspect_api_response.py             # API response inspector
│   └── check_clubs.py                      # Database inspection utility
│
├── Configuration
│   ├── .env                                # Credentials (not committed)
│   ├── .env.example                        # Environment variable template
│   ├── requirements.txt                    # Local app dependencies
│   ├── requirements_cloud.txt              # Cloud pipeline dependencies
│   └── setup_cron.sh                       # Automation setup wizard
│
└── Documentation
    ├── README.md                           # Project overview & quick start
    ├── CLAUDE.md                           # This file (Claude Code guidance)
    ├── PIPELINE_COMPLETE.md                # Complete pipeline reference
    ├── QUICKSTART.md                       # Quick command reference
    ├── AUTOMATION_GUIDE.md                 # Automation setup guide
    ├── SETUP_GUIDE.md                      # Detailed setup instructions
    └── changelog.md                        # Project change history
```

### Environment Variables (.env)

```bash
# Supabase (Cloud Database)
SUPABASE_URL=https://lhccrzxgnmynxmvoydkm.supabase.co
SUPABASE_KEY=your-anon-key

# Google Cloud Platform
GCP_PROJECT_ID=valued-odyssey-474423-g1
GCP_REGION=us-central1
BQ_DATASET_ID=golf_data
BQ_TABLE_ID=shots

# AI Analysis
GEMINI_API_KEY=your-gemini-api-key

# Optional (other APIs)
ANTHROPIC_API_KEY=your-anthropic-key
```

### Data Schema (Consistent Across SQLite, Supabase, BigQuery)

All 30 fields are synced across platforms:
- **Identifiers**: shot_id (PK), session_id, date_added
- **Club Info**: club
- **Distance**: carry, total, side_distance
- **Speed**: ball_speed, club_speed, smash
- **Spin**: back_spin, side_spin
- **Angles**: launch_angle, side_angle, club_path, face_angle, dynamic_loft, attack_angle, descent_angle
- **Impact**: impact_x, impact_y, **optix_x, optix_y** (Uneekor Optix precise impact location)
- **Club Geometry**: **club_lie, lie_angle** (Club position at impact)
- **Flight**: apex, flight_time
- **Classification**: shot_type
- **Media**: impact_img, swing_img

### BigQuery Indexes (Automatic)

Created during setup for optimal query performance:
- Primary: shot_id
- session_id (for session-based queries)
- date_added (for time-series analysis)
- club (for club-specific analysis)

---

## AI Analysis Capabilities

### What Gemini AI Analyzes

1. **Swing Mechanics**:
   - Club speed efficiency
   - Smash factor optimization
   - Attack angle consistency
   - Club path patterns

2. **Shot Dispersion**:
   - Standard deviation analysis
   - Consistency patterns
   - Outlier detection

3. **Comparisons**:
   - PGA Tour averages (altitude-adjusted)
   - Personal historical trends
   - Club-to-club performance

4. **Correlations**:
   - Club path vs side spin
   - Face angle vs shot shape
   - Launch angle vs carry distance
   - Attack angle vs spin rates

5. **Recommendations**:
   - Specific improvement areas
   - Optimal launch conditions
   - Training focus suggestions
   - Equipment optimization

### Sample AI Output

For a Driver analysis with 5 shots:
- Identifies high smash factor (1.38) as strength
- Flags low club speed (51.1 mph) as primary limiting factor
- Recommends swing speed training and center-face contact drills
- Suggests optimal launch conditions (12-14° launch, 2000-2400 rpm spin)
- Compares to PGA Tour averages adjusted for Denver altitude

---

## Automation Options

### Option 1: Manual (scripts/post_session.py)
- Run after each practice session
- Interactive prompts guide analysis
- Full control over when AI runs
- Best for: Learning the system

### Option 2: Hourly Sync (scripts/auto_sync.py via cron)
- Data always fresh in BigQuery
- No analysis overhead
- Run manual analysis when needed
- Best for: Keeping data current

### Option 3: Daily Sync + Analysis
- Evening analysis of all day's shots
- Automated insights without intervention
- Log history for tracking
- Best for: Hands-off operation

### Setup Automation
```bash
./setup_cron.sh  # Interactive setup wizard
```

---

## MCP Control Plane Integration

### Overview
The **MCP Database Toolbox** provides a unified "Control Plane" for conversational AI access to your golf data across both local SQLite and cloud BigQuery databases.

### Architecture
- **Shared Interface**: Single YAML configuration for multiple data sources
- **Autonomous Discovery**: AI agents can independently explore schemas using `list-tables` and `get-table-schema`
- **Conversational Analytics**: Natural language queries without writing SQL
- **Multi-Source Support**: Seamlessly query both local SQLite and BigQuery from one interface

### Setup
1. **Install MCP Toolbox**: Download binary to `~/.mcp/database-toolbox/`
2. **Create Configuration** (`~/.mcp/database-toolbox/tools.yaml`):
   ```yaml
   sources:
     local-sqlite:
       kind: sqlite
       database: /absolute/path/to/golf_stats.db
     google-bigquery:
       kind: bigquery
       project: valued-odyssey-474423-g1
   ```
3. **Start MCP Server**:
   ```bash
   toolbox --tools-file ~/.mcp/database-toolbox/tools.yaml --stdio
   ```

### Use Cases
- **Cross-Database Queries**: Compare local practice data with cloud historical data
- **AI-Driven Discovery**: Let AI agents explore schema and find insights autonomously
- **Unified Interface**: Single command to access all your golf data sources
- **Real-Time Analysis**: Query fresh local data without cloud sync delays

### Integration Points
- **Local SQLite**: Direct access to `golf_stats.db` for offline analysis
- **BigQuery**: Access to full historical data warehouse
- **Supabase**: Can be added as a PostgreSQL source (optional)

For detailed setup instructions, see `SETUP_GUIDE.md` Step 10.

---

## Common Workflows

### After Practice Session
```bash
python scripts/post_session.py
# Shows today's summary, offers AI analysis, displays all-time stats
```

### Quick Club Check
```bash
python scripts/gemini_analysis.py summary
python scripts/gemini_analysis.py analyze Driver
```

### Troubleshooting
```bash
python legacy/test_connection.py  # Test all connections
tail -f logs/sync.log             # View automation logs
```

### BigQuery Exploration
```sql
-- Average by club (in BigQuery Console)
SELECT club, AVG(carry), AVG(smash), COUNT(*)
FROM `valued-odyssey-474423-g1.golf_data.shots`
WHERE carry > 0
GROUP BY club
ORDER BY AVG(carry) DESC
```

---

## Code Architecture Insights

### Data Flow Through Modules

**Import Flow (app.py → golf_scraper.py → golf_db.py → Local/Cloud):**
1. User pastes Uneekor URL in Streamlit sidebar
2. `golf_scraper.extract_url_params()` parses report_id and key from URL
3. `golf_scraper.run_scraper()` fetches JSON from Uneekor API
4. For each shot in each session:
   - Convert metric units to imperial (m/s → mph, meters → yards)
   - Calculate smash factor (ball_speed / club_speed)
   - Extract advanced metrics (optix_x, optix_y, club_lie, lie_angle)
   - `golf_db.save_shot()` upserts data to SQLite (local-first)
   - `golf_db.save_shot_to_supabase()` optionally uploads to cloud (if SUPABASE_URL configured)
   - `golf_scraper.upload_shot_images()` downloads images and uploads to Supabase Storage (if cloud enabled)
5. `app.py` queries SQLite via `golf_db.get_session_data()` and displays in UI

**Sync Flow (Supabase → BigQuery):**
1. `scripts/supabase_to_bigquery.py` fetches all shots from Supabase (paginated)
2. Transforms data to match BigQuery schema
3. Uses `WRITE_TRUNCATE` (full) or `WRITE_APPEND` (incremental) load jobs
4. BigQuery table ready for SQL queries and AI analysis

**Analysis Flow (BigQuery → Gemini API):**
1. `scripts/gemini_analysis.py` queries BigQuery for shot data
2. Converts result to CSV format for efficient token usage
3. Sends to Gemini API with code execution tool enabled
4. Gemini writes and executes Python code to analyze data
5. Returns statistical insights and recommendations

### Key Design Patterns

- **Local-First Architecture**: SQLite as primary database for offline access, optional cloud sync
- **Self-Healing Schema**: Auto-migration of new columns on startup (no manual ALTER TABLE needed)
- **Idempotent Imports**: `golf_db.save_shot()` uses upsert to prevent duplicates (both SQLite and Supabase)
- **Unit Conversion Layer**: All metric→imperial conversions happen in `golf_scraper.py` (single source of truth)
- **Invalid Data Cleaning**: Both `golf_scraper.py` and `golf_db.py` clean invalid values (99999 → 0)
- **Separation of Concerns**:
  - `app.py` = UI only
  - `golf_scraper.py` = External API integration
  - `golf_db.py` = Database abstraction (dual SQLite/Supabase support)
  - `scripts/` = Batch processing and analysis

### Critical Code Locations

- **Unit conversion constants**: `golf_scraper.py:87-88`
- **Advanced metrics extraction**: `golf_scraper.py` (optix_x, optix_y, club_lie, lie_angle)
- **Self-healing schema migration**: `golf_db.py:init_db()` (auto-adds missing columns)
- **Dual database save logic**: `golf_db.py:save_shot()` (SQLite) and `save_shot_to_supabase()` (cloud)
- **Image upload to Supabase**: `golf_scraper.py:148-207`
- **BigQuery schema definition**: `bigquery_schema.json`
- **Supabase schema definition**: `supabase_schema.sql`
- **Gemini AI prompt template**: `scripts/gemini_analysis.py:67-87`
