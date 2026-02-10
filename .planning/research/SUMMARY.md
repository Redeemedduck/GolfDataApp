# Project Research Summary

**Project:** Local AI/ML Golf Analytics Enhancement
**Domain:** Sports analytics with local-first machine learning
**Researched:** 2026-02-10
**Confidence:** HIGH

## Executive Summary

This project enhances an existing Python/Streamlit golf analytics application with local ML capabilities for offline coaching and insights. The recommended approach builds on a solid foundation (XGBoost, scikit-learn, SQLite) by adding three layers: an analytics engine for table-stakes features (dispersion, true distances, strokes gained), a coaching engine for differentiated features (practice plans, real-time recommendations), and a monitoring layer for model health. The architecture emphasizes local-first execution, graceful degradation when dependencies are missing, and interpretable predictions.

The primary risk is overfitting on small datasets (2000-5000 shots). Golf swing data is high-dimensional but sample sizes are limited compared to typical ML applications. Mitigation requires aggressive XGBoost regularization, nested cross-validation, minimum sample size enforcement, and prominent display of prediction confidence intervals. Secondary risks include fragile lazy-loading architecture and silent database sync failures, both addressable through refactoring in the foundation phase.

Key competitive advantage: Offline ML coaching. Major platforms (TrackMan, Arccos, Golfshot) require cloud connectivity for AI features. Delivering actionable insights locally — practice plans, club recommendations, fault detection — using only launch monitor data creates differentiation while respecting privacy and enabling simulator use in offline environments.

## Key Findings

### Recommended Stack

The existing stack (Python 3.10-3.12, Streamlit, scikit-learn, XGBoost, SQLite) is solid. Recommended additions fall into three categories: model management (MLflow lightweight mode for experiment tracking), prediction quality (MAPIE for confidence intervals, SHAP for explainability), and data validation (pydantic for schema enforcement, scipy.stats for drift detection). All additions integrate cleanly as optional dependencies with graceful degradation.

**Core technologies:**
- **MLflow (lightweight mode)**: Experiment tracking and model versioning — file-based, no server required, addresses lack of version control
- **MAPIE**: Model-agnostic prediction intervals — wraps existing XGBoost/sklearn to produce confidence ranges
- **SHAP**: Feature importance and prediction explanations — critical for user trust ("why does AI recommend this club?")
- **scipy.stats**: Statistical tests for drift detection and significance testing — already installed via transitive dependencies
- **pydantic**: Data validation at entry — enforces valid ranges, centralizes sentinel value (99999) handling

**Avoid:**
- TensorFlow/PyTorch (overkill for tabular data at this scale)
- Weights & Biases (cloud-dependent, violates offline-first constraint)
- LangChain (not needed for structured local ML coaching)
- Ray/Dask (distributed computing unnecessary for 2000-5000 row dataset)

### Expected Features

Research identified 11 features across three tiers based on competitive analysis of TrackMan, Arccos, Golfshot, and other golf analytics platforms.

**Must have (table stakes):**
- Shot dispersion analysis — scatter patterns per club, every competitor offers this
- True club distances — median/IQR instead of maximum, prevents over-clubbing
- Strokes gained analysis — industry standard PGA metric, users expect it
- Miss tendency detection — directional bias (slice/hook/push/pull) per club
- Session-to-session progress tracking — trend lines, statistical significance tests

**Should have (competitive advantage):**
- Personalized practice plans — auto-generated 15-30 min routines from detected weaknesses (LOCAL = differentiator)
- Context-aware recommendations — real-time mid-session suggestions ("last 5 swings show low attack angle, try tee higher")
- Fault pattern recognition — multi-metric clustering to identify swing fault signatures
- Probabilistic club recommendations — Monte Carlo simulation for "7-iron has 65% chance of hitting green"
- Equipment change detection — alert when distances shift >10%, validate with user
- Session quality scoring — single 0-100 gamification metric

