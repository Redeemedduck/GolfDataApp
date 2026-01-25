# CLAUDE.md - Branch: production-no-ml

This file provides guidance to Claude Code when working with code in this branch.

**Branch Focus**: Production-Ready Cloud-Native AI Coach with Gemini 3.0

---

## 🎯 Branch Overview

This is the **production-no-ml** branch, which provides a cloud-native AI coaching experience using Google's Gemini 3.0 models instead of local machine learning models.

**Key Differences from Main Branch:**
- ❌ **NO local ML models** (no scikit-learn, XGBoost, Isolation Forest)
- ✅ **Cloud-native AI** with Gemini 3.0 function calling
- ✅ **Zero model training required** (no .pkl files, no training scripts)
- ✅ **Serverless architecture** ready for Google Cloud Run
- ✅ **Lower resource footprint** (no ML dependencies)

**What's Included:**
- ✅ Multi-page Streamlit architecture (Phases 1-3)
- ✅ Enhanced database management with audit trail
- ✅ Advanced visualizations and export tools
- ✅ Google Cloud Run containerization
- ✅ **AI Coach with Gemini 3.0 function calling** (NEW)

---

## 📁 Project Structure

```
GolfDataApp/
├── app.py                              # Landing page with AI Coach navigation
│
├── golf_db.py                          # Database layer (866 lines)
├── golf_scraper.py                     # Uneekor API client
├── gemini_coach.py                     # Gemini 3.0 AI Coach (NEW - 600+ lines)
│
├── pages/                               # Multi-page app
│   ├── 1_📥_Data_Import.py             # Uneekor data import
│   ├── 2_📊_Dashboard.py               # Analytics (5 tabs)
│   ├── 3_🗄️_Database_Manager.py       # CRUD operations (6 tabs)
│   └── 4_🤖_AI_Coach.py                # Gemini chat interface (NEW)
│
├── components/                          # Reusable UI components
│   ├── __init__.py
│   ├── session_selector.py             # Session/club filter widget
│   ├── metrics_card.py                 # KPI metrics display
│   ├── shot_table.py                   # Interactive shot table
│   ├── heatmap_chart.py                # Impact location heatmap
│   ├── trend_chart.py                  # Performance trends
│   ├── radar_chart.py                  # Multi-metric comparison
│   └── export_tools.py                 # CSV/Excel/text export
│
├── scripts/                             # Cloud sync & automation
│   ├── supabase_to_bigquery.py         # Cloud data warehouse sync
│   ├── gemini_analysis.py              # Batch AI analysis
│   ├── auto_sync.py                    # Automation
│   └── post_session.py                 # Post-session hooks
│
├── docs/                                # Documentation
│   └── ...
│
├── .streamlit/                          # Streamlit config
│   └── config.toml                     # Production settings
│
├── Dockerfile                           # Cloud Run containerization
├── .dockerignore                        # Docker exclusions
├── cloudbuild.yaml                     # CI/CD pipeline
└── CLOUD_RUN_DEPLOYMENT.md             # Deployment guide
```

**Key Difference**: No `utils/` directory, no `models/` directory, no ML training scripts.

### Automation Module (NEW)

```
automation/                             # Scraper automation system
├── __init__.py                        # Module exports
├── credential_manager.py              # Cookie persistence + encryption
├── rate_limiter.py                    # Token bucket throttling
├── browser_client.py                  # Playwright browser lifecycle
├── uneekor_portal.py                  # Portal navigation & extraction
├── session_discovery.py               # Discovery + deduplication
├── naming_conventions.py              # Club/session standardization
├── backfill_runner.py                 # Historical import with checkpointing
└── notifications.py                   # Slack integration

automation_runner.py                    # CLI entry point
```

---

## 🚀 Running the Application

### Quick Start

```bash
# 1. Set up environment variables
cp .env.example .env
# Add your GEMINI_API_KEY to .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the app
streamlit run app.py
```

The app will open at `http://localhost:8501/` with:
- **Landing page**: Quick stats and navigation to 4 pages
- **Data Import**: Import from Uneekor URLs
- **Dashboard**: Advanced analytics with 5 tabs
- **Database Manager**: CRUD operations with 6 tabs
- **AI Coach**: Chat-based coaching with Gemini 3.0 (NEW)

