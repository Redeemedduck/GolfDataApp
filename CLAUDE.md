# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a golf data analysis platform with two architectures and **dual AI analysis**:

1. **Local Streamlit App** (app.py): Fetches shot data from Uneekor API → stores in SQLite → displays in interactive UI with AI Coach
2. **Cloud Pipeline** (NEW): Supabase (cloud DB) → BigQuery (data warehouse) → Multi-Agent AI (Claude + Gemini)

The app is designed for high-altitude golf analysis (Denver) and captures detailed shot metrics including ball speed, spin rates, launch angles, and more.

### Multi-Agent AI System
- **Claude AI**: Conversational coaching, drill recommendations, interactive chat
- **Gemini AI**: Statistical analysis, code execution, pattern detection
- **Combined**: Complementary insights for comprehensive golf improvement

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

# AI Analysis with Claude (NEW)
python scripts/claude_analysis.py                      # Analyze all clubs
python scripts/claude_analysis.py Driver               # Analyze specific club
python scripts/claude_analysis.py --model=opus         # Use Opus (best quality)
python scripts/claude_analysis.py --model=sonnet       # Use Sonnet (balanced)
python scripts/claude_analysis.py --model=haiku        # Use Haiku (fast/cheap)
python scripts/claude_analysis.py --interactive        # Interactive chat mode

# AI Analysis with Gemini
python gemini_analysis.py summary            # Show club performance summary
python gemini_analysis.py analyze Driver     # AI insights for specific club
python gemini_analysis.py analyze            # Analyze all clubs

# Multi-Agent Comparison (NEW)
python scripts/compare_ai_analysis.py Driver           # Compare Claude vs Gemini
python scripts/compare_ai_analysis.py --save           # Save comparison report
python scripts/compare_ai_analysis.py Driver --claude-model=opus --save

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
   - **Dashboard Tab**: Session selector, KPI metrics, charts (carry by club, dispersion)
   - **Shot Viewer Tab**: Interactive table with detailed shot metrics, media display (impact/swing images)
   - **AI Coach Tab (NEW)**: Interactive chat with Claude AI for personalized coaching
     - Model selector (Opus/Sonnet/Haiku)
     - Persistent conversation history per session
     - Session data automatically included in context
     - Quick analysis button for instant insights
     - Chat resets when switching sessions

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
┌─ claude_analysis.py → Claude API (anthropic SDK) → Conversational AI Coaching
└─ gemini_analysis.py → Gemini API (google-genai SDK) → Statistical AI Insights
   └─ compare_ai_analysis.py → Both AIs → Multi-Agent Comparison

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
- **Multi-Agent AI**: Both Claude and Gemini available for analysis - use each for their strengths or compare them
- **SQL Injection Protection**: Parameterized queries used throughout (fixed in latest version)
- **Security**: All sensitive credentials stored in `.env` file (not committed to git)
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
- **anthropic**: Claude API client for conversational AI coaching (NEW)
- **selenium** (optional): Only needed for legacy backup scraper
- **webdriver-manager** (optional): Only needed for legacy backup scraper

### Cloud Pipeline (install via `pip install -r requirements_cloud.txt`)
- **python-dotenv**: Environment variable management
- **supabase**: Supabase Python client for database access
- **google-cloud-bigquery**: BigQuery client for data warehousing
- **google-cloud-aiplatform**: Vertex AI integration (infrastructure only, not actively used for analysis)
- **google-genai**: Gemini API client for AI analysis (statistical analysis engine)
- **anthropic**: Claude API client for AI analysis (conversational coaching engine)
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

### Analysis Engine: Multi-Agent AI (Claude + Gemini)

**Current Implementation:**
- **Dual AI System**: Claude AI + Gemini AI working together
- **Claude AI** via `anthropic` SDK (claude-opus-4, claude-sonnet-4.5, claude-haiku-4)
  - Conversational coaching and personalized drill recommendations
  - Nuanced swing interpretation and contextual explanations
  - Interactive chat capabilities with conversation memory
  - Prompt caching for cost efficiency (90% savings on repeated analyses)
- **Gemini AI** via `google-genai` SDK (gemini-2.0-flash-exp model)
  - Python code execution for statistical analysis
  - Mathematical correlations and pattern detection
  - Advanced dispersion and consistency calculations
- **Infrastructure**: Vertex AI enabled for future ML features

**Why Multi-Agent Approach:**
- Different AI models excel at different analysis types
- Claude best for: coaching dialogue, drill suggestions, "why" explanations
- Gemini best for: numerical analysis, correlations, "what" calculations
- When both AIs agree → high-confidence recommendations
- When they differ → interesting insights requiring human judgment

