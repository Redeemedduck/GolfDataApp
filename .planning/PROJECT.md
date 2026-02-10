# GolfDataApp — Local AI/ML Modules

## What This Is

A golf analytics platform that imports shot data from the Uneekor simulator portal, stores it locally (SQLite) with optional cloud sync (Supabase), and provides dashboards, AI coaching, and ML-powered insights through a Streamlit web app. This milestone focuses on strengthening the local AI and ML capabilities so the app delivers intelligent coaching and predictions without requiring cloud API keys.

## Core Value

Golfers get actionable, personalized coaching and shot predictions that work offline — no API keys, no cloud dependency, no cost per query.

## Requirements

### Validated

- ✓ SQLite local-first storage with optional Supabase cloud sync — existing
- ✓ Streamlit dashboard with 5-tab analytics (Overview, Impact, Trends, Shots, Export) — existing
- ✓ Uneekor portal automation via Playwright (discovery, backfill, rate limiting) — existing
- ✓ Data import from Uneekor URLs with validation — existing
- ✓ Database management with CRUD, tagging, session splitting — existing
- ✓ AI Coach page with pluggable provider selection — existing
- ✓ Gemini cloud AI coach with function calling — existing
- ✓ Basic local coach with intent detection and template responses — existing
- ✓ ML models: XGBoost distance prediction, shot shape classification, anomaly detection — existing
- ✓ Exception hierarchy with context dicts — existing
- ✓ Soft-delete archival and recovery — existing
- ✓ Club name normalization and session date reclassification — existing

### Active

- [ ] Enhanced local AI coaching beyond templates (context-aware, conversational)
- [ ] Improved ML training pipeline (automated retraining, model versioning)
- [ ] Practice plan generation from ML analysis (club gaps, consistency issues)
- [ ] Shot prediction confidence and explanation (why the model predicts X)
- [ ] Swing pattern detection across sessions (trends, regressions, breakthroughs)
- [ ] Club recommendation engine (which club for which situation)
- [ ] ML model performance dashboard (accuracy metrics, feature importance)

### Out of Scope

- Cloud AI provider changes (Gemini integration already works) — not this milestone
- UI redesign or new Streamlit pages beyond ML dashboards — separate effort
- Automation/scraper improvements — tracked separately
- Mobile app or deployment infrastructure — future milestone

## Context

- Branch: `feat/local-ai-ml-modules`
- Existing ML module (`ml/`) uses lazy loading via `__getattr__` — graceful degradation if sklearn/xgboost missing
- Local coach (`local_coach.py`) currently uses intent detection + template responses — functional but not intelligent
- AI provider registry (`services/ai/`) supports pluggable backends via `@register_provider` decorator
- Concerns: ML lazy imports are fragile, no model versioning, no retraining pipeline
- The `anthropic` package is installed but unused — available for local provider integration

## Constraints

- **Offline-first**: All new ML/AI features must work without internet or API keys
- **Graceful degradation**: If ML dependencies missing, fall back to rule-based logic (existing pattern)
- **Python 3.10+**: Must pass CI on 3.10, 3.11, 3.12
- **No new heavy dependencies**: Prefer sklearn/xgboost ecosystem already in use
- **Data scale**: ~80-100 sessions, ~2000-5000 shots — models must train in <60 seconds

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Local-first ML over cloud AI | Zero cost, works offline, user owns data | — Pending |
| Extend existing provider registry | Consistent with architecture, minimal refactoring | — Pending |
| Keep lazy loading pattern for ML | Already established, allows optional install | — Pending |

---
*Last updated: 2026-02-09 after initialization*