### Environment Setup

Create a `.env` file with:
```bash
# Required for AI Coach
GEMINI_API_KEY=your_gemini_api_key_here

# Optional for cloud sync
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

**Get Gemini API Key**: https://aistudio.google.com/app/apikey

---

## 🤖 AI Coach with Gemini 3.0

### Overview

The AI Coach uses **Google Gemini 3.0** models with **function calling** to provide personalized golf coaching. Unlike local ML models that need training, Gemini can directly query your golf data and provide insights on-demand.

### Architecture

```
User Question
    ↓
Gemini 3.0 Model
    ↓
Function Calling (if needed)
    ↓
Query Golf Database
    ↓
Return Data to Gemini
    ↓
Generate Coaching Response
```

### Available Models

**Gemini 3.0 Flash** (Recommended):
- **Speed**: 3x faster than Gemini 2.5 Pro
- **Cost**: $0.50/1M input tokens, $3/1M output tokens
- **Use case**: General coaching questions, quick analysis
- **Context**: 1M tokens (huge conversation history)

**Gemini 3.0 Pro**:
- **Reasoning**: Enhanced complex reasoning
- **Use case**: Multi-step analysis, agentic workflows
- **Cost**: Higher than Flash
- **Context**: 1M tokens

### Function Calling Tools

The AI Coach has access to 6 function calling tools:

1. **query_shot_data**: Retrieve shot data from database
   - Filter by session, club, or limit
   - Returns shot records with all metrics

2. **calculate_statistics**: Calculate stats for any metric
   - Mean, median, std dev, min, max, quartiles
   - Coefficient of variation for consistency
   - Works across sessions or specific clubs

3. **get_user_profile**: Get performance baselines
   - Overall or club-specific profile
   - Consistency scores per metric
   - Total shots and club breakdown

4. **analyze_trends**: Performance trends over time
   - Linear regression analysis
   - Session-by-session tracking
   - Improvement percentage calculation

5. **get_club_gapping**: Distance gap analysis
   - Average carry per club
   - Gaps between consecutive clubs
   - Identify gapping issues

6. **find_outliers**: Detect unusual shots
   - Unrealistic values (carry > 400 yds, smash > 1.6, etc.)
   - Data quality checking
   - Session or club filtering

### Using the AI Coach

**Example Questions:**

```
"What's my average carry distance with Driver?"
→ Calls: calculate_statistics(metric='carry', club='Driver')

"How has my ball speed improved over time?"
→ Calls: analyze_trends(club='Driver', metric='ball_speed')

"Do I have any club gapping issues?"
→ Calls: get_club_gapping()

"Show me my most recent outliers"
→ Calls: find_outliers(limit=10)

"What should I work on in my next practice session?"
→ Calls: get_user_profile() + calculate_statistics() + generate insights
```

**Chat Interface Features:**
- Multi-turn conversations with context
- Suggested starter questions
- Function call transparency (see what data was accessed)
- Model selection (Flash vs Pro)
- Thinking level control (minimal/low/medium/high)
- Conversation reset

### Code Example

```python
from gemini_coach import GeminiCoach

# Initialize coach
coach = GeminiCoach(model_type='flash', thinking_level='medium')

# Ask a question
response = coach.chat("What's my average carry with 7 iron?")

print(response['response'])
# Output: "Based on your data, your average carry with 7 iron is 165.3 yards..."

# Check function calls made
for fn_call in response['function_calls']:
    print(f"Called: {fn_call['function']}")
    print(f"Args: {fn_call['arguments']}")
