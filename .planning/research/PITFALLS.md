# Domain Pitfalls: Local AI/ML Golf Analytics

**Domain:** Golf analytics with local ML coaching
**Researched:** 2026-02-10
**Confidence:** MEDIUM-HIGH

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Small Dataset Overfitting

**What goes wrong:** With 2000-5000 shots, ML models memorize training data noise rather than learning generalizable patterns. Models achieve 95%+ training accuracy but 60% test accuracy. Predictions fail catastrophically on new swing variations.

**Why it happens:** XGBoost and gradient boosting models are powerful enough to fit extremely complex patterns. Small datasets don't represent the full distribution of swing mechanics, club variations, and environmental conditions.

**Consequences:**
- Model confidently predicts wildly incorrect distances
- Different clubs produce identical predictions
- Model breaks when golfer adjusts technique
- Users lose trust in AI coach after bad recommendations

**Prevention:**
1. **Aggressive regularization** - Use XGBoost's `max_depth=3-4`, `min_child_weight=3`, `gamma=1.0` to limit tree complexity
2. **Nested cross-validation** - Use k-fold CV (k=5) for both model selection AND hyperparameter tuning
3. **Sample size validation** - Require minimum 2000 samples before enabling ML predictions
4. **Early stopping** - Monitor validation loss during training; stop when validation performance plateaus
5. **Feature selection** - Reduce feature count to 10-15 most important features to match dataset size

**Detection:**
- Training accuracy >90% but validation accuracy <70%
- High feature importance on irrelevant features (e.g., date_added predicting distance)
- Prediction variance increases dramatically on recent sessions
- Users report "AI coach worked at first, now gives bad advice"

**Phase mapping:** Phase 2 (Model Training) - implement before first model training

---

### Pitfall 2: Fragile Lazy Loading Architecture

**What goes wrong:** The `__getattr__` pattern for lazy-loading ML dependencies fails silently in production, causes race conditions in multi-threaded contexts, and breaks static analysis tools.

**Why it happens:** Lazy loading defers import errors until runtime attribute access. Multiple threads can trigger simultaneous imports without locks.

**Consequences:**
- `ModuleNotFoundError` raised when user clicks "Get AI Recommendation" instead of at app startup
- Race condition causes duplicate XGBoost imports and memory bloat
- Circular imports between `ml/` and `local_coach.py` surface only in production

**Prevention:**
1. **Explicit optional imports** - Use `try/except ImportError` at module level with clear fallback flags
2. **Thread-safe loading** - If lazy loading is essential, use `threading.Lock()` around import logic
3. **Startup validation** - Check `ML_AVAILABLE` in app.py and show clear UI state
4. **Feature flags** - Separate `ML_INSTALLED` (dependencies present) from `ML_ENABLED` (user opted in + minimum data threshold met)

**Detection:**
- Late `ModuleNotFoundError` in production logs
- Intermittent AI coach failures that resolve on retry (race condition)
- High memory usage with multiple XGBoost instances loaded

**Phase mapping:** Phase 1 (Foundation) - refactor before adding new ML features

---

### Pitfall 3: Silent Database Sync Failures

**What goes wrong:** Supabase sync errors are caught and ignored, causing data loss without alerts. Users see "saved" confirmations but data never reaches cloud.

**Why it happens:** Current implementation wraps Supabase calls in `try/except` with no logging. Soft dependency model makes failures "acceptable."

**Consequences:**
- Shot data lost permanently when local SQLite corrupts
- Multi-device users see stale data on second device
- No visibility into sync lag until user complains

**Prevention:**
1. **Explicit error handling** - Log ALL sync failures with context (table, operation, error type, record count)
2. **Sync health metrics** - Track success rate, lag time, queue depth
3. **User-visible status** - Show sync state in UI: "Synced 5 seconds ago" or "Offline mode - 23 shots pending sync"
4. **Retry queue** - Failed syncs go to persistent queue with exponential backoff

**Detection:**
- Empty Supabase tables despite local data
- `change_log` entries with no corresponding Supabase updates
- User reports "lost my data" or "session disappeared"

**Phase mapping:** Phase 1 (Foundation) - fix immediately, blocks reliable operation

---

### Pitfall 4: Rate Limiter Unit Conversion Bug

**What goes wrong:** Token bucket rate limiter confuses hours/minutes, causing either aggressive blocking or ineffective limiting (portal bans IP).

**Why it happens:** Time unit conversions are error-prone. Common mistakes: mixing `time.time()` (seconds) with millisecond calculations, or inverting rate.

**Consequences:**
- Automation runs stall with false "rate limit exceeded" errors
- Portal blocks IP for excessive requests despite rate limiter
- Backfill takes 10x longer than expected

**Prevention:**
1. **Explicit time constants** - Named constants for `SECONDS_PER_MINUTE`, `SECONDS_PER_HOUR`
2. **Property-based tests** - Use Hypothesis to test rate limiter with various time scales
3. **Unit test coverage** - Test exact scenarios: 6 req/min should allow 6 requests in 60 seconds, deny 7th
4. **Integration test with mock time** - Use `freezegun` to advance time and verify token bucket refills