**Defer (v2+):**
- Video swing analysis — out of scope, launch monitor data is sufficient
- Social/competitive features — mission drift, conflicts with local-first privacy
- Course strategy simulator — better served by Uneekor's native software
- Biometric integration — peripheral value, adds external API dependencies

### Architecture Approach

The architecture extends the existing layered structure (UI → Coach → AI Registry → ML Module → Data Layer) by adding three new subsystems within the ML module: an analytics engine for pure computation (dispersion, distances, strokes gained), a coaching engine that transforms analytics into advice (practice plans, recommendations), and a monitoring engine for model health (drift detection, versioning, performance tracking). All new code lives in isolated directories with minimal changes to existing modules.

**Major components:**
1. **Analytics Engine (ml/analytics/)** — Pure computation, takes DataFrames and returns insights, zero dependencies on existing ML models, can ship independently
2. **Coaching Engine (ml/coaching/)** — Transforms analytics results into actionable advice using decision trees and template libraries, depends only on analytics output
3. **Model Monitor (ml/monitoring/)** — Tracks model health with drift detection, versioning, and performance logging, wraps existing joblib persistence for backward compatibility

**Integration strategy:**
- Minimal changes to existing code (2 new tables in golf_db.py, extend local_coach.py response generation)
- New functionality isolated in new files/directories
- Risk mitigation: Analytics module has zero coupling to existing ML models, monitoring wraps rather than replaces persistence

### Critical Pitfalls

Research identified 11 pitfalls across critical/moderate/minor severity. Top 5 require immediate attention in foundation and training phases.

1. **Small dataset overfitting** — With 2000-5000 shots, models memorize noise instead of learning patterns. Prevention: aggressive XGBoost regularization (max_depth=3-4, min_child_weight=3), nested k-fold CV, minimum sample size enforcement (2000), early stopping on validation loss. Detection: train accuracy >90% but validation <70%.

2. **Fragile lazy loading architecture** — Current `__getattr__` pattern for ML dependencies fails silently in production, causes race conditions in multi-threaded contexts. Prevention: explicit `try/except ImportError` at module level with feature flags, thread-safe locks if lazy loading required, startup validation with clear UI state. Fix in Phase 1 before adding features.

3. **Silent database sync failures** — Supabase sync errors caught and ignored, causes data loss. Prevention: log ALL failures with context, track sync health metrics (success rate, lag, queue depth), user-visible status ("Synced 5s ago" or "23 shots pending"), retry queue with exponential backoff. Fix in Phase 1.

4. **Rate limiter unit conversion bug** — Token bucket confuses hours/minutes, causes portal IP bans. Prevention: explicit time constants, property-based tests with Hypothesis, freezegun time mocking. Add tests in Phase 1 before automation expansion.

5. **Model staleness without monitoring** — Trained models degrade as swing mechanics evolve, no drift detection. Prevention: statistical tests (Kolmogorov-Smirnov) per session, automated retraining triggers (every 500 shots or monthly), model versioning with metadata, performance logging. Implement in Phase 3.

## Implications for Roadmap

Based on research, suggested phase structure follows dependency chains and risk mitigation priorities:

### Phase 1: Foundation & Stability
**Rationale:** Fix critical infrastructure issues before building new features. Fragile lazy loading, silent sync failures, and rate limiter bugs create technical debt that compounds. The foundation must be solid to support ML expansion.

**Delivers:** Refactored ML imports with explicit optional handling, comprehensive database sync monitoring with retry queue, rate limiter unit tests with time mocking, new tables (session_metrics, model_performance), audit of existing data for sentinel values.

**Addresses:** Critical pitfalls 2-4 (lazy loading, sync failures, rate limiter)

**Avoids:** Building new features on unstable foundation

**Research flag:** SKIP — refactoring and testing, standard patterns