**Analysis Sources:**
1. **Python Orchestration Scripts**:
   - `claude_analysis.py`: Claude-powered analysis with prompt caching (NEW)
   - `gemini_analysis.py`: Gemini analysis with code execution
   - `compare_ai_analysis.py`: Multi-agent comparison tool (NEW)
   - `auto_sync.py`: Automated sync with optional analysis
   - `post_session.py`: Interactive post-session workflow

2. **Claude API** (via anthropic SDK):
   - Receives shot data from BigQuery
   - Generates conversational coaching insights
   - Provides structured drill recommendations
   - Compares to altitude-adjusted PGA Tour averages
   - Maintains conversation context for follow-up questions
   - Uses prompt caching to reduce costs by 90% on repeated runs

3. **Gemini API** (via google-genai SDK):
   - Receives shot data from BigQuery
   - Executes Python code for statistical calculations
   - Generates numerical swing analysis
   - Identifies mathematical patterns and correlations
   - Compares to PGA Tour averages (altitude-adjusted)

4. **BigQuery**:
   - Data aggregation and statistical queries
   - Session summaries and trend analysis
   - Historical comparisons
   - Supports complex SQL for custom analysis
   - Single source of truth for both AI engines

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
│   ├── app.py                      # Streamlit UI with AI Coach tab ⭐
│   ├── golf_scraper.py             # Uneekor API client
│   ├── golf_db.py                  # SQLite operations
│   └── golf_stats.db               # Local database
│
├── Cloud Pipeline
│   ├── supabase_to_bigquery.py     # Sync Supabase → BigQuery
│   ├── gemini_analysis.py          # AI analysis via Gemini API (statistical)
│   ├── vertex_ai_analysis.py       # Vertex AI integration (alternative, not primary)
│   ├── bigquery_schema.json        # BigQuery table schema
│   └── test_connection.py          # Connection testing
│
├── Scripts (Multi-Agent AI) ⭐ NEW
│   ├── claude_analysis.py          # AI analysis via Claude API (conversational)
│   └── compare_ai_analysis.py      # Multi-agent comparison (Claude vs Gemini)
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
    ├── CLAUDE_AI_INTEGRATION.md    # Claude integration guide ⭐ NEW
    ├── CLAUDE_INTEGRATION_RECOMMENDATIONS.md  # Detailed recommendations ⭐ NEW
    ├── CODE_REVIEW_RESPONSE.md     # Security fixes documentation ⭐ NEW
    ├── INTEGRATION_SUMMARY.md      # Quick overview ⭐ NEW
    ├── CHANGELOG.md                # Version history ⭐ NEW
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

# AI Analysis (Multi-Agent)
GEMINI_API_KEY=your-gemini-api-key        # For statistical analysis
ANTHROPIC_API_KEY=your-anthropic-key      # For conversational coaching (NEW)
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

### Multi-Agent AI Analysis

The platform uses **two AI engines** working together for comprehensive insights:

**Claude AI** - Conversational Golf Coach:
- Interactive chat for personalized Q&A
- Nuanced swing interpretation and contextual explanations
- Specific drill recommendations with setup instructions
- Encouraging coaching tone with actionable feedback
- "Why" explanations (e.g., "why am I pulling left?")
- Maintains conversation context across multiple questions

**Gemini AI** - Statistical Analyst:
- Python code execution for mathematical analysis
- Advanced statistical calculations (dispersion, correlations)
- Pattern detection across large datasets
- Numerical precision and quantitative insights
- "What" calculations (e.g., "what is my standard deviation?")

**When to Use Each:**
- Use **Claude** for: coaching dialogue, drill recommendations, understanding "why"
- Use **Gemini** for: statistical deep-dives, correlation analysis, numerical patterns
- Use **Both** (comparison): for comprehensive validation and multi-perspective insights

### What the AIs Analyze

1. **Swing Mechanics**:
   - Club speed efficiency and optimization potential
   - Smash factor analysis (ball speed / club speed ratio)
   - Attack angle consistency and appropriateness
   - Club path patterns (in-to-out vs out-to-in tendencies)

2. **Shot Dispersion**:
   - Standard deviation analysis (lateral and distance)
   - Consistency patterns and variability trends
   - Outlier detection and frequency
   - Shot shape control reliability

