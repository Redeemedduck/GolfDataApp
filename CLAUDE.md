# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Run the Streamlit app
streamlit run app.py

# Run all tests (unittest runner; pytest also works)
python -m unittest discover -s tests

# Run agent tests only
python -m unittest tests.unit.test_agent_tools tests.unit.test_agent_core tests.unit.test_claude_provider

# Run a single test file
python -m unittest tests.test_golf_db
python -m unittest tests.unit.test_ml_models
python -m unittest tests.unit.test_local_coach
python -m unittest tests.unit.test_date_parsing
python -m unittest tests.unit.test_exceptions
python -m unittest tests.unit.test_credential_manager
python -m unittest tests.unit.test_naming_conventions
python -m unittest tests.unit.test_rate_limiter_config
python -m unittest tests.unit.test_data_foundation
python -m unittest tests.integration.test_automation_flow
python -m unittest tests.integration.test_date_reclassification
python -m unittest tests.integration.test_reimport
python -m unittest tests.unit.test_bag_config
python -m unittest tests.unit.test_date_range_filter
python -m unittest tests.unit.test_shot_navigator
python -m unittest tests.unit.test_trajectory_view
python -m unittest tests.unit.test_goal_tracker
python -m unittest tests.unit.test_data_quality
python -m unittest tests.unit.test_time_window

