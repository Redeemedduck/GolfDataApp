# Requirements: GolfDataApp — Local AI/ML Modules

**Defined:** 2026-02-10
**Core Value:** Golfers get actionable, personalized coaching and shot predictions that work offline

## v1 Requirements

### Foundation (FNDTN)

- [ ] **FNDTN-01**: ML imports use explicit try/except with feature flags instead of fragile `__getattr__` lazy loading
- [ ] **FNDTN-02**: Supabase sync failures are logged with context and surfaced to user, not silently swallowed
- [ ] **FNDTN-03**: Model versioning infrastructure saves/loads models with metadata (training date, sample size, accuracy)
- [ ] **FNDTN-04**: Session metrics table stores aggregate stats per session for trend analysis

### Analytics (ANLYT)

- [ ] **ANLYT-01**: User can view shot dispersion patterns (2D scatter with outlier filtering) per club
- [ ] **ANLYT-02**: User can see true club distances (median carry/total with IQR) instead of maximums
- [ ] **ANLYT-03**: User can see miss tendency breakdown (% straight/draw/fade/hook/slice) per club
- [ ] **ANLYT-04**: User can track session-over-session progress with trend lines and % improvement
- [ ] **ANLYT-05**: User can see session quality score (0-100) summarizing consistency and improvement

### Coaching (COACH)

- [ ] **COACH-01**: Local coach generates context-aware responses using analytics data, not just templates
- [ ] **COACH-02**: User receives personalized practice plan based on detected weaknesses
- [ ] **COACH-03**: User sees prediction confidence intervals ("148-156 yards, 80% confidence") not point estimates

### Monitoring (MONTR)

- [ ] **MONTR-01**: Model drift detection alerts when predictions deviate significantly from actuals
- [ ] **MONTR-02**: User can trigger model retraining with latest shot data

## v2 Requirements

### Advanced Analytics

- **ANLYT-06**: Strokes gained analysis comparing to handicap benchmarks
- **ANLYT-07**: Equipment change detection with user prompts
- **ANLYT-08**: Probabilistic club recommendations via Monte Carlo simulation

### Advanced Coaching

- **COACH-04**: Fault pattern recognition via multi-metric clustering (swing fault signatures)
- **COACH-05**: Context-aware mid-session recommendations (sliding window analysis)
- **COACH-06**: SHAP-based prediction explanations showing feature contributions

### Infrastructure

- **MONTR-03**: ML dashboard page showing model performance, feature importance, drift history
- **MONTR-04**: Automated retraining pipeline triggered by drift thresholds

## Out of Scope

| Feature | Reason |
|---------|--------|
| Video swing analysis | Requires different tech stack (CV/pose estimation), launch monitor data sufficient |
| Social/competitive features | Mission drift, conflicts with local-first privacy model |
| Course strategy simulator | Better served by Uneekor's native software |
| Biometric integration | Adds external API dependencies, peripheral value |
| New cloud AI providers | Gemini integration already works, not this milestone |
| UI redesign | Separate effort, this milestone focuses on ML backend |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FNDTN-01 | Phase 1 | Pending |
| FNDTN-02 | Phase 1 | Pending |
| FNDTN-03 | Phase 1 | Pending |
| FNDTN-04 | Phase 1 | Pending |
| ANLYT-01 | Phase 2 | Pending |
| ANLYT-02 | Phase 2 | Pending |
| ANLYT-03 | Phase 2 | Pending |
| ANLYT-04 | Phase 2 | Pending |
| ANLYT-05 | Phase 2 | Pending |
| COACH-01 | Phase 3 | Pending |
| COACH-02 | Phase 3 | Pending |
| COACH-03 | Phase 3 | Pending |
| MONTR-02 | Phase 3 | Pending (partial — retraining UI) |
| MONTR-01 | Phase 4 | Pending |
| MONTR-02 | Phase 4 | Pending (full — automated triggers) |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

**Notes:**
- MONTR-02 split across Phase 3 (manual retraining UI) and Phase 4 (automated retraining triggers)
- Phase count compressed from 5 to 4 for quick depth mode

---
*Requirements defined: 2026-02-10*
*Last updated: 2026-02-10 after roadmap creation*
