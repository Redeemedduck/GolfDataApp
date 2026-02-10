# Technology Stack

**Analysis Date:** 2026-02-09

## Languages

**Primary:**
- Python 3.10+ - All application code, automation, ML models
  - Used in: `app.py`, `golf_db.py`, `automation/`, `ml/`, `services/`, `pages/`
  - CI validates: Python 3.10, 3.11, 3.12

**Secondary:**
- SQL (SQLite/Supabase PostgreSQL) - Data persistence

## Runtime

**Environment:**
- Python 3.10 minimum (3.11, 3.12 tested and supported in CI)
- Virtual environment recommended (venv at `./venv/`)

**Package Manager:**
- pip (Python package manager)
- Lockfile: `requirements.txt` (no lock file; pins major versions)

## Frameworks

**Core UI:**
- Streamlit 1.x - Web application framework for analytics dashboard
  - Landing page: `app.py`
  - Pages: `pages/1_Data_Import.py`, `pages/2_Dashboard.py`, `pages/3_Database_Manager.py`, `pages/4_AI_Coach.py`
  - Components: Reusable UI in `components/` (all follow `render_*()` pattern)

**Data & Analysis:**
- pandas - DataFrames, data manipulation, CSV/Excel handling
- numpy - Numerical computations
- plotly / plotly-express - Interactive visualizations and charts

**Testing:**
- unittest - Python standard library test runner (primary)
  - Compatible with pytest as secondary runner
  - Test discovery: `tests/` directory with `conftest.py` fixtures

**Build/Dev:**
- GitHub Actions (CI/CD) - `.github/workflows/ci.yml`
  - Syntax validation: `py_compile`
  - Test execution: `unittest discover`
  - ML validation: Module import checks

## Key Dependencies

**Critical:**
- `google-generativeai` (v0.x) - Gemini 3.0 API client for cloud-based AI coaching
  - Used in: `gemini_coach.py`
  - Environment: `GEMINI_API_KEY`

- `supabase` (v1.x) - PostgreSQL cloud database client (soft dependency)
  - Used in: `golf_db.py` for optional cloud sync
  - Environment: `SUPABASE_URL`, `SUPABASE_KEY`
  - Fallback: Works offline with local SQLite if credentials missing

- `playwright` - Browser automation for Uneekor portal scraping
  - Used in: `automation/browser_client.py`, `automation/session_discovery.py`
  - Requires: `playwright install chromium` (first-time setup)
  - Role: Headless browser control with rate limiting

**Machine Learning:**
- `scikit-learn` (>=1.3.0) - Classification, distance prediction, anomaly detection
  - Used in: `ml/train_models.py`, `ml/classifiers.py`, `ml/anomaly_detection.py`
  - Lazy-loaded: ML features degrade gracefully if not installed

- `xgboost` (>=2.0.0) - Gradient boosting for distance prediction
  - Used in: `ml/train_models.py`
  - Optional: Falls back to linear regression if unavailable

- `joblib` (>=1.3.0) - ML model serialization and caching
  - Used in: `ml/train_models.py` (model persistence)

**Data Format Support:**
- `openpyxl` - Excel (.xlsx) file I/O
  - Used in: `pages/2_Dashboard.py` (export functionality)

**Infrastructure:**
- `requests` - HTTP client for Slack webhooks and API calls
  - Used in: `automation/notifications.py`
  - Async-compatible wrapper in: `asyncio.run_in_executor()`

- `cryptography` - Secure credential storage for Uneekor portal cookies
  - Used in: `automation/credential_manager.py`
  - Encrypts: Authentication tokens for Playwright automation

- `python-dotenv` - Environment variable loading
  - Used throughout: `.env` file configuration
  - Config: `.env` (not committed, use `.env.example`)

**Legacy/Secondary:**
- `selenium` + `webdriver-manager` - Legacy scraper (pre-Playwright)
  - Used in: `golf_scraper.py` (superseded by Playwright)
  - Status: Functional but no longer primary automation method

- `anthropic` - Claude API (installed but not currently used)
  - Listed in requirements but no active usage detected
  - Available for future integration

## Configuration

**Environment:**
- Load method: `python-dotenv` reads from `.env` file
- Detection: `os.getenv()` throughout codebase
- Cloud environment: Detects `K_SERVICE` env var for Cloud Run deployment

**Runtime Modes:**
- **Local development**: SQLite default, optional Supabase sync
- **Cloud (Cloud Run)**: Detects `K_SERVICE` env var, forces Supabase reads
- **Read modes**: `"auto"` (SQLite first), `"sqlite"` (local only), `"supabase"` (cloud only)
  - Set via: `golf_db.set_read_mode(mode)`

**Database Configuration:**
- SQLite: `golf_stats.db` in project root (WAL mode enabled)
- Supabase: Optional - reads `SUPABASE_URL` and `SUPABASE_KEY`

## Platform Requirements

**Development:**
- macOS or Linux (Windows possible but untested)
- Python 3.10+ (virtual environment recommended)
- Playwright dependencies: Chromium browser (downloaded on first `playwright install chromium`)
- Uneekor portal credentials for automation features (optional)

**Production:**
- **Deployment target**: Google Cloud Run (detects via `K_SERVICE` env var)
- **Containerization**: Docker capable (Cloud Run compatible)
- **Database**: SQLite locally or Supabase in cloud
- **Rate limiting**: Token bucket (6 requests/min default for Uneekor portal)

## Build & Deployment

**Local development:**
```bash
pip install -r requirements.txt
streamlit run app.py
```

**CI/CD:**
- GitHub Actions workflow: `.github/workflows/ci.yml`
- On push to `main` or `develop`, or PR to `main`:
  1. Lint: `py_compile` syntax check (Python 3.10, 3.11, 3.12)
  2. Test: `unittest discover` from `tests/`
  3. ML Validation: Module imports and instantiation checks

**Automation CLI:**
```bash
python automation_runner.py <command>  # Entry point in `automation_runner.py`
```

---

*Stack analysis: 2026-02-09*