3. **Comparisons**:
   - PGA Tour averages (altitude-adjusted for Denver)
   - Personal historical trends and improvement tracking
   - Club-to-club performance benchmarking
   - Session-to-session progress monitoring

4. **Correlations**:
   - Club path vs side spin relationship
   - Face angle vs shot shape patterns
   - Launch angle vs carry distance optimization
   - Attack angle vs spin rate effects
   - Impact location vs ball flight characteristics

5. **Recommendations**:
   - Specific improvement areas with priority ranking
   - Optimal launch conditions for each club
   - Training focus suggestions with drill specifics
   - Equipment optimization opportunities

### Sample AI Outputs

**Claude Analysis (Conversational):**
```
🏌️ Golf Performance Analysis: Driver

## 🎯 Key Strengths
- Excellent smash factor (1.48) - you're finding the center consistently
- Good launch angle (11.2°) - optimal for your swing speed
- Ball speed efficiency is tour-level for your club speed

## ⚠️ Primary Areas for Improvement
- Club speed (92 mph) is below tour average (112 mph) - biggest distance limiter
- Side spin variability (±850 rpm) suggests inconsistent face control
- Attack angle slightly negative (-1.2°) - hitting down on driver

## 💡 Actionable Recommendations

### Priority #1: Increase Swing Speed
- **Drill:** Overspeed training with lighter club (60% weight)
- **Feel:** Faster tempo on downswing, "swoosh" at impact
- **Measurement:** Target 95 mph by next month (3 mph gain)

### Priority #2: Improve Face Control
- **Drill:** Impact bag work focusing on square face
- **Feel:** Quiet hands through impact, stable face angle
- **Measurement:** Reduce side spin std dev to ±500 rpm
```

**Gemini Analysis (Statistical):**
```python
# Code Execution Results:

Dispersion Analysis:
- Side Distance Std Dev: 23.4 yards (Tour Avg: 15.2 yards)
- Carry Distance Std Dev: 8.7 yards (Tour Avg: 6.1 yards)

Correlation Analysis:
- Club Path vs Side Spin: r=0.87 (strong positive)
- Face Angle vs Club Path: r=0.62 (moderate positive)
- Club Speed vs Carry: r=0.94 (very strong positive)

Consistency Ranking:
1. Smash Factor: CV=2.1% (excellent)
2. Launch Angle: CV=8.4% (good)
3. Side Spin: CV=34.2% (needs improvement)
```

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
# Interactive UI with AI Coach
streamlit run app.py  # Use AI Coach tab for chat

# CLI post-session analysis
python post_session.py  # Shows summary, offers AI analysis

# Quick Claude analysis
python scripts/claude_analysis.py Driver --model=haiku  # Fast feedback

# Multi-agent comparison
python scripts/compare_ai_analysis.py Driver --save  # Both AIs
```

### Quick Club Check
```bash
# Claude (conversational coaching)
python scripts/claude_analysis.py Driver
python scripts/claude_analysis.py --interactive  # Chat mode

# Gemini (statistical analysis)
python gemini_analysis.py summary
python gemini_analysis.py analyze Driver

# Compare both
python scripts/compare_ai_analysis.py Driver
```

### Interactive AI Coaching Session
```bash
# Launch Streamlit app
streamlit run app.py

# Steps:
# 1. Select your session
# 2. Click "AI Coach" tab
# 3. Ask questions:
#    - "Why am I pulling my driver left?"
#    - "How can I improve consistency?"
#    - "What drill should I work on?"
# 4. Model selector: Opus (best), Sonnet (balanced), Haiku (fast)
# 5. Chat history persists throughout session
```

### Troubleshooting
```bash
python test_connection.py  # Test all connections
tail -f logs/sync.log      # View automation logs

# Verify API keys
echo $ANTHROPIC_API_KEY    # Claude API key
echo $GEMINI_API_KEY       # Gemini API key
```

### BigQuery Exploration
```sql
-- Average by club (in BigQuery Console)
SELECT club, AVG(carry), AVG(smash), COUNT(*)
FROM `valued-odyssey-474423-g1.golf_data.shots`
WHERE carry > 0
GROUP BY club
ORDER BY AVG(carry) DESC;

-- Recent session analysis
SELECT
  club,
  COUNT(*) as shots,
  AVG(carry) as avg_carry,
  STDDEV(side_distance) as dispersion,
  AVG(smash) as avg_smash
FROM `valued-odyssey-474423-g1.golf_data.shots`
WHERE DATE(date_added) >= CURRENT_DATE() - 7
GROUP BY club
ORDER BY avg_carry DESC;
```