```

---

## 🏗️ Architecture Overview

### Phase 1: Multi-Page Architecture

**Before**: Single `app.py` with 3 tabs (221 lines)
**After**:
- Landing page (`app.py` - 208 lines)
- 4 dedicated page files (`pages/` - 1,280+ lines)
- 8 reusable components (`components/` - 1,198 lines)

**Benefits**:
- Separation of concerns
- Improved maintainability
- Better UX
- Reusable components

### Phase 2: Enhanced Database Management

**golf_db.py** expanded from 233 → 866 lines (+633, +271%)

**New Database Tables**:
```sql
shots_archive    -- Deleted shots for recovery
change_log       -- Audit trail for all modifications
```

**New Functions** (13 total):
- Session operations (delete, merge, split, rename)
- Bulk editing (metadata update, recalculate, rename clubs)
- Data quality (outliers, validation, deduplication)
- Audit trail (restore, change log, archived shots)

### Phase 3: Advanced Visualizations

**New Visualization Components** (4 modules, 599 lines):
- Heatmap Chart (impact location visualization)
- Trend Chart (performance tracking with regression)
- Radar Chart (multi-metric club comparison)
- Export Tools (CSV/Excel/text export)

### Cloud-Native AI Coach (This Branch)

**New AI Integration** (840+ lines):
- gemini_coach.py (600+ lines) - Gemini 3.0 integration
- pages/4_🤖_AI_Coach.py (240+ lines) - Chat interface
- 6 function calling tools for data access
- Multi-model support (Flash/Pro)
- Conversation history management

### Scraper Automation Module (NEW)

**Automation System** (4,400+ lines):
- Browser automation with Playwright
- Cookie persistence for session reuse
- Historical backfill with rate limiting
- Club name normalization
- Automatic session tagging
- Slack notifications

---

## 🤖 Scraper Automation

### Overview

The automation module provides hands-free data import from Uneekor:

1. **Browser Automation**: Playwright-based portal navigation
2. **Session Discovery**: Find and track sessions automatically
3. **Deduplication**: Never import the same data twice
4. **Historical Backfill**: Import past sessions with rate limiting
5. **Naming Conventions**: Standardize club names and session labels
6. **Notifications**: Slack alerts for import events

### Quick Start

```bash
# 1. Install Playwright browser
pip install -r requirements.txt
playwright install chromium

# 2. First-time login (saves cookies)
python automation_runner.py login

# 3. Discover sessions
python automation_runner.py discover --headless

# 4. Run historical backfill
python automation_runner.py backfill --start 2025-01-01
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `login` | Interactive login to save cookies |
| `discover` | Find sessions from Uneekor portal |
| `backfill` | Import historical sessions |
| `status` | Show automation status |
| `notify` | Test Slack notification |
| `normalize` | Test club name normalization |

### Rate Limiting

The system uses conservative rate limits to avoid being blocked:

- **Default**: 6 requests/minute (one every 10 seconds)
- **Backfill**: 10 requests/minute
- **Jitter**: Random delays for natural patterns

```python
# Rate limit estimation
# 100 sessions × 10 seconds/session = ~17 minutes
limiter.estimate_time_for_requests(100)  # Returns ~1000 seconds
```

### Club Name Normalization

Standardizes club names from various Uneekor formats:

| Input | Normalized |
|-------|------------|
| `7i`, `7 iron`, `Iron 7` | `7 Iron` |
| `DR`, `driver`, `1W` | `Driver` |
| `pw`, `pitching wedge` | `PW` |
| `56 deg`, `sand wedge` | `SW` |

### Session Naming

Auto-generated session names based on type:

| Type | Pattern | Example |
|------|---------|---------|
| Practice | `Practice - {date}` | Practice - Jan 25, 2026 |
| Drill | `Drill - {focus} - {date}` | Drill - Driver Consistency - Jan 25, 2026 |
| Round | `{course} Round - {date}` | Pebble Beach Round - Jan 25, 2026 |
| Warmup | `Warmup - {date}` | Warmup - Jan 25, 2026 |

### Auto-Tagging Rules

Sessions are automatically tagged based on characteristics:

- **Driver Focus**: Single-club driver sessions
- **Short Game**: Wedge-only sessions
- **Full Bag**: 10+ clubs used
- **High Volume**: 100+ shots
- **Warmup**: <10 shots

### Slack Notifications

Configure Slack for import alerts:

