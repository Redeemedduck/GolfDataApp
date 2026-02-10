# Codebase Structure

**Analysis Date:** 2026-02-09

## Directory Layout

```
GolfDataApp/
├── app.py                          # Streamlit landing page and navigation
├── golf_db.py                      # Database abstraction layer (SQLite + Supabase)
├── golf_scraper.py                 # Shot data extraction from Uneekor API
├── local_coach.py                  # Offline AI coach (template + ML-based)
├── gemini_coach.py                 # Cloud AI coach (Gemini API with function calling)
├── automation_runner.py             # CLI for automation, discovery, backfill
├── observability.py                 # Structured event logging
├── exceptions.py                    # Exception hierarchy with context dicts
│
├── automation/                      # Uneekor portal automation
│   ├── __init__.py
│   ├── backfill_runner.py          # Orchestrate rate-limited historical imports
│   ├── session_discovery.py         # Detect sessions on Uneekor portal (Playwright)
│   ├── browser_client.py            # Playwright lifecycle, login, cookie persistence
│   ├── credential_manager.py        # AES-256 encrypted cookie storage
│   ├── uneekor_portal.py            # Navigation logic for Uneekor portal
│   ├── rate_limiter.py              # Token bucket rate limiting
│   ├── naming_conventions.py        # Club name normalization, auto-tagging
│   ├── notifications.py             # Slack webhook notifications
│   └── inventory/                   # Session discovery state tables
│
├── components/                      # Reusable Streamlit UI components
│   ├── __init__.py                  # Barrel export (all render_* functions)
│   ├── session_selector.py          # Dropdown for session selection
│   ├── metrics_card.py              # KPI cards (avg carry, etc.)
│   ├── shot_table.py                # Interactive shot data table
│   ├── heatmap_chart.py             # Impact location heatmaps
│   ├── trend_chart.py               # Time-series performance charts
│   ├── radar_chart.py               # Radar chart for club comparison
│   └── export_tools.py              # CSV/Excel export, summary generation
│
├── pages/                           # Streamlit multi-page app
│   ├── 1_📥_Data_Import.py         # Paste URL, import shots from Uneekor
│   ├── 2_📊_Dashboard.py            # Analytics (Overview, Impact, Trends, Shots, Export tabs)
│   ├── 3_🗄️_Database_Manager.py    # CRUD, tagging, session operations
│   └── 4_🤖_AI_Coach.py            # Chat interface with provider dropdown
│
├── services/                        # Service abstractions
│   └── ai/
│       ├── __init__.py
│       ├── registry.py              # Provider registry (decorator-based)
│       └── providers/
│           ├── local_provider.py    # LocalCoach wrapper for registry
│           └── gemini_provider.py   # GeminiCoach wrapper for registry
│
├── ml/                              # Optional ML module (lazy-loaded)
│   ├── __init__.py                  # __getattr__ for lazy loading
│   ├── train_models.py              # DistancePredictor (XGBoost)
│   ├── classifiers.py               # ShotShapeClassifier (D-plane theory)
│   └── anomaly_detection.py         # SwingFlawDetector (Isolation Forest)
│
├── utils/                           # Utility functions
│   ├── __init__.py
│   └── logging_config.py            # Structured logging configuration
│
├── tests/                           # Test suite
│   ├── conftest.py                  # Shared fixtures (temp_db, golf_db_instance, etc.)
│   ├── test_golf_db.py              # golf_db CRUD tests
│   ├── test_scraper.py              # golf_scraper extraction tests
│   ├── unit/                        # Isolated unit tests
│   │   ├── test_local_coach.py
│   │   ├── test_ml_models.py
│   │   ├── test_date_parsing.py
│   │   ├── test_exceptions.py
│   │   ├── test_credential_manager.py
│   │   ├── test_naming_conventions.py
│   │   └── test_observability.py
│   ├── integration/                 # Cross-module integration tests
│   │   ├── test_automation_flow.py
│   │   └── test_date_reclassification.py
│   └── e2e/                         # End-to-end user flow tests
│       ├── test_coach_flow.py
│       └── test_data_flow.py
│
├── docs/                            # Documentation
│   ├── archive/                     # Old/superseded docs
│   ├── plans/                       # Implementation plans and roadmaps
│   └── tutorials/                   # How-to guides
│
├── scripts/                         # Standalone utilities
│   ├── migrate_to_supabase.py      # One-time migration script
│   └── mcp_supabase_config.py      # MCP server configuration
│
├── logs/                            # Event logs (auto-created)
│   ├── import_runs.jsonl            # Import operation events
│   └── sync_runs.jsonl              # Sync operation events
│
├── models/                          # Trained ML models (auto-created)
│
├── mcp/                             # MCP server code (unused in core app)
│
├── golf_stats.db                    # SQLite database (local, checked in .gitignore)
├── golf_stats.db-wal                # SQLite WAL file
├── golf_stats.db-shm                # SQLite shared memory
│
├── .planning/                       # GSD planning documents
│   └── codebase/                    # This location (ARCHITECTURE.md, STRUCTURE.md, etc.)
│
├── .streamlit/                      # Streamlit config (theme, secrets)
├── .github/workflows/               # CI/CD
│   └── ci.yml                       # Lint + test on push
│
├── .env.example                     # Template for environment variables
├── CLAUDE.md                        # Project instructions
├── README.md                        # Main documentation
├── SETUP_GUIDE.md                   # Installation and setup
├── IMPROVEMENT_ROADMAP.md           # Feature roadmap
└── PIPELINE_COMPLETE.md             # Data pipeline documentation
```