**Detection:**
- Automation fails immediately despite being first request
- Logs show wait times of 3600+ seconds (hours instead of minutes)
- Portal returns 429 errors despite rate limiter "allowing" requests

**Phase mapping:** Phase 1 (Foundation) - add tests before automation expansion

---

### Pitfall 5: Model Staleness Without Monitoring

**What goes wrong:** Trained models degrade silently as golfer's swing mechanics evolve. Predictions become increasingly inaccurate but no alerts fire.

**Why it happens:** No drift detection pipeline. Models trained once and never updated. User swing improvements shift data distribution.

**Consequences:**
- Model trained on beginner data gives bad advice to improving golfer
- Club changes invalidate distance predictions
- AI coach becomes less useful over time, users churn

**Prevention:**
1. **Drift detection** - Monitor key metrics per session using statistical tests (Kolmogorov-Smirnov)
2. **Automated retraining triggers** - Every 500 new shots, when drift score exceeds threshold, or monthly
3. **Model versioning** - Tag models with training date, sample size, feature set
4. **Performance tracking** - Log prediction accuracy per session to database

**Detection:**
- Mean absolute error increases over time
- User engagement with AI coach decreases
- No model files modified in 6+ months

**Phase mapping:** Phase 3 (Monitoring & Retraining) - implement after initial model deployment

---

## Moderate Pitfalls

### Pitfall 6: Poor UX for Prediction Uncertainty

**What goes wrong:** ML predictions shown with false precision ("247 yards") when uncertainty is +/-30 yards. Users trust bad predictions because UI doesn't communicate confidence.

**Prevention:**
1. **Confidence intervals** - Use quantile regression or bootstrap prediction intervals: "240-260 yards (80% confidence)"
2. **Visual uncertainty** - Show prediction as range bar, not single number
3. **Sample size warnings** - "Low confidence: Only 12 Driver shots in training data."

**Phase mapping:** Phase 2 (Model Training) - design alongside prediction features

---

### Pitfall 7: Feature Engineering Complexity

**What goes wrong:** Golf data has complex relationships (D-plane theory, spin loft, dynamic loft vs static loft). Naive features miss critical interactions.

**Prevention:**
1. **Domain-informed features** - Consult D-plane theory: spin axis affects curve, attack angle + dynamic loft = spin loft
2. **Interaction terms** - Create `club_speed * smash_factor`, `attack_angle * spin_rate`
3. **Golf-specific ratios** - Smash factor (ball speed / club speed), carry-to-total ratio
4. **Feature importance analysis** - Use XGBoost's `plot_importance()` to validate features match domain expectations

**Phase mapping:** Phase 2 (Model Training) - research before feature selection

---

### Pitfall 8: Missing Data Handling

**What goes wrong:** Uneekor's `99999` sentinel value for missing data not consistently cleaned. Models trained on sentinel values produce garbage predictions.

**Prevention:**
1. **Centralized cleaning** - Single `clean_golf_data()` function applied to ALL data entry points
2. **Schema validation** - Enforce reasonable ranges per field
3. **Sentinel detection** - Explicit check for `99999`, `None`, `-1`, empty strings
4. **Imputation strategy** - For training: drop rows with missing target. For features: median imputation per club type

**Phase mapping:** Phase 1 (Foundation) - audit existing data before model training

---

## Minor Pitfalls

### Pitfall 9: Inadequate Train/Test Split Strategy

**What goes wrong:** Random train/test split leaks information when multiple shots from same session span both sets.

**Prevention:** Use time-based or session-based split. Train on sessions 1-80%, test on sessions 81-100%.

**Phase mapping:** Phase 2 (Model Training)

---

### Pitfall 10: Ignoring Multicollinearity

**What goes wrong:** Ball speed and club speed are highly correlated. Model unstable, coefficients uninterpretable.

**Prevention:** Calculate VIF for features. Drop or combine collinear features (e.g., keep smash factor, drop individual speeds). Tree-based models handle multicollinearity better than linear models.

**Phase mapping:** Phase 2 (Model Training)

---

### Pitfall 11: No Model Explainability

**What goes wrong:** AI coach says "hit 7 iron" but golfer doesn't understand why. Black box predictions reduce trust.

**Prevention:** Use SHAP values to explain predictions. Show feature contributions visually.

**Phase mapping:** Phase 3 (Advanced Features)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Foundation Setup | Fragile lazy loading breaks in production | Refactor to explicit optional imports with feature flags |
| Foundation Setup | Silent sync failures lose data | Add logging, metrics, retry queue, user-visible status |
| Foundation Setup | Rate limiter unit conversion bug | Comprehensive unit tests with time mocking |
| Data Pipeline | Sentinel values in training data | Centralized cleaning, schema validation |
| Model Training | Overfitting small dataset | Aggressive regularization, nested CV, sample size checks |
| Model Training | Poor feature engineering | Research biomechanics, domain-informed features |
| Model Training | Misleading train/test split | Session-based or time-based split strategy |
| Model Deployment | Prediction uncertainty not communicated | Confidence intervals, visual ranges, sample size warnings |
| Monitoring | Model staleness goes undetected | Drift detection, automated retraining, performance tracking |
| Advanced Features | Black box predictions reduce trust | SHAP explainability, feature contribution visualization |

---
*Research completed: 2026-02-10*