### Phase 2: Analytics Engine (Table Stakes Features)
**Rationale:** Analytics engine is self-contained with zero dependencies on existing ML models. Features 1-4 (dispersion, true distances, strokes gained, miss detection) can be built in parallel and deliver immediate user value. Progress tracking (Feature 5) depends on all four.

**Delivers:** Shot dispersion analysis with 2D scatter and outlier removal, true club distances with median/IQR and confidence intervals, strokes gained analysis with benchmark comparisons, miss tendency detection extending existing D-plane classifier, session-to-session progress tracking with statistical significance tests.

**Uses:** pandas, numpy, scipy.stats (already installed), existing shot shape classifier

**Implements:** ml/analytics/ directory with 5 modules (dispersion, club_distances, strokes_gained, miss_tendencies, progress)

**Addresses:** Features 1-5 (all table stakes)

**Avoids:** Small dataset overfitting (no ML models yet), feature engineering complexity (domain-informed metrics)

**Research flag:** SKIP — established sports analytics patterns, clear specifications from FEATURES.md

### Phase 3: Model Training & Predictions
**Rationale:** With analytics foundation in place, enhance existing ML models with prediction confidence and explainability. This phase focuses on quality over quantity — make existing predictions trustworthy before adding new models.

**Delivers:** MAPIE integration for prediction intervals, SHAP integration for feature importance visualization, enhanced model retraining pipeline with versioning, confidence-aware UI changes ("148-156 yards, 80% confidence"), minimum sample size enforcement before enabling predictions.

**Uses:** MAPIE, SHAP, MLflow (all new dependencies), enhanced XGBoost regularization

**Implements:** ml/monitoring/versioning.py and performance.py, enhanced train_models.py, updated UI components

**Addresses:** Critical pitfall 1 (overfitting), moderate pitfalls 6-7 (prediction uncertainty UX, feature engineering)

**Avoids:** False precision in UI, training on dirty data (Phase 1 audit), black box predictions (SHAP)

**Research flag:** CONSIDER — MAPIE integration patterns and XGBoost regularization tuning may benefit from deeper research if documentation is sparse

### Phase 4: Coaching Engine (Differentiators)
**Rationale:** Now that predictions are trustworthy, build the differentiating features. Practice plans and recommendations use analytics output (from Phase 2) rather than raw ML predictions. Session quality scoring provides gamification.

**Delivers:** Personalized practice plan generator with drill library mapping, context-aware session recommendations (sliding window analysis), session quality scoring (0-100 gamification metric), equipment change detection with user prompts, enhanced local coach integration.

**Uses:** ml/analytics/ output, ml/coaching/ decision trees and templates

**Implements:** ml/coaching/ directory (practice_plans, recommendations), enhanced local_coach.py

**Addresses:** Features 6-7, 10-11 (practice plans, recommendations, equipment detection, session scoring)

**Avoids:** Over-reliance on cloud AI (local templates + rules), alert fatigue (max 1 suggestion per 10 shots)

**Research flag:** MEDIUM — Practice plan design and drill library structure may benefit from domain expert review or sports training literature research

### Phase 5: Advanced Features & Monitoring
**Rationale:** Final polish with high-complexity features and operational monitoring. Fault recognition uses clustering (DBSCAN), probabilistic recommendations use Monte Carlo. Drift detection ensures long-term model health.

**Delivers:** Fault pattern recognition with multi-metric clustering, probabilistic club recommendations with Monte Carlo simulation, drift detection pipeline with Kolmogorov-Smirnov tests, automated retraining triggers, ML dashboard page (new Streamlit page).

**Uses:** DBSCAN clustering, scipy.stats drift tests, ml/monitoring/drift.py

**Implements:** ml/coaching/fault_detection.py, pages/5_ML_Dashboard.py, automated retraining orchestration

**Addresses:** Features 8-9 (fault recognition, probabilistic recommendations), critical pitfall 5 (model staleness)

**Avoids:** Monitoring gaps (drift detection in place), black box fault detection (explainable clusters)