## Directory Purposes

**automation/:**
- Purpose: Uneekor portal scraping, session discovery, backfill orchestration
- Contains: Browser automation (Playwright), rate limiting, state management, cookie encryption
- Key files: `session_discovery.py` (state machine), `backfill_runner.py` (orchestrator), `uneekor_portal.py` (navigation)

**components/:**
- Purpose: Reusable Streamlit UI building blocks
- Contains: Charts (heatmap, trend, radar), tables, export functions
- Pattern: All functions are `render_*(data: pd.DataFrame, **kwargs) -> None` (stateless, side-effect only)

**pages/:**
- Purpose: Streamlit multi-page application routes
- Contains: Data import, analytics dashboard, database management, AI coach interface
- Key distinction: Page 1 and 3 modify data (import, delete); Page 2 and 4 read data (visualize, chat)

**services/ai/:**
- Purpose: Pluggable AI backend system
- Contains: Registry with self-registration via decorators, local and cloud provider wrappers
- Key file: `registry.py` (central dispatch point)

**ml/:**
- Purpose: Optional machine learning features
- Contains: Distance prediction (XGBoost), shot shape classification (D-plane), anomaly detection
- Design: Lazy-loaded via `__getattr__` in `__init__.py` — imports succeed even if XGBoost unavailable

**tests/:**
- Purpose: Test coverage (unit, integration, e2e)
- Structure: Mirror of main codebase + conftest.py with shared fixtures
- Key fixture: `populated_golf_db` (initialized with 10 sample shots)

**scripts/:**
- Purpose: One-time or utility scripts (not core app logic)
- Examples: Supabase migration, MCP configuration builder

**docs/:**
- Purpose: User and developer documentation
- Structure: Archive (old), plans (implementation), tutorials (how-tos)

## Key File Locations

**Entry Points:**
- `app.py`: Main Streamlit app (landing page)
- `automation_runner.py`: CLI entry for automation
- `.github/workflows/ci.yml`: Continuous integration

**Configuration:**
- `.streamlit/config.toml`: Streamlit theme/secrets
- `.env.example`: Environment variable template
- `CLAUDE.md`: Project guidelines
- `SETUP_GUIDE.md`: Installation steps

**Core Logic:**
- `golf_db.py`: Database abstraction (500+ lines) — read/write modes, migrations, soft deletes
- `local_coach.py`: Offline AI coach (650+ lines) — intent detection, rule-based insights
- `automation/session_discovery.py`: Session discovery state machine (950+ lines) — Playwright orchestration
- `automation/backfill_runner.py`: Backfill orchestrator (450+ lines) — rate limiting, checkpointing

