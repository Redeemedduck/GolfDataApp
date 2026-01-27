# Design: Codebase Cleanup & Test Coverage Improvement

**Date:** 2026-01-27
**Status:** Approved
**Scope:** Remove dead code/docs, improve test coverage, tighten architecture

## Context

The GolfDataApp has grown organically through several phases. Cloud infrastructure (BigQuery, Vertex AI, Cloud Run) was built but is not actively used — only Supabase sync is real. The legacy scraper is kept as a fallback. The repo has accumulated 20+ root-level markdown files, debug scripts, and deployment configs that no longer apply.

The test suite has 81 methods across 8 files, but only 36 pass locally due to missing optional dependencies. Effective coverage is ~15%. Major modules like `naming_conventions.py`, `credential_manager.py`, and `exceptions.py` have zero tests.

## Constraints

- **Moderate breaking changes OK** — restructure imports, move files, consolidate modules. App must still run and tests must pass afterward.
- **Supabase sync is active** — keep all Supabase integration intact.
- **Legacy scraper stays** — `golf_scraper.py` is kept as fallback, no investment needed.
- **Cloud Run / BigQuery / Vertex AI are unused** — safe to remove entirely.

---

## Phase 1: Remove Dead Weight

### Delete: Cloud Infrastructure (6 files)

- `cloudbuild.yaml`
- `deploy.sh`
- `setup_cron.sh`
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

### Delete: Cloud Scripts (4 files, ~1,072 lines)

- `scripts/supabase_to_bigquery.py`
- `scripts/vertex_ai_analysis.py`
- `scripts/post_session.py`
- `scripts/auto_sync.py`

### Delete: Cloud Schema & Deps (2 files)

- `bigquery_schema.json`
- `requirements_cloud.txt`

### Delete: Legacy Directory (7 files, ~656 lines)

Everything in `legacy/`:
- `check_clubs.py`
- `debug_scraper.py`, `debug_scraper2.py`, `debug_scraper3.py`
- `golf_scraper_fixed.py`
- `golf_scraper_selenium_backup.py`
- `inspect_api_response.py`
- `test_connection.py`

### Delete: Duplicate Markdown (1 file)

- `IMPROVEMENT_PLAN.md` (superseded by `IMPROVEMENT_ROADMAP.md`)

### Archive to `docs/archive/` (8 files)

- `DEPLOYMENT_SUMMARY.md`
- `PIPELINE_COMPLETE.md`
- `PHASE1_SUMMARY.md`
- `PHASE2_SUMMARY.md`
- `PHASE3_SUMMARY.md`
- `VERTEX_AI_SETUP.md`
- `WORKFLOW_REVIEW.md`
- `CLOUD_RUN_DEPLOYMENT.md`

### Fix `.gitignore`

Ensure ignored:
```
__pycache__/
*.pyc
*.pyo
*.db-shm
*.db-wal
golf_stats.db
golf_data.db
.uneekor_cookies.enc
.uneekor_key
/models/trained_*.pkl
```

### Clean `requirements.txt`

Remove cloud-only deps: `google-cloud-bigquery`, `google-cloud-aiplatform`, `db-dtypes` (verify no active imports first).

**Estimated removal: ~3,500-4,000 lines of code + 9 markdown files.**

---

## Phase 2: Improve Test Coverage

### Fix existing tests

Add `unittest.skipUnless` guards on test classes that need heavy optional deps (pandas, numpy, scikit-learn, xgboost). The full suite should always run cleanly — missing deps produce skips, not errors.

### New tests (priority order)

1. **`tests/unit/test_naming_conventions.py`**
   - Club name normalization exhaustive tests
   - All aliases ("7i" -> "7 Iron", "Drv" -> "Driver", etc.)
   - Edge cases: empty string, unknown clubs, case sensitivity

2. **`tests/unit/test_credential_manager.py`**
   - Encryption/decryption roundtrip
   - Cookie save and load
   - Missing key file handling
   - All mockable without real browser

3. **`tests/unit/test_exceptions.py`**
   - Exception hierarchy verification
   - Context dict behavior
   - String representations

4. **`tests/test_golf_db.py` additions**
   - `init_db()` schema creation
   - Soft delete -> archive flow
   - Tag CRUD operations
   - `get_all_sessions()`

5. **`tests/unit/test_automation_runner.py`**
   - CLI argument parsing
   - Subcommand routing (mock actual runners)

6. **`tests/unit/test_observability.py`**
   - JSONL append/read cycle
   - File creation on first write

### Out of scope

- Playwright browser tests (need real browser)
- Streamlit UI tests (framework limitation)
- `gemini_coach.py` (external API, covered by provider pattern)

---

## Phase 3: Tighten Architecture

### Update documentation

- **`CLAUDE.md`** — Remove cloud references (Cloud Run, BigQuery, Vertex AI, Dockerfile). Update commands, architecture diagram, module table.
- **`README.md`** — Simplify to local-first + Supabase. Remove cloud deployment sections.
- **`IMPROVEMENT_ROADMAP.md`** — Update to reflect current priorities.

### Consolidate root markdown

- Merge `CLAUDE_SETUP.md` + `SETUP_GUIDE.md` -> single `SETUP_GUIDE.md`
- Fold `AGENTS.md` into `CLAUDE.md`
- Delete `CLAUDE_BRANCH.md` after branch merge

**Target: 7 root-level markdown files** (README, CLAUDE, QUICKSTART, SETUP_GUIDE, AUTOMATION_GUIDE, IMPROVEMENT_ROADMAP, changelog)

### Verify CI pipeline

- Update `.github/workflows/ci.yml` to remove `py_compile` for deleted files
- Confirm new skip-guarded tests run
- Verify `validate-ml` job still works

### Clean requirements.txt

Remove cloud-only packages. Verify every remaining dependency is imported by active code.
