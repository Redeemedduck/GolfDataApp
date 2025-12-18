# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a golf data analysis platform with two architectures:

1. **Local Streamlit App** (app.py): Fetches shot data from Uneekor API → stores in SQLite → displays in interactive UI
2. **Cloud Pipeline** (NEW): Supabase (cloud DB) → BigQuery (data warehouse) → Gemini AI (analysis)

The app is designed for high-altitude golf analysis (Denver) and captures detailed shot metrics including ball speed, spin rates, launch angles, and more.

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
python supabase_to_bigquery.py full          # Full sync (replace all)
python supabase_to_bigquery.py incremental   # Sync only new shots

# AI Analysis with Gemini
python gemini_analysis.py summary            # Show club performance summary
python gemini_analysis.py analyze Driver     # AI insights for specific club
python gemini_analysis.py analyze            # Analyze all clubs

# Automation
python post_session.py                       # Interactive post-session analysis
python auto_sync.py                          # Background sync (for cron)
python auto_sync.py --analyze                # Background sync + AI analysis

# Testing
python test_connection.py                    # Test all connections
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

3. **golf_db.py** (Database Layer)
   - SQLite operations for shot storage and retrieval
   - **Expanded Schema**: `shots` table now includes 25+ fields:
     - Identifiers: shot_id (PK), session_id, date_added
     - Basic: club, carry, total, smash
     - Speed: ball_speed, club_speed
     - Spin: side_spin, back_spin
     - Angles: launch_angle, side_angle, club_path, face_angle, dynamic_loft, attack_angle
     - Impact: impact_x, impact_y
     - Flight: side_distance, descent_angle, apex, flight_time
     - Classification: shot_type
     - Media: impact_img, swing_img
   - `init_db()` creates database and table if not exists
   - `save_shot()` uses INSERT OR REPLACE for idempotent imports, handles both old and new API formats
   - Includes helper function to clean invalid values (converts 99999 to 0)
   - `get_session_data()` supports filtering by session_id or returning all shots
   - `get_unique_sessions()` returns distinct sessions ordered by date

### Data Flow

**Local Application Flow:**
```
User pastes Uneekor URL → golf_scraper parses report_id & key →
HTTP GET to Uneekor API → Receives JSON with all sessions/shots →
For each session (club):
  For each shot:
    Calculate smash factor →
    Clean invalid values (99999 → 0) →
    golf_db.save_shot() → SQLite storage →
app.py loads data → Displays in interactive table with detailed shot metrics
```

**Cloud Pipeline Flow (NEW):**
```
Uneekor API → (via app.py or direct) → Supabase (PostgreSQL) →
supabase_to_bigquery.py (sync) → BigQuery (data warehouse) →
gemini_analysis.py → Gemini API (google-genai SDK) → AI Insights

Optional Automation:
├─ auto_sync.py (scheduled via cron) → checks for new data → syncs automatically
└─ post_session.py (manual) → interactive analysis after practice sessions
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

- **API-Based Architecture**: Application now uses Uneekor's API instead of web scraping for faster, more reliable data collection
- **SQL Injection Risk**: Still exists in `get_session_data()` - session IDs should be validated before use in queries
- **Database Migration**: When updating from old schema, delete `golf_stats.db` to recreate with new expanded schema
- **Invalid Data**: API returns `99999` for missing measurements - these are automatically converted to 0
- **Smash Factor**: Calculated locally (not provided by API) as ball_speed / club_speed
- **High Altitude Context**: App configured for Denver altitude golf analysis (affects carry distance expectations)
- **Image Download**: API endpoint available in `download_shot_images()` but not yet integrated into main import flow
- **Legacy Scraper**: Old Selenium-based scraper saved as `golf_scraper_selenium_backup.py` in case API access is lost

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
- **Primary**: Gemini API via `google-genai` SDK (gemini-2.0-flash-exp model)
- **Infrastructure**: Vertex AI enabled for future ML features
- **Why Direct API**: Faster iteration, simpler authentication, model access issues with Vertex AI Generative Models in this project

**Analysis Sources:**
1. **Python Orchestration Scripts**:
   - `gemini_analysis.py`: Main analysis tool, queries BigQuery and calls Gemini API
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
├── Local Application
│   ├── app.py                      # Streamlit UI
│   ├── golf_scraper.py             # Uneekor API client
│   ├── golf_db.py                  # SQLite operations
│   └── golf_stats.db               # Local database
│
├── Cloud Pipeline
│   ├── supabase_to_bigquery.py     # Sync Supabase → BigQuery
│   ├── gemini_analysis.py          # AI analysis via Gemini API ⭐
│   ├── vertex_ai_analysis.py       # Vertex AI integration (alternative, not primary)
│   ├── bigquery_schema.json        # BigQuery table schema
│   └── test_connection.py          # Connection testing
│
├── Automation
│   ├── auto_sync.py                # Scheduled sync script
│   ├── post_session.py             # Interactive post-session analysis
│   └── setup_cron.sh               # Automation setup wizard
│
├── Configuration
│   ├── .env                        # Credentials (not committed)
│   ├── requirements.txt            # Local app dependencies
│   └── requirements_cloud.txt      # Cloud pipeline dependencies
│
└── Documentation
    ├── CLAUDE.md                   # This file
    ├── PIPELINE_COMPLETE.md        # Complete pipeline reference
    ├── QUICKSTART.md               # Quick command reference
    ├── AUTOMATION_GUIDE.md         # Automation setup guide
    └── SETUP_GUIDE.md              # Detailed setup instructions
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

All 26 fields are synced across platforms:
- **Identifiers**: shot_id (PK), session_id, date_added
- **Club Info**: club
- **Distance**: carry, total, side_distance
- **Speed**: ball_speed, club_speed, smash
- **Spin**: back_spin, side_spin
- **Angles**: launch_angle, side_angle, club_path, face_angle, dynamic_loft, attack_angle, descent_angle
- **Impact**: impact_x, impact_y
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

### Option 1: Manual (post_session.py)
- Run after each practice session
- Interactive prompts guide analysis
- Full control over when AI runs
- Best for: Learning the system

### Option 2: Hourly Sync (auto_sync.py via cron)
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

## Common Workflows

### After Practice Session
```bash
python post_session.py
# Shows today's summary, offers AI analysis, displays all-time stats
```

### Quick Club Check
```bash
python gemini_analysis.py summary
python gemini_analysis.py analyze Driver
```

### Troubleshooting
```bash
python test_connection.py  # Test all connections
tail -f logs/sync.log      # View automation logs
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