# Syntax check all Python files (this is what CI runs as "lint")
python -m py_compile app.py golf_db.py local_coach.py exceptions.py
python -m py_compile automation/*.py ml/*.py utils/*.py agent/*.py
python -m py_compile services/ai/*.py services/ai/providers/*.py services/analytics/*.py services/data_quality.py services/time_window.py
python -m py_compile components/*.py
for f in pages/*.py; do python -m py_compile "$f"; done

# Train ML models (requires shot data in database)
python -m ml.train_models

# Automation CLI (Playwright scraper for Uneekor portal)
playwright install chromium              # First-time only
python automation_runner.py login        # Interactive login, saves cookies
python automation_runner.py discover --headless
python automation_runner.py backfill --start 2025-01-01
python automation_runner.py backfill --start 2025-01-01 --clubs "Driver,7 Iron"
python automation_runner.py backfill --start 2025-01-01 --dry-run
python automation_runner.py backfill --retry-failed

# Session date reclassification
python automation_runner.py reclassify-dates --status
python automation_runner.py reclassify-dates --from-listing   # Extract from listing page DOM
python automation_runner.py reclassify-dates --from-listing --auto-backfill  # Extract + propagate
python automation_runner.py reclassify-dates --backfill
python automation_runner.py reclassify-dates --scrape --max 10
python automation_runner.py reclassify-dates --manual 43285 2026-01-15

# Clean re-import (wipe all shots, re-fetch from Uneekor API)
python automation_runner.py reimport-all --dry-run    # Preview only
python automation_runner.py reimport-all              # Full reimport

# Database sync (SQLite <-> Supabase)
python automation_runner.py sync-database --dry-run
python automation_runner.py sync-database
python automation_runner.py sync-database --direction from-supabase

# Golf Agent (Claude Agent SDK)
op run --env-file=.env.template -- python3 -m agent.cli              # Interactive chat
op run --env-file=.env.template -- python3 -m agent.cli --single "How's my driver?"  # One-shot query
```

## Architecture Overview

### Data Flow

```
Uneekor Portal --> automation/ --> golf_db.py --> SQLite + Supabase
                                       |
                                       v
                               Streamlit Pages
                                       |
                             ┌─────────┴─────────┐
                             v                   v
                     local_coach.py      gemini_coach.py      agent/
                     (Offline ML)        (Cloud AI)           (Agent SDK)
```

### Shared Data Layer: `golf-data-core` Package

The core data layer lives in a separate package at `~/Documents/GitHub/golf-data-core/` (`pip install -e`). GolfDataApp uses backward-compatible shims that re-export from the package — **all existing imports work unchanged**.

| Package Module | Purpose |
|----------------|---------|
| `golf_data.db` | Database layer: SQLite + Supabase, `configure()` for path/credentials/normalization |
| `golf_data.clubs` | Club normalization: `ClubNameNormalizer`, `SessionNamer`, `map_uneekor_club()` |
| `golf_data.exceptions` | Exception hierarchy: `GolfDataAppError` base with context dicts |
| `golf_data.filters.quality` | Two-layer outlier filtering: hard caps + z-score |
| `golf_data.filters.time_window` | Time window filtering (3mo/6mo/1yr/all) |
| `golf_data.analytics.*` | executive_summary, session_grades, progress_tracker, practice_planner |
| `golf_data.config` | `BagConfig` class with multi-path `my_bag.json` discovery |
| `golf_data.utils.*` | bag_config, big3_constants, date_helpers |

**Shim pattern** — GolfDataApp modules delegate to the package:
```python
# golf_db.py — module proxy that forwards attribute access to golf_data.db
import golf_data.db as _real_db
from automation.naming_conventions import normalize_with_context
_real_db.configure(sqlite_db_path=..., normalize_fn=normalize_with_context)

# services/data_quality.py — star-import shim
from golf_data.filters.quality import *
```

**Second app usage:**
```python
from golf_data import db
db.configure(sqlite_db_path='/path/to/golf_stats.db')
db.init_db()
shots = db.get_all_shots()
```

### Core Modules

| Module | Purpose |
|--------|---------|
| `golf_db.py` | **Shim** → delegates to `golf_data.db` (configures SQLite path + normalization) |
| `exceptions.py` | **Shim** → re-exports from `golf_data.exceptions` |
| `local_coach.py` | Local AI coach: intent detection, template responses, ML predictions |
| `gemini_coach.py` | Gemini AI Coach with function calling |
| `automation/` | Playwright-based scraper: rate limiting, checkpointing, cookie persistence |
| `ml/` | ML models: XGBoost distance prediction, shot shape classification, anomaly detection |
| `services/ai/` | AI provider registry (decorator pattern for pluggable backends) |
| `services/analytics/` | **Shims** → re-export from `golf_data.analytics.*` |
| `services/data_quality.py` | **Shim** → re-exports from `golf_data.filters.quality` |
| `services/time_window.py` | **Shim** → re-exports from `golf_data.filters.time_window` |
| `components/` | Reusable Streamlit UI components (all follow `render_*()` pattern) |
| `agent/` | Claude Agent SDK golf coach: CLI (`python3 -m agent`), Streamlit provider, 8 MCP tools wrapping `golf_db` |
| `golf_scraper.py` | API-based scraper: uses Uneekor API `club_name` + `client_created_date` fields, maps via `map_uneekor_club()` |

### Hybrid Database Pattern

The database layer lives in `golf_data.db` (from the `golf-data-core` package). GolfDataApp configures it at import time via `golf_db.py` shim:
```python
golf_data.db.configure(
    sqlite_db_path='golf_stats.db',
    normalize_fn=normalize_with_context,  # Two-tier: ClubNameNormalizer + SessionContextParser
)
```

All write operations follow:
1. Write to local SQLite (always)
2. Sync to Supabase (if configured, soft dependency)
3. For deletions: archive to `shots_archive` in both SQLite and Supabase before removing

Read modes (`get_read_mode()`/`set_read_mode()`): `"auto"` (SQLite first, Supabase fallback), `"sqlite"` (local only), `"supabase"` (cloud only, for containers).

SQLite uses **WAL mode** for concurrent reads/writes. Schema migrations in `init_db()` use `PRAGMA table_info` to detect and add missing columns dynamically.

### AI Provider System

Providers self-register via `@register_provider` decorator in `services/ai/registry.py`. Each provider defines `PROVIDER_ID` and `DISPLAY_NAME` class attributes. Providers are auto-imported when `services/ai/providers/` is loaded.

```python
from services.ai import list_providers, get_provider
providers = list_providers()        # All registered ProviderSpec objects
spec = get_provider('local')        # Get by ID, returns ProviderSpec
instance = spec.provider_cls()      # Instantiate the provider
```

### ML Module

ML dependencies are **lazy-loaded** via `__getattr__` in `ml/__init__.py`. Code that uses ML gracefully degrades if XGBoost/sklearn aren't installed — rule-based fallbacks handle all cases. Key classes: `DistancePredictor`, `ShotShapeClassifier` (D-plane theory), `SwingFlawDetector` (Isolation Forest).

### Streamlit Pages

- `app.py` — Practice Journal home (2x2 hero stats, calendar strip, session cards grouped by week)
- `pages/1_📊_Dashboard.py` — Analytics (5 tabs: State of Your Game, Progress & Trends, Practice Plan, Big 3 Deep Dive, Shots) + global time window/outlier filters
- `pages/2_🏌️_Club_Profiles.py` — Per-club deep dives (hero stats, smash goal tracker, trends, Big 3, session comparison, smart radar defaults)
- `pages/3_🤖_AI_Coach.py` — Chat interface with provider selection dropdown
- `pages/4_⚙️_Settings.py` — Data Import + Database Manager (5 tabs: Data, Maintenance, Tags, Automation, Display)

Components in `components/` are stateless: `render_*(data: pd.DataFrame, **kwargs) -> None`.

Key UI components:
- `journal_card.py` / `journal_view.py` — Session cards (2 metrics + inline Big 3) + rolling week grouping
- `calendar_strip.py` — Flexbox practice frequency strip (responsive width)
- `big3_summary.py` / `big3_detail_view.py` — Impact Laws visualization (Face, Path, Strike)
- `face_path_diagram.py` — D-plane scatter (Face Angle vs Club Path)
- `direction_tendency.py` — Face/path histograms + shot shape distribution
- `club_hero.py` / `club_trends.py` — Club profile hero card + trend charts
- `date_range_filter.py` — Preset buttons (7d/30d/90d/All) + custom date range picker
- `shot_navigator.py` — Prev/next shot controls with `clamp_index()` helper
- `trajectory_view.py` — 2D side-view ball flight arc (piecewise quadratic)
- `goal_tracker.py` — Smash factor progress bar toward per-club targets
- `executive_summary.py` — Quality score gauge, Big 3 status cards, top/bottom clubs, action items
- `session_grades.py` — Session cards with A-F letter grades, trajectory indicator
- `progress_dashboard.py` — Per-club sparklines, Most Improved / Needs Attention highlights
- `practice_plan.py` — Weakness badges, drill blocks with severity colors, time budget

Shared utilities:
- `utils/date_helpers.py` — `parse_session_date()`, `format_session_date()` (used by 3 components)
- `utils/big3_constants.py` — Big 3 thresholds, colors, `face_label()`/`path_label()`/`strike_label()` (used by 2 components)
- `utils/responsive.py` — `is_compact_layout()`, `render_compact_toggle()`, `add_responsive_css()`
- `utils/bag_config.py` — `get_bag_order()`, `get_club_sort_key()`, `is_in_bag()`, `get_smash_target()`, `get_all_smash_targets()`, `get_adjacent_clubs()`, `get_uneekor_mapping()`, `get_special_categories()` (reads `my_bag.json`)
- `utils/chart_theme.py` — Unified dark Plotly theme: `themed_figure()`, `apply_theme()`, `context_color()`. Colors: `COLOR_GOOD` (green), `COLOR_FAIR` (amber), `COLOR_POOR` (red), `COLOR_NEUTRAL` (blue)

### Automation Module

Layered architecture: `automation_runner.py` CLI → `BackfillRunner` (orchestration + checkpointing) → `SessionDiscovery` (dedup + state tracking) → `PlaywrightClient` (browser lifecycle + cookies) → `UneekorPortal` (navigation).

Key behaviors:
- Token bucket rate limiting (6 req/hour default, configured via `max_sessions_per_hour`)
- Encrypted cookie persistence (`credential_manager.py`)
- Resumable backfill with `sessions_discovered` and `backfill_runs` tables
- Club name normalization via `naming_conventions.py` (e.g., "7i" → "7 Iron") + Uneekor API mapping via `map_uneekor_club()` (e.g., "WEDGE_PITCHING" → "PW")
- Exponential backoff on retries (10s → 30s → 90s)

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | For Agent SDK | Claude Agent SDK access |
| `GEMINI_API_KEY` | For AI Coach | Gemini API access |
| `SUPABASE_URL` | No | Cloud sync URL |
| `SUPABASE_KEY` | No | Cloud sync key |
| `SLACK_WEBHOOK_URL` | No | Automation alerts |
| `USE_SUPABASE_READS` | No | Set `1` to force cloud reads (containers) |
| `GOLFDATA_LOGGING` | No | Set `1` for structured logging |

## Database Schema

| Table | Purpose | Supabase Sync |
|-------|---------|---------------|
| `shots` | Main data (30+ fields per shot) | Yes — full upsert |
| `shots_archive` | Soft-deleted shots (recovery) | Yes — archived on session delete |
| `change_log` | Audit trail for modifications | No — local only |
| `tag_catalog` | Shot tag definitions | Yes — upsert/delete |
| `sessions_discovered` | Automation: discovered sessions + import status + `date_source` | Yes — service role |
| `automation_runs` | Automation: high-level run tracking | Yes — service role |
| `backfill_runs` | Automation: backfill progress checkpoints | Yes — service role |
| `sync_audit` | Tracks sync operations with timestamps, counts, errors | No — local only |
| `session_stats` | Pre-computed per-session aggregates (Big 3 metrics, carry, smash) | No — local cache |

Canonical Supabase schema: `supabase_schema.sql` (all tables, indexes, RLS policies, views).

Derived columns on `shots` table: `face_to_path` (= face_angle - club_path), `strike_distance` (= sqrt(impact_x^2 + impact_y^2)). Computed on ingest in `save_shot()`, backfilled via `backfill_derived_columns()`.

Key date distinction: `session_date` = when the practice occurred (always `YYYY-MM-DD` date-only format), `date_added` = when data was imported.

### Bag Configuration

`my_bag.json` defines 16 clubs + 2 special categories (Sim Round, Other) with canonical names, Uneekor API mapping keys, aliases, and display order. The `BagConfig` class in `golf_data.config` searches multiple paths: `$GOLF_BAG_CONFIG` → CWD/`my_bag.json` → `~/.golf/my_bag.json` → package default.

Load via `utils/bag_config.py` (shim to `golf_data.utils.bag_config`):
```python
from utils.bag_config import get_bag_order, get_club_sort_key, is_in_bag, get_uneekor_mapping
clubs = sorted(club_list, key=get_club_sort_key)  # Bag order: Driver first
mapping = get_uneekor_mapping()                    # {'DRIVER': 'Driver', 'IRON7': '7 Iron', ...}
```

## Key Conventions

- All database operations use **parameterized SQL**; `update_shot_metadata()` enforces a field allowlist (`ALLOWED_UPDATE_FIELDS`)
- Deletions are **soft deletes** — records go to `shots_archive` for recovery
- The value `99999` is a Uneekor sentinel meaning "no data" — cleaned via `clean_value()` in `golf_db.py` (returns `None`, not `0.0`). Also catches optix sentinels (`-1666.64`/`1666.55`) and extreme values (`carry >= 1000`, `club_speed >= 200`)
- Club names are normalized at import time. For API imports (reimport-all, golf_scraper): `map_uneekor_club()` (from `golf_data.clubs`) maps Uneekor `club_name` directly to canonical names. For Playwright imports: two-tier pipeline (`ClubNameNormalizer` → `SessionContextParser` fallback). Original raw values preserved in `original_club_value` column; `sidebar_label` and `uneekor_club_id` stored for traceability
- The `normalize_with_context()` function in `automation/naming_conventions.py` is the canonical entry point for Playwright-based club normalization (injected into `golf_data.db` via `configure(normalize_fn=...)`); `map_uneekor_club()` from `golf_data.clubs` is the entry point for API-based normalization
- `utils/migrate_club_data.py` — one-time migration script for existing data (`--dry-run`, `--report` modes)
- Sessions are auto-tagged based on characteristics (`AutoTagger`: Driver Focus, Short Game, etc.)
- Session display names are generated via `SessionNamer.generate_display_name()` — format: `"2026-01-25 Mixed Practice (47 shots)"`
- Session types detected by club distribution (`SessionNamer.detect_session_type()`): Driver Focus, Iron Work, Short Game, Woods Focus, Mixed Practice, Warmup
- `golf_db.batch_update_session_names()` retroactively renames all imported sessions
- Per-club smash factor targets are defined in `my_bag.json` under `smash_targets` key and accessed via `utils/bag_config.py:get_smash_target()` / `get_all_smash_targets()`
- Sidebar has navigation + global filters (time window, outlier toggle); technical controls (data source, sync status, layout, appearance) live in Settings > Display tab
- Global filters stored in `st.session_state["time_window"]` and `st.session_state["outlier_filter"]`, applied via `get_filtered_shots()` in `services/data_access.py`
- **Backfill performance tip:** Disable Supabase during bulk import (`SUPABASE_URL=""`) then batch-sync after with `sync-database`. Per-shot upserts in `add_shot()` are slow for bulk operations.

### Coding Style

- Python code uses **4-space indentation**, `snake_case` for functions/variables, `PascalCase` for classes
- Keep modules small and focused; UI-only logic goes in `pages/` or `components/`
- No formatter/linter is configured; keep diffs clean and avoid mixed line endings
- Follow **conventional commit** style: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, etc.
- PRs should include a short summary, manual test steps, and screenshots for UI changes

## Testing

Tests use `unittest` (and are also compatible with `pytest`). Shared fixtures in `tests/conftest.py` provide:

| Fixture | Purpose |
|---------|---------|
| `temp_db_path` | Temporary SQLite path (auto-cleaned) |
| `golf_db_instance` | Initialized `golf_db` module pointed at temp DB with Supabase disabled |
| `populated_golf_db` | `golf_db_instance` pre-loaded with 10 sample shots |
| `sample_shot_data` | Single shot dict with realistic Driver metrics |
| `sample_shots_batch` | 10 shots with varying carry distances |
| `ml_test_dataframe` | 100-row DataFrame with synthetic launch data (seeded) |
| `mock_rate_limiter` | Permissive rate limiter (1000 req/min) for automation tests |
| `local_coach` | Stateless `LocalCoach` instance |
| `discovery_db` | Initialized `SessionDiscovery` with temp DB |

### Test Isolation

Tests that mock `sys.modules` (e.g., `test_agent_tools.py`, `test_claude_provider.py`, `test_agent_core.py`) use `setUpModule()`/`tearDownModule()` to save and restore entries. This prevents test-ordering conflicts when running the full suite. **Never use `sys.modules["foo"] = mock` at module level** — always wrap in setup/teardown. Pre-load real modules (e.g., `import exceptions`) before injecting mocks to avoid clobbering them.

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):
- **test** job: Python 3.10, 3.11, 3.12 — `py_compile` lint + `unittest discover`
- **validate-ml** job: Verifies all ML classes import and `LocalCoach` instantiates

## Known Limitations

### Session Date Accuracy (Uneekor Portal Limitation)

**Problem:** The Uneekor portal does not reliably expose session dates. Report pages show today's "view date", not the original session date.

**Solution (as of 2026-02-03):** The listing page (`/portal/reports`) shows sessions grouped by date headers (e.g., "January 15, 2026"). The `--from-listing` command extracts dates from the DOM by walking the page structure and associating each session link with its preceding date header.

**Recommended approach:**
```bash
# Extract dates from listing page and propagate to shots (single command)
python automation_runner.py reclassify-dates --from-listing --auto-backfill

# Or as separate steps:
python automation_runner.py reclassify-dates --from-listing
python automation_runner.py reclassify-dates --backfill
```

**Alternative methods:**
- `--manual <report_id> <YYYY-MM-DD>`: Set dates for sessions you remember
- `--scrape`: Visit report pages (less reliable, shows current date)

**Date source tracking:** The `date_source` column in `sessions_discovered` tracks where dates came from:
- `listing_page`: Extracted from listing page DOM (most reliable)
- `link_text`: Parsed from session link text
- `report_page`: Scraped from report page header
- `manual`: Manually entered