```bash
# .env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Test notification:
```bash
python automation_runner.py notify "Test message"
```

### Database Tables

The automation module adds tracking tables:

```sql
sessions_discovered    -- Track discovered sessions and import status
automation_runs        -- Log automation run history
backfill_runs          -- Track backfill progress and checkpoints
```

### Code Example

```python
from automation import (
    SessionDiscovery,
    normalize_club,
    get_notifier,
)

# Discover sessions
discovery = SessionDiscovery()
result = await discovery.discover_sessions(headless=True)
print(f"Found {result.new_sessions} new sessions")

# Normalize club name
normalized = normalize_club("7i")  # Returns "7 Iron"

# Send notification
await get_notifier().send("Import complete!", level='info')
```

---

## 🗄️ Database Architecture

### Tables

**shots** (Main data table):
- 30+ fields per shot
- Includes ball flight, club data, impact location
- Session-based organization

**shots_archive** (Deleted shots):
- Soft delete for recovery
- 4 fields: id, shot_id, session_id, deleted_at

**change_log** (Audit trail):
- All modifications tracked
- 6 fields: id, timestamp, operation, table_name, record_id, details

### Hybrid Sync Pattern

All write operations follow this pattern:

```python
def operation():
    # 1. Local SQLite (always)
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        # ... execute ...
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")

    # 2. Cloud Supabase (if configured)
    if supabase:
        try:
            # ... execute same operation ...
        except Exception as e:
            print(f"Supabase Error: {e}")
```

**Benefits**:
- Works offline (local-first)
- Cloud backup when available
- No data loss if cloud is down

---

## 📊 Dashboard (5 Tabs)

### Tab 1: Performance Overview
- KPI metrics row
- Carry distance box plot
- Shot dispersion scatter
- Multi-metric radar chart

### Tab 2: Impact Analysis
- Impact location heatmap
- Sweet spot overlay
- Average impact marker
- Consistency statistics

### Tab 3: Trends Over Time
- Global trends across sessions
- Linear regression with improvement annotation
- Club-specific filtering
- 6 metrics available

### Tab 4: Shot Viewer
- Interactive shot table
- Shot detail panel
- Impact/swing image viewer

### Tab 5: Export Data
- Session export (CSV + text + Excel)
- All sessions export
- Per-club export
- Data preview

---

## 🗄️ Database Manager (6 Tabs)

### Tab 1: Edit Data
- Rename club (this session)
- Rename session (change session ID)
- Shot count by club

### Tab 2: Delete Operations
- Delete entire session
- Delete all shots for club
- Delete individual shot
- Confirmation checkboxes

### Tab 3: Session Operations
- Merge multiple sessions
- Split session (move shots)
- Multi-select interfaces

### Tab 4: Bulk Operations
- Bulk rename club (all sessions)
- Recalculate metrics (smash factor + clean data)
- Scope selector (current/all sessions)

### Tab 5: Data Quality
- Outlier detection
- Data validation
- Deduplication

### Tab 6: Audit Trail
- Change log viewer
- Restore deleted shots
- Multi-select restore

---

## 🐳 Docker & Cloud Run Deployment

### Local Docker Testing

```bash
# Build image
docker build -t golf-data-app .

# Run container
docker run -p 8080:8080 \
  -e GEMINI_API_KEY="your-key" \
  -e SUPABASE_URL="your-url" \
  -e SUPABASE_KEY="your-key" \
  golf-data-app

# Open browser
open http://localhost:8080
```

### Deploy to Cloud Run

```bash
# Deploy with secret for API key
gcloud run deploy golf-data-app \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --update-secrets GEMINI_API_KEY=gemini-api-key:latest
```

**See**: `CLOUD_RUN_DEPLOYMENT.md` for full guide

---

## 🔧 Development Guidelines

### Working with Gemini Coach

**Import Pattern**:
```python
import gemini_coach

# Get singleton instance
coach = gemini_coach.get_coach(model_type='flash')

# Chat
response = coach.chat("Your question here")
print(response['response'])

# Switch models
coach.switch_model('pro')

# Reset conversation
coach.reset_conversation()
```

**Adding New Function Tools**:

1. Add function to `gemini_coach.py`:
```python
def _your_function(self, param1: str, param2: int) -> str:
    """Your function implementation."""
    try:
        # ... your logic ...
        return json.dumps(result)
    except Exception as e:
        return json.dumps({'error': str(e)})