**Testing:**
- `tests/conftest.py`: Shared fixtures (temp DB, sample data)
- `tests/test_golf_db.py`: Database layer tests
- `tests/unit/test_ml_models.py`: ML model tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `golf_db.py`, `local_coach.py`)
- Streamlit pages: `N_emoji_Page_Name.py` (e.g., `1_📥_Data_Import.py`, `4_🤖_AI_Coach.py`)
- Components: `descriptor_chart.py` or `operation_tools.py` (e.g., `heatmap_chart.py`, `export_tools.py`)

**Directories:**
- Package dirs: `lowercase_with_underscores` (e.g., `automation`, `components`, `services`)
- Sections: Functional grouping (e.g., `automation` for all scraping, `services/ai` for provider registry)

**Functions/Classes:**
- Classes: `PascalCase` (e.g., `LocalCoach`, `GeminiCoach`, `SessionDiscovery`)
- Functions: `snake_case` (e.g., `run_scraper()`, `save_shot()`, `get_provider()`)
- Streamlit components: `render_*(...)` pattern (e.g., `render_shot_table()`, `render_impact_heatmap()`)
- Intent patterns: `{entity}_{action}` (e.g., `driver_stats`, `swing_issue`, `gapping`)

**Database:**
- Tables: `lowercase_with_underscores` (e.g., `shots`, `sessions_discovered`, `backfill_runs`)
- Columns: `snake_case` (e.g., `shot_id`, `session_date`, `date_added`)
- Indices: `idx_{table}_{column}` (e.g., `idx_shots_session_id`, `idx_shots_session_date`)

## Where to Add New Code

**New Feature (e.g., "shot dispersion heatmap"):**
- Primary code: `components/dispersion_heatmap.py` (render function)
- Usage: Import in `pages/2_📊_Dashboard.py` and call `render_dispersion_heatmap(data)`
- Tests: `tests/unit/test_dispersion_heatmap.py`

**New AI Provider (e.g., "Claude provider"):**
- Implementation: `services/ai/providers/claude_provider.py`
- Register: Add `@register_provider` decorator to provider class
- Test: `tests/unit/test_claude_provider.py`
- Usage: Dropdown on `pages/4_🤖_AI_Coach.py` auto-populated via `services.ai.list_providers()`

**New ML Model (e.g., "putting stroke classification"):**
- Implementation: `ml/putting_classifier.py`
- Lazy-load: Export class in `ml/__init__.py` via `__getattr__`
- Usage: `from ml import PuttingClassifier` (fails gracefully if sklearn unavailable)
- Test: `tests/unit/test_putting_classifier.py`

**New Automation Command (e.g., "export-to-csv"):**
- Implementation: Add `def cmd_export_csv(args)` in `automation_runner.py`
- Subparser: Register in `main()` via `subparsers.add_parser('export-csv')`
- Logic: Call `golf_db.get_session_data()` and `components.export_to_csv()`

**Database Schema Change (e.g., add "wind_speed" to shots):**
- Migration: Edit `golf_db.init_db()` → add to `required_columns` dict
- Backwards compatible: Column added via `ALTER TABLE` on next startup
- Scraper: Update `golf_scraper.py` extraction logic
- Tests: Add sample data with new field to `conftest.py`

**Utilities (shared helpers):**
- Location: `utils/` for app-wide utilities (e.g., logging config)
- Or: Module-specific helpers in the relevant package (e.g., `automation/rate_limiter.py` only used by backfill)

## Special Directories

**logs/:**
- Purpose: Structured event logging (JSON lines format)
- Generated: Yes (auto-created by `observability.append_event()`)
- Committed: No (in .gitignore)
- Files: `import_runs.jsonl`, `sync_runs.jsonl`

**models/:**
- Purpose: Trained ML model artifacts (serialized format)
- Generated: Yes (created by `ml.train_models.py` if ML data available)
- Committed: No (in .gitignore)
- Pattern: Model files named by type (e.g., `distance_predictor`, `shot_classifier`)

**.planning/codebase/:**
- Purpose: GSD planning and analysis documents
- Generated: Yes (by codebase mapper and planners)
- Committed: Yes (tracks architectural decisions)
- Files: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, INTEGRATIONS.md, CONCERNS.md

**.streamlit/:**
- Purpose: Streamlit configuration (theme, sidebar, secrets)
- Files: `config.toml`, `secrets.toml` (not in git)
- Editable: Yes, persisted across runs

---

*Structure analysis: 2026-02-09*
