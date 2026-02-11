# GolfDataApp — Golf Analytics Platform

## What This Is

A golf analytics platform that imports shot data from the Uneekor simulator portal, stores it locally (SQLite) with optional cloud sync (Supabase), and provides dashboards, AI coaching, ML-powered predictions, and personalized practice plans through a Streamlit web app. All ML features work offline without API keys or cloud dependencies.

## Core Value

Golfers get actionable, personalized coaching and shot predictions that work offline — no API keys, no cloud dependency, no cost per query.

## Requirements

### Validated

- ✓ SQLite local-first storage with optional Supabase cloud sync — existing
- ✓ Streamlit dashboard with 6-tab analytics — existing + v1.0
- ✓ Uneekor portal automation via Playwright — existing
- ✓ Data import with validation — existing
- ✓ Database management with CRUD, tagging, session splitting — existing
- ✓ AI Coach with pluggable provider selection — existing
- ✓ Gemini cloud AI coach with function calling — existing
- ✓ ML imports with explicit try/except and feature flags — v1.0
- ✓ Supabase sync failure logging and user-facing status — v1.0
- ✓ Model versioning with metadata (date, samples, accuracy) — v1.0
- ✓ Session metrics aggregation table — v1.0
- ✓ Shot dispersion visualization per club with outlier filtering — v1.0
- ✓ True club distances (median carry/total with IQR) — v1.0
- ✓ Miss tendency breakdown per club (D-plane classification) — v1.0
- ✓ Session-over-session progress tracking with statistical significance — v1.0
- ✓ Session quality score (0-100) with component breakdown — v1.0
- ✓ Context-aware local coaching using analytics data — v1.0
- ✓ Personalized practice plans from detected weaknesses — v1.0
- ✓ Prediction confidence intervals (MAPIE conformalized) — v1.0
- ✓ Model drift detection with adaptive baselines — v1.0
- ✓ Manual + automated model retraining — v1.0

### Active

(None — define via `/gsd:new-milestone`)

### Out of Scope

- Video swing analysis — requires CV/pose estimation, launch monitor data sufficient
- Social/competitive features — conflicts with local-first privacy model
- Course strategy simulator — better served by Uneekor native software
- Mobile app or deployment infrastructure — future milestone
- UI redesign — separate effort

## Context

**Shipped v1.0** with 63,754 LOC Python across 202 files.
**Tech stack:** Streamlit, SQLite (WAL mode), XGBoost, scikit-learn, MAPIE, Plotly, Playwright, optional Supabase sync.
**Branch:** `feat/local-ai-ml-modules` (78 commits ahead of main)
**Test suite:** 244 tests (78 new in v1.0) across 7 test files.
**Model performance:** XGBoost distance predictor — MAE 4.18 yards, R² 0.986, trained on 2,140 shots.
**Live-tested:** All 6 pages verified working via Playwright browser automation (3 runtime bugs found and fixed during testing).

## Constraints

- **Offline-first**: All ML/AI features must work without internet or API keys
- **Graceful degradation**: If ML dependencies missing, fall back to rule-based logic
- **Python 3.10+**: Must pass CI on 3.10, 3.11, 3.12
- **No new heavy dependencies**: Prefer sklearn/xgboost ecosystem already in use
- **Data scale**: ~80-100 sessions, ~2000-5000 shots — models must train in <60 seconds

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Local-first ML over cloud AI | Zero cost, works offline, user owns data | ✓ Good — all features work offline |
| Extend existing provider registry | Consistent architecture, minimal refactoring | ✓ Good — LocalCoach as analytics provider |
| Explicit try/except over lazy loading | Fragile `__getattr__` caused silent failures | ✓ Good — clear feature flags (ML_AVAILABLE, etc.) |
| MAPIE for prediction intervals | Distribution-free guarantees, works with XGBoost | ✓ Good — conformal intervals at 80% confidence |
| D-plane classification for miss tendency | Physics-based, no ML dependencies needed | ✓ Good — accurate shot shape categorization |
| Adaptive drift threshold (30%) | Fixed thresholds cause false alarms on small datasets | ✓ Good — median baseline + percentage threshold |
| Composite quality score (40/30/30) | Balances consistency, performance, improvement | ✓ Good — interpretable 0-100 score |
| 4 phases (compressed from 5) | Quick depth mode, deferred advanced features to v2 | ✓ Good — shipped in 2 days |

---
*Last updated: 2026-02-11 after v1.0 milestone*