```

2. Register in `_register_functions()`:
```python
'your_function': self._your_function,
```

3. Add declaration in `_get_function_declarations()`:
```python
{
    'name': 'your_function',
    'description': 'What this function does',
    'parameters': {
        'type': 'object',
        'properties': {
            'param1': {
                'type': 'string',
                'description': 'Description of param1'
            }
        },
        'required': ['param1']
    }
}
```

### Working with Components

All components follow this pattern:

```python
def render_component_name(data: pd.DataFrame, **kwargs) -> None:
    """Component description."""
    st.subheader("Title")
    # ... implementation ...
```

**Import Pattern**:
```python
from components import (
    render_session_selector,
    render_metrics_row,
    render_impact_heatmap
)
```

### Database Operations

**Import Pattern**:
```python
import golf_db

# Initialize
golf_db.init_db()

# Get data
df = golf_db.get_all_shots()
sessions = golf_db.get_unique_sessions()

# Write operations (auto-syncs to Supabase if configured)
golf_db.delete_session(session_id, archive=True)
golf_db.merge_sessions(session_ids, new_session_id)
```

---

## 🧪 Testing

### Syntax Validation

```bash
python -m py_compile app.py golf_db.py gemini_coach.py components/*.py pages/*.py
```

### Run Specific Page

```bash
streamlit run pages/4_🤖_AI_Coach.py
```

### Test Gemini Coach

```python
import os
os.environ['GEMINI_API_KEY'] = 'your_key'

import gemini_coach

coach = gemini_coach.get_coach()
response = coach.chat("What's in my database?")
print(response['response'])
print(f"Function calls: {len(response['function_calls'])}")
```

---

## 📦 Dependencies

### Core
```
streamlit               # Web UI framework
pandas                  # Data manipulation
plotly, plotly-express  # Interactive visualizations
numpy                   # Numerical computations
```

### Database & API
```
psycopg2-binary        # PostgreSQL adapter
supabase               # Cloud database client
requests               # HTTP requests
python-dotenv          # Environment variables
```

### AI
```
google-generativeai    # Gemini 3.0 API
anthropic              # Claude AI (optional)
```

### Export & Scraping
```
openpyxl               # Excel file handling
selenium               # Web automation (legacy)
webdriver-manager      # Browser driver (legacy)
```

### Automation
```
playwright             # Browser automation for scraper
cryptography           # Cookie encryption
```

**Total**: 16 dependencies

---

## 🆚 Comparison: Cloud-Native vs Local ML

| Feature | production-no-ml (This Branch) | Main Branch |
|---------|-------------------------------|-------------|
| **AI Model** | Gemini 3.0 (cloud) | XGBoost + scikit-learn (local) |
| **Training Required** | ❌ No | ✅ Yes (50+ shots) |
| **Model Files** | ❌ None | ✅ .pkl files |
| **Dependencies** | 14 packages | 18+ packages |
| **Memory Footprint** | Low (~500MB) | Higher (~1.5GB with ML) |
| **Cold Start** | Fast (<5s) | Slower (~10s to load models) |
| **Accuracy** | Gemini reasoning | Trained on user data |
| **Internet Required** | ✅ Yes (for AI) | ❌ No (models local) |
| **Cost** | $0.50/1M tokens | Free (local compute) |
| **Coaching Style** | Conversational AI | Data-driven predictions |
| **Function Calling** | ✅ 6 tools | ❌ N/A |
| **Multi-turn Chat** | ✅ Yes | ❌ N/A |
| **Cloud Run Ready** | ✅ Yes | ⚠️ Needs persistent storage |

**When to Use This Branch**:
- ✅ Production deployments on Cloud Run
- ✅ Conversational coaching experience
- ✅ No model training overhead
- ✅ Lower resource requirements
- ✅ Serverless architecture

**When to Use Main Branch**:
- ✅ Offline-first requirements
- ✅ Data-driven predictions
- ✅ No API costs
- ✅ Full control over model training
- ✅ Custom ML experimentation

---

## 🎓 Common Workflows

### After Practice Session

```bash
# 1. Import data
Open app → Data Import page → Paste Uneekor URL → Run Import

# 2. View analytics
Dashboard page → Impact Analysis tab → Check strike pattern

# 3. Get AI insights
AI Coach page → Ask "What should I work on?" → Review recommendations

# 4. Export for coach
Dashboard page → Export Data tab → Download CSV + summary
```

### Using AI Coach Effectively

```bash
# 1. Start with general question
"What's my current performance level?"

# 2. Ask follow-up questions
"How has my consistency improved?"

# 3. Get specific club analysis
"Show me my driver performance trends"

# 4. Request actionable advice
"What should I focus on in my next practice session?"

# 5. Check data quality
"Are there any outliers in my recent session?"
```

---

## 🚨 Important Notes

### AI Coach Best Practices

- **Be specific**: Ask about specific clubs, sessions, or metrics
- **Provide context**: Mention what you're working on
- **Follow up**: Gemini remembers conversation history
- **Check function calls**: See what data was accessed (transparency)
- **Reset when needed**: Clear conversation if it gets off track
- **Use Flash for speed**: Switch to Pro only for complex multi-step analysis

### API Key Security

- **NEVER commit** `.env` file with API keys
- **Use Cloud Run secrets** for production deployments
- **Rotate keys** periodically
- **Monitor usage** at https://aistudio.google.com

### Database Integrity

- All write operations sync to SQLite + Supabase
- Deletions are archived for recovery
- Change log tracks all modifications
- Never hard-code SQL without parameterization

### Performance

- Gemini API calls: <2s for simple queries
- Function calling adds ~1s per tool invocation
- Large data queries: Cache results in session state
- Export: In-memory only (no disk I/O on server)

---

## 📖 Key Files & Line Counts

| File | Lines | Purpose |
|------|-------|---------|
| **app.py** | 208 | Landing page with AI Coach nav |
| **golf_db.py** | 866 | Database layer |
| **golf_scraper.py** | ~300 | Uneekor API client |
| **gemini_coach.py** | 600+ | Gemini 3.0 AI Coach |
| **automation_runner.py** | 350+ | Automation CLI (NEW) |
| **automation/** (8 files) | 4,400+ | Scraper automation (NEW) |
| **pages/1_📥_Data_Import.py** | 131 | Import UI |
| **pages/2_📊_Dashboard.py** | 435 | Analytics (5 tabs) |
| **pages/3_🗄️_Database_Manager.py** | 475 | CRUD (6 tabs) |
| **pages/4_🤖_AI_Coach.py** | 240+ | Chat interface |
| **components/** (8 files) | 1,198 | Reusable UI |
| **Total** | ~8,900+ | Core app + automation |

---

## 📝 Changelog (This Branch)

### 2026-01-25: Scraper Automation Module
- Created automation/ module (4,400+ lines)
- Playwright browser automation with cookie persistence
- Session discovery and deduplication system
- Historical backfill with rate limiting and checkpointing
- Club name normalization (e.g., "7i" -> "7 Iron")
- Automatic session naming and tagging
- Slack notification integration
- CLI runner (automation_runner.py)
- Updated Dockerfile for Playwright support
- Added cryptography dependency for cookie encryption

### 2025-12-28: Cloud-Native AI Coach Implementation
- Created gemini_coach.py (600+ lines) - Gemini 3.0 integration
- Created pages/4_🤖_AI_Coach.py (240+ lines) - Chat interface
- Added 6 function calling tools for data access
- Updated app.py with AI Coach navigation
- Documented cloud-native architecture

### 2025-12-28: Branch Created from commit 1329ae4
- Includes: Phases 1-3 + Cloud Run containerization
- Excludes: Phase 4 (local ML), Phase 5 (local AI Coach GUI)
- Base commit: "feat: Add Google Cloud Run containerization support"

---

**Last Updated**: 2026-01-25
**Branch**: `production-no-ml`
**Status**: Production-ready with automated scraping and AI coaching
**Deployment**: Ready for Google Cloud Run (includes Playwright)
