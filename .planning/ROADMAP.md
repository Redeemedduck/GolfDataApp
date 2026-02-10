# Roadmap: Local AI/ML Golf Analytics

**Project:** GolfDataApp — Local AI/ML Modules
**Created:** 2026-02-10
**Depth:** Quick (4 phases)
**Coverage:** 14/14 requirements mapped

## Overview

Transform GolfDataApp into an intelligent offline golf coach by strengthening ML foundations, adding analytics-driven insights, enhancing predictions with confidence intervals, and building personalized coaching features. This roadmap delivers actionable, trustworthy coaching that works without cloud APIs or internet connectivity.

## Phases

### Phase 1: Foundation & Stability

**Goal:** Critical infrastructure is robust and monitorable before building new ML features.

**Dependencies:** None (foundational)

**Requirements:** FNDTN-01, FNDTN-02, FNDTN-03, FNDTN-04

**Plans:** 4 plans (3 original + 1 gap closure)

Plans:
- [x] 01-01-PLAN.md — Refactor ML imports to explicit try/except with feature flags
- [x] 01-02-PLAN.md — Add structured logging and sync status UI for Supabase operations
- [x] 01-03-PLAN.md — Validate model versioning and implement session metrics population
- [x] 01-04-PLAN.md — Gap closure: Add missing session_stats CREATE TABLE to init_db()

**Success Criteria:**
1. ML module imports use explicit try/except with feature flags; startup validates dependencies and displays clear UI state
2. Database sync failures are logged with context and surfaced to user; sync status visible in UI ("Synced 5s ago" or "23 shots pending")
3. Model save/load includes metadata (training date, sample size, accuracy); old models are backward compatible
4. Session metrics table aggregates stats per session; user can query aggregate stats without recalculating from raw shots

**Why this phase:** Research identified fragile lazy loading, silent sync failures, and lack of versioning as critical technical debt. Fix infrastructure before expanding ML features to prevent compounding issues.

---

### Phase 2: Analytics Engine

**Goal:** User sees trustworthy, table-stakes golf analytics: dispersion patterns, true distances, miss tendencies, and progress trends.

**Dependencies:** Phase 1 (requires stable data layer and session metrics)

**Requirements:** ANLYT-01, ANLYT-02, ANLYT-03, ANLYT-04, ANLYT-05

**Success Criteria:**
1. User views shot dispersion scatter plot per club with outlier filtering; patterns are visually clear
2. User sees median carry/total distances with IQR ranges instead of misleading maximums; UI prevents over-clubbing
3. User sees miss tendency breakdown (% straight/draw/fade/hook/slice) per club; patterns inform swing corrections
4. User tracks session-over-session progress with trend lines and % improvement; statistical significance is indicated
5. User sees session quality score (0-100) summarizing consistency and improvement; score is interpretable and motivating

**Plans:** 4 plans (3 original + 1 gap closure)

Plans:
- [x] 02-01-PLAN.md -- Analytics utilities, dispersion chart (ANLYT-01), distance table (ANLYT-02)
- [x] 02-02-PLAN.md -- Miss tendency analysis (ANLYT-03), progress tracker (ANLYT-04)
- [x] 02-03-PLAN.md -- Session quality score (ANLYT-05), component exports, analytics tests
- [ ] 02-04-PLAN.md -- Gap closure: integrate all 5 analytics components into Dashboard page

**Why this phase:** Analytics engine is self-contained with zero dependencies on existing ML models. Delivers immediate user value while de-risking architecture changes. All features can be built in parallel.

---

### Phase 3: ML Enhancement & Coaching

**Goal:** User receives intelligent, context-aware coaching with trustworthy predictions and personalized practice plans.

**Dependencies:** Phase 2 (coaching uses analytics output; predictions need versioning from Phase 1)

**Requirements:** COACH-01, COACH-02, COACH-03, MONTR-02 (partial — retraining UI, full monitoring in Phase 4)

**Success Criteria:**
1. Local coach generates responses using analytics data (e.g., "Your 7-iron dispersion is 18 yards; focus on setup consistency"); responses reference actual stats, not templates
2. User receives 15-30 min personalized practice plan based on detected weaknesses (e.g., "Your driver carries 15 yards left; drill: alignment sticks, 20 reps")
3. Predictions show confidence intervals ("148-156 yards, 80% confidence") not point estimates; users understand prediction uncertainty
4. User can trigger model retraining from UI; retraining completes in <60 seconds; new model version is saved with metadata

**Why this phase:** With trustworthy analytics foundation, enhance predictions with confidence intervals and build differentiating coaching features. Predictions must be trustworthy before coaching relies on them.

---

### Phase 4: Monitoring & Model Health

**Goal:** Models stay accurate over time; drift is detected and addressed automatically.

**Dependencies:** Phase 3 (requires versioning and coaching system to monitor)

**Requirements:** MONTR-01, MONTR-02 (full implementation)

**Success Criteria:**
1. Model drift detection runs after each session; alerts fire when predictions deviate significantly from actuals (e.g., "7-iron prediction off by >10 yards for 3 sessions")
2. Automated retraining is triggered by drift alerts or manual user action; retraining pipeline includes nested cross-validation and regularization checks
3. User sees model performance dashboard: accuracy metrics, feature importance, drift history; UI explains when retraining is recommended

**Why this phase:** Final polish ensuring long-term model health. Drift detection prevents models from degrading as swing mechanics evolve. Closes the feedback loop from prediction to validation to retraining.

---

## Progress

| Phase | Status | Requirements | Completion |
|-------|--------|--------------|------------|
| 1 - Foundation & Stability | Complete (2026-02-10) | 4 | 100% |
| 2 - Analytics Engine | Not Started | 5 | 0% |
| 3 - ML Enhancement & Coaching | Not Started | 4 | 0% |
| 4 - Monitoring & Model Health | Not Started | 2 | 0% |

**Overall:** 4/14 requirements complete (29%)

---

## Notes

- **Depth rationale:** Compressed from research's 5 phases to 4 for quick mode. Combined ML Enhancement + basic Coaching (Phase 3) and deferred advanced features to v2.
- **Research flags:** Phase 3 may need deeper research for MAPIE integration patterns and XGBoost regularization tuning if docs are sparse.
- **Out of scope (deferred to v2):** Fault pattern recognition, probabilistic club recommendations, ML dashboard page, automated drift retraining, equipment change detection.

---

*Roadmap created: 2026-02-10*
*Last updated: 2026-02-10*