**Research flag:** HIGH — Fault pattern signatures and clustering parameter tuning likely need deeper research into golf biomechanics literature and D-plane theory

### Phase Ordering Rationale

- **Foundation first (Phase 1)** to prevent technical debt from compounding during feature development
- **Analytics before ML enhancement (Phase 2 before 3)** because analytics engine is self-contained and delivers immediate value while de-risking architecture changes
- **Model quality before coaching features (Phase 3 before 4)** ensures coaching recommendations are built on trustworthy predictions
- **Advanced features last (Phase 5)** as they require all prior layers and have highest complexity
- **Dependency chains respected**: Progress tracking needs analytics, coaching needs progress tracking, monitoring needs model versioning

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Model Training):** MAPIE integration patterns if docs are sparse, XGBoost regularization parameter tuning for golf-specific data
- **Phase 4 (Coaching Engine):** Practice plan structure and drill library design — may benefit from sports training pedagogy research
- **Phase 5 (Advanced Features):** Swing fault signatures mapping to biomechanical causes — complex domain requiring D-plane theory and potentially golf instructor input

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Refactoring and testing patterns are well-established
- **Phase 2 (Analytics):** Sports analytics calculations are documented (dispersion, strokes gained formulas publicly available)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommended libraries have proven track records, existing stack is solid, additions are conservative and optional |
| Features | HIGH | Feature set derived from competitive analysis of established platforms (TrackMan, Arccos), clear table stakes vs. differentiators |
| Architecture | HIGH | Extension strategy is low-risk (isolated new code, minimal changes to existing modules), follows existing patterns |
| Pitfalls | MEDIUM-HIGH | Top 5 pitfalls are well-documented in ML literature, golf-specific pitfalls inferred from domain but not exhaustively validated |

**Overall confidence:** HIGH

### Gaps to Address

- **Strokes gained benchmark data**: Research references "static tables from USGA/PGA studies" but doesn't specify sources. Need to identify specific benchmarks during Phase 2 planning or create synthetic benchmarks from available data.

- **Drill library content**: Practice plan generator requires mapping weaknesses to drills. Research doesn't specify drill library source. Options: curate from golf instruction literature, start with small hand-crafted library, or defer to v2 if content creation is too time-intensive.

- **Swing fault signature validation**: Phase 5 fault recognition maps metric clusters to biomechanical faults. Signatures are inferred from D-plane theory but not validated by golf instructors. Consider domain expert review or treat initial version as experimental.

- **Optimal regularization parameters**: Research recommends aggressive XGBoost regularization but doesn't specify if parameters (max_depth=3-4, min_child_weight=3, gamma=1.0) are golf-data-specific or general ML guidance. May need empirical tuning during Phase 3.

## Sources

### Primary (HIGH confidence)
- **STACK.md** — Researched existing stack, evaluated additions (MLflow, MAPIE, SHAP, pydantic), identified libraries to avoid, specified dependency tiers
- **FEATURES.md** — Competitive analysis of TrackMan, Arccos, Golfshot platforms, feature complexity assessment, dependency mapping, build order recommendations
- **ARCHITECTURE.md** — Current architecture documentation, proposed extension design, component boundaries, data flow patterns, integration strategy
- **PITFALLS.md** — Domain pitfall research with ML-specific risks (overfitting, drift), infrastructure risks (lazy loading, sync failures), prevention strategies, phase mapping

### Secondary (MEDIUM confidence)
- Golf analytics platform competitive landscape — feature sets inferred from product marketing and user documentation, not hands-on usage
- D-plane theory for shot shape classification — established golf physics, referenced in multiple sources but not formally cited

### Tertiary (LOW confidence)
- Strokes gained benchmark values — referenced as available from USGA/PGA but specific sources not verified
- Optimal XGBoost regularization for golf data — parameters recommended from general ML guidance, not empirically validated on golf datasets

---
*Research completed: 2026-02-10*
*Ready for roadmap: yes*
