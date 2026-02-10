# Phase 4: Monitoring & Model Health - Research

**Researched:** 2026-02-10
**Domain:** ML model drift detection, performance monitoring, automated retraining triggers
**Confidence:** HIGH

## Summary

Phase 4 builds a monitoring system that tracks model performance over time, detects drift when predictions degrade, and automates retraining triggers. The core technical challenge is balancing detection sensitivity (catching real drift) with false alarms (triggering unnecessary retraining) on small datasets (2000-5000 shots).

Three key insights drive this phase: (1) Prediction error monitoring (MAE/RMSE tracking) is the gold standard for concept drift detection when ground truth labels are available, far superior to statistical distribution tests; (2) Adaptive thresholds based on historical performance patterns reduce false alarms compared to fixed thresholds; (3) Offline-first architecture requires storing drift history locally for dashboard visualization, not relying on external monitoring services.

The project has strong existing infrastructure: `session_stats` table for aggregated metrics (Phase 1), `update_session_metrics()` auto-updates on shot save/delete, model metadata with training date and MAE (Phase 3), and retraining UI with prediction intervals (Phase 3). Phase 4 extends these by adding prediction tracking, drift detection logic, performance dashboard components, and automated retraining triggers.

**Primary recommendation:** Track prediction vs actual error per session using MAE as primary drift metric, store drift history in new `model_performance` table, trigger retraining when MAE increases >30% above baseline for 3+ consecutive sessions, and build Streamlit dashboard with feature importance trends, MAE history chart, and retraining recommendation alerts.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.x | Error metrics computation, drift history aggregation | Already in use; foundation for time-series tracking |
| numpy | 1.23+ | Statistical calculations, MAE/RMSE computation | Already in use; efficient array operations |
| Plotly | 5.x | Interactive drift charts, feature importance trends | Already in use (Phase 2); consistent UI patterns |
| sqlite3 | Built-in | Local drift history persistence | Already in use; offline-first requirement |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | 1.11+ | Statistical tests for baseline computation (quantiles) | Already installed; establish adaptive thresholds |
| Streamlit | 1.31+ | Dashboard UI components | Already in use; render performance metrics |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| MAE tracking | Kolmogorov-Smirnov test for distribution drift | MAE directly measures prediction quality; K-S only detects input distribution changes (may not affect performance) |
| Local SQLite storage | External monitoring service (e.g., Evidently AI, Grafana) | Offline-first constraint requires local storage; external services add API dependency |
| Adaptive thresholds | Fixed MAE threshold (e.g., always retrain at MAE > 10 yards) | Adaptive adjusts for seasonality and user skill improvement; fixed causes false alarms |

**Installation:**
No new dependencies required. All libraries already installed.

## Architecture Patterns

### Recommended Module Structure
```
ml/
├── monitoring/
│   ├── __init__.py
│   ├── drift_detector.py      # Core drift detection logic
│   └── performance_tracker.py # Prediction logging and metrics

components/
├── model_health_dashboard.py  # Main dashboard component
├── drift_history_chart.py     # MAE over time visualization
├── feature_importance_trend.py # Feature importance over versions
└── retraining_alert.py        # Alert UI when drift detected

golf_db.py                      # Extend with model_performance table
```

### Pattern 1: Prediction Logging on Each Shot
**What:** Log predictions alongside actuals in database for drift calculation
**When to use:** Every time a shot is imported (MONTR-01)
**Example:**
```python
# Source: Production ML monitoring best practices + existing golf_db pattern
def log_prediction(shot_id: str, club: str, predicted_carry: float, actual_carry: float, model_version: str) -> None:
    """
    Log prediction for drift tracking.

    This creates a prediction record that will be used to compute drift metrics
    per session and over time.

    Args:
        shot_id: Shot identifier
        club: Club used
        predicted_carry: Model prediction (yards)
        actual_carry: Actual carry distance (yards)
        model_version: Model version string (from metadata.version)
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        # Store prediction for later drift analysis
        cursor.execute('''
            INSERT INTO model_predictions (
                shot_id, club, predicted_value, actual_value,
                absolute_error, model_version, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            shot_id,
            club,
            predicted_carry,
            actual_carry,
            abs(predicted_carry - actual_carry),
            model_version
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"Failed to log prediction: {e}")
```

**Integration point:** Call `log_prediction()` in `save_shot()` after importing Uneekor data. Only log if model exists and shot has valid carry distance.

### Pattern 2: Session-Level Drift Detection
**What:** Compute drift metrics per session and check against adaptive thresholds
**When to use:** After `update_session_metrics()` completes (MONTR-01)
**Example:**
```python
# Source: Research on drift detection thresholds + adaptive baselines
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

class DriftDetector:
    """
    Detects model drift by comparing prediction error against baseline.

    Uses adaptive thresholds based on historical performance to reduce false alarms.
    """

    def __init__(self, drift_threshold_pct: float = 0.30):
        """
        Initialize drift detector.

        Args:
            drift_threshold_pct: Percentage increase in MAE that triggers alert (default 30%)
        """
        self.drift_threshold_pct = drift_threshold_pct

    def check_session_drift(self, session_id: str) -> Dict[str, Any]:
        """
        Check if model predictions for this session show significant drift.

        Compares session MAE against baseline (median of last 20 sessions).
        Alerts if MAE exceeds baseline by drift_threshold_pct.

        Args:
            session_id: Session to check

        Returns:
            Dict with:
            - has_drift: bool
            - session_mae: float (yards)
            - baseline_mae: float (yards)
            - drift_pct: float (percentage above baseline)
            - consecutive_drift_sessions: int
            - recommendation: str (action to take)
        """
        # Get predictions for this session
        df = self._get_session_predictions(session_id)

        if df.empty or len(df) < 5:
            return {
                'has_drift': False,
                'message': f'Need at least 5 predictions (have {len(df)})'
            }

        # Compute session MAE
        session_mae = df['absolute_error'].mean()

        # Get baseline MAE (median of last 20 sessions)
        baseline_mae = self._get_baseline_mae()

        if baseline_mae is None:
            # Not enough history - store this as baseline reference
            self._store_performance_record(session_id, session_mae, baseline_mae=None, has_drift=False)
            return {
                'has_drift': False,
                'session_mae': session_mae,
                'message': 'Building baseline (need 20+ sessions)'
            }

        # Calculate drift percentage
        drift_pct = (session_mae - baseline_mae) / baseline_mae

        # Check if drift exceeds threshold
        has_drift = drift_pct > self.drift_threshold_pct

        # Count consecutive drift sessions
        consecutive = self._count_consecutive_drift() if has_drift else 0

        # Store record
        self._store_performance_record(session_id, session_mae, baseline_mae, has_drift)

        # Generate recommendation
        if consecutive >= 3:
            recommendation = "URGENT: Retrain model - drift detected for 3+ sessions"
        elif has_drift:
            recommendation = f"Monitor closely - drift detected ({consecutive + 1} session{'s' if consecutive > 0 else ''})"
        else:
            recommendation = "Model performing within expected range"

        return {
            'has_drift': has_drift,
            'session_mae': session_mae,
            'baseline_mae': baseline_mae,
            'drift_pct': drift_pct,
            'consecutive_drift_sessions': consecutive,
            'recommendation': recommendation
        }

    def _get_session_predictions(self, session_id: str) -> pd.DataFrame:
        """Get all predictions for a session."""
        conn = sqlite3.connect(SQLITE_DB_PATH)
        df = pd.read_sql_query(
            "SELECT * FROM model_predictions WHERE shot_id IN (SELECT shot_id FROM shots WHERE session_id = ?)",
            conn,
            params=(session_id,)
        )
        conn.close()
        return df

    def _get_baseline_mae(self) -> Optional[float]:
        """
        Get baseline MAE (median of last 20 sessions).

        Uses median instead of mean to be robust to outlier sessions.
        """
        conn = sqlite3.connect(SQLITE_DB_PATH)
        df = pd.read_sql_query('''
            SELECT session_mae
            FROM model_performance
            WHERE session_mae IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 20
        ''', conn)
        conn.close()

        if len(df) < 10:
            # Need at least 10 sessions for reliable baseline
            return None

        return df['session_mae'].median()

    def _count_consecutive_drift(self) -> int:
        """Count consecutive sessions with drift (from most recent)."""
        conn = sqlite3.connect(SQLITE_DB_PATH)
        df = pd.read_sql_query('''
            SELECT has_drift
            FROM model_performance
            ORDER BY timestamp DESC
            LIMIT 10
        ''', conn)
        conn.close()

        count = 0
        for has_drift in df['has_drift']:
            if has_drift:
                count += 1
            else:
                break
        return count

    def _store_performance_record(self, session_id: str, session_mae: float, baseline_mae: Optional[float], has_drift: bool) -> None:
        """Store performance metrics for this session."""
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO model_performance (
                session_id, session_mae, baseline_mae, has_drift, timestamp
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (session_id, session_mae, baseline_mae, has_drift))

        conn.commit()
        conn.close()
```

**Trigger integration:** Call `DriftDetector().check_session_drift(session_id)` in `update_session_metrics()` after computing session stats. Display alert in UI if `has_drift=True`.

**Why 30% threshold:** Research shows adaptive thresholds reduce false alarms. 30% balances sensitivity (catches real degradation) with specificity (avoids retraining on normal variance). For typical MAE of 8 yards, drift triggers at ~10.4 yards.

**Why median baseline:** Median is robust to outlier sessions (e.g., one session with bad data). Mean would be pulled by outliers, causing false alarms.

### Pattern 3: Model Performance Dashboard
**What:** Streamlit component showing drift history, feature importance trends, and retraining recommendations
**When to use:** New dashboard page or section in existing Dashboard (MONTR-01, MONTR-02)
**Example:**
```python
# Source: ML monitoring dashboard best practices + existing Streamlit patterns
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_model_health_dashboard():
    """
    Render model performance monitoring dashboard.

    Shows:
    - Current model info (version, training date, samples)
    - MAE trend over time (drift chart)
    - Feature importance comparison across versions
    - Drift alerts and retraining recommendations
    """
    st.header("🔬 Model Health Monitor")

    # Load current model metadata
    metadata = get_model_info(DISTANCE_MODEL_PATH)

    if not metadata:
        st.warning("No model trained. Train a model first.")
        return

    # Current model info
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Model Version", metadata.version)

    with col2:
        trained_date = metadata.trained_at.split('T')[0] if 'T' in metadata.trained_at else metadata.trained_at
        st.metric("Trained", trained_date)

    with col3:
        st.metric("Training Samples", f"{metadata.training_samples:,}")

    with col4:
        training_mae = metadata.metrics.get('mae', 0)
        st.metric("Training MAE", f"{training_mae:.1f} yd")

    st.divider()

    # Get performance history
    conn = sqlite3.connect(SQLITE_DB_PATH)
    perf_df = pd.read_sql_query('''
        SELECT
            session_id, session_mae, baseline_mae, has_drift, timestamp
        FROM model_performance
        ORDER BY timestamp ASC
    ''', conn)
    conn.close()

    if perf_df.empty:
        st.info("📊 No performance data yet. Import sessions with shot data to start tracking.")
        return

    # Check for recent drift
    recent_drift = perf_df.tail(5)['has_drift'].any()
    consecutive_drift = (perf_df.tail(3)['has_drift'] == True).sum()

    if consecutive_drift >= 3:
        st.error(
            "🚨 **Model Drift Detected**\n\n"
            f"Prediction error has exceeded baseline for {consecutive_drift} consecutive sessions. "
            "Retraining is strongly recommended."
        )

        if st.button("🔄 Retrain Model Now", type="primary", use_container_width=True):
            # Trigger retraining flow (reuse existing retraining_ui logic)
            with st.spinner("Retraining model..."):
                predictor = DistancePredictor()
                df = golf_db.get_all_shots()

                # Determine if we can train with intervals
                can_train_intervals = HAS_MAPIE and len(df) >= 1000

                if can_train_intervals:
                    new_metadata = predictor.train_with_intervals(df=df, save=True)
                else:
                    new_metadata = predictor.train(df=df, save=True)

                st.success(
                    f"✅ Model retrained successfully!\n\n"
                    f"- **New MAE:** {new_metadata.metrics['mae']:.2f} yards\n"
                    f"- **Samples:** {new_metadata.training_samples:,}"
                )
                st.rerun()

    elif recent_drift:
        st.warning(
            "⚠️ **Elevated Error Detected**\n\n"
            "Recent sessions show increased prediction error. Continue monitoring."
        )
    else:
        st.success("✅ Model performing within expected range")

    # MAE Trend Chart
    st.subheader("📈 Prediction Error Trend")

    fig = go.Figure()

    # Session MAE line
    fig.add_trace(go.Scatter(
        x=perf_df['timestamp'],
        y=perf_df['session_mae'],
        mode='lines+markers',
        name='Session MAE',
        line=dict(color='blue', width=2),
        marker=dict(
            size=6,
            color=['red' if drift else 'blue' for drift in perf_df['has_drift']]
        )
    ))

    # Baseline MAE line (dashed)
    fig.add_trace(go.Scatter(
        x=perf_df['timestamp'],
        y=perf_df['baseline_mae'],
        mode='lines',
        name='Baseline (median)',
        line=dict(color='gray', width=1, dash='dash')
    ))

    # Training MAE reference (horizontal line)
    fig.add_hline(
        y=training_mae,
        line_dash="dot",
        line_color="green",
        annotation_text="Training MAE",
        annotation_position="right"
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Mean Absolute Error (yards)",
        hovermode='x unified',
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "🔵 Blue points = normal performance | "
        "🔴 Red points = drift detected (>30% above baseline)"
    )

    # Feature Importance (current model)
    st.divider()
    st.subheader("🎯 Feature Importance")

    predictor = DistancePredictor()
    predictor.load()

    if predictor.is_loaded() and hasattr(predictor.model, 'feature_importances_'):
        importance = dict(zip(
            predictor._feature_names,
            predictor.model.feature_importances_
        ))

        # Sort by importance
        sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)

        feature_names = [f[0] for f in sorted_features]
        feature_values = [f[1] for f in sorted_features]

        fig = go.Figure(go.Bar(
            x=feature_values,
            y=feature_names,
            orientation='h',
            marker_color='lightblue'
        ))

        fig.update_layout(
            xaxis_title="Importance Score",
            yaxis_title="Feature",
            height=300
        )

        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Higher scores indicate features that contribute more to predictions. "
            "Significant changes in feature importance may indicate data distribution shifts."
        )
```

**UI placement:** Add as new tab in existing Dashboard page (`pages/2_📊_Dashboard.py`) or create standalone `pages/5_🔬_Model_Health.py`.

### Pattern 4: Automated Retraining Trigger
**What:** Automatically suggest or trigger retraining when drift threshold exceeded
**When to use:** After drift detection runs (MONTR-02)
**Example:**
```python
# Source: Automated retraining best practices + existing retraining_ui pattern
from typing import Optional
import time

def check_and_trigger_retraining(session_id: str, auto_retrain: bool = False) -> Optional[dict]:
    """
    Check for drift and optionally trigger automated retraining.

    Args:
        session_id: Session that just completed
        auto_retrain: If True, automatically retrain on drift (default: False, alert only)

    Returns:
        Dict with drift status and retraining result (if triggered), or None
    """
    detector = DriftDetector()
    drift_status = detector.check_session_drift(session_id)

    if not drift_status.get('has_drift'):
        return None  # No drift, no action

    consecutive = drift_status.get('consecutive_drift_sessions', 0)

    # Retraining policy: auto-retrain if 3+ consecutive drift sessions
    should_retrain = consecutive >= 3

    if should_retrain and auto_retrain:
        logger.info(f"Auto-retraining triggered: {consecutive} consecutive drift sessions")

        start_time = time.time()

        try:
            predictor = DistancePredictor()
            df = golf_db.get_all_shots()

            # Train with intervals if enough data
            if HAS_MAPIE and len(df) >= 1000:
                new_metadata = predictor.train_with_intervals(df=df, save=True)
            else:
                new_metadata = predictor.train(df=df, save=True)

            elapsed = time.time() - start_time

            drift_status['retraining_triggered'] = True
            drift_status['retraining_success'] = True
            drift_status['new_mae'] = new_metadata.metrics['mae']
            drift_status['retraining_time'] = elapsed

            logger.info(
                f"Auto-retraining completed: MAE {new_metadata.metrics['mae']:.2f} yards ({elapsed:.1f}s)"
            )

        except Exception as e:
            drift_status['retraining_triggered'] = True
            drift_status['retraining_success'] = False
            drift_status['retraining_error'] = str(e)

            logger.error(f"Auto-retraining failed: {e}")

    elif should_retrain:
        # Alert only (manual retraining)
        drift_status['retraining_recommended'] = True
        drift_status['alert_message'] = (
            f"🚨 Model drift detected for {consecutive} sessions. "
            "Visit Model Health dashboard to retrain."
        )

    return drift_status
```

**Integration:** Call `check_and_trigger_retraining(session_id, auto_retrain=False)` at end of `update_session_metrics()`. Display alert in UI if drift detected. User can enable auto-retraining in settings.

**Policy rationale:** 3-session threshold prevents retraining on single outlier sessions while catching sustained drift. Auto-retraining is opt-in (default: alert only) to give users control.

### Anti-Patterns to Avoid

- **Anti-pattern: Fixed MAE threshold (e.g., "always retrain at MAE > 10 yards")**
  - Problem: Doesn't account for user skill improvement or seasonal variance
  - Solution: Use adaptive baseline (median of last 20 sessions)

- **Anti-pattern: Logging predictions for every shot synchronously**
  - Problem: Slows down shot import, blocks UI
  - Solution: Batch predictions per session, log asynchronously after import completes

- **Anti-pattern: Retraining on every drift alert**
  - Problem: Over-retraining wastes compute, may fit to noise
  - Solution: Require 3 consecutive drift sessions before auto-retraining

- **Anti-pattern: Using Kolmogorov-Smirnov test for drift detection**
  - Problem: Detects input distribution changes, not prediction quality degradation
  - Solution: Use prediction error (MAE/RMSE) which directly measures what users care about

- **Anti-pattern: Storing full prediction history in memory**
  - Problem: Memory consumption grows unbounded
  - Solution: Persist to SQLite, query with LIMIT for dashboard (e.g., last 50 sessions)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drift detection algorithms | Custom statistical tests from scratch | MAE tracking with adaptive baseline (Pattern 2) | Proven approach, interpretable, doesn't require complex statistics |
| Performance dashboards | Custom HTML/CSS charts | Plotly + Streamlit components (Pattern 3) | Interactive, consistent with existing UI, maintained by community |
| Prediction logging | Custom CSV files or JSON exports | SQLite table with indexes (Pattern 1) | Queryable, integrates with existing database, handles concurrency |
| Baseline computation | Moving average or exponential smoothing | Median of last N sessions (Pattern 2) | Robust to outliers, simple to explain to users |

**Key insight:** Offline-first constraint means we can't use cloud monitoring services (Evidently AI, Grafana, etc.). All drift history must be stored locally in SQLite and rendered in Streamlit. This is actually simpler than integrating external services.

## Common Pitfalls

### Pitfall 1: False Alarms from Normal Variance
**What goes wrong:** Drift alerts fire on every slightly-above-average session
**Why it happens:** Fixed threshold doesn't account for natural session variance
**How to avoid:** Use adaptive baseline (median of last 20 sessions) and percentage threshold (30%), not absolute yards threshold
**Warning signs:** Users ignore drift alerts because they're too frequent
**Validation:** Track false alarm rate (alerts that don't correspond to actual model degradation)

### Pitfall 2: Insufficient Baseline History
**What goes wrong:** Drift detection triggers too early (e.g., after only 3 sessions)
**Why it happens:** Baseline computed from too few sessions isn't stable
**How to avoid:** Require minimum 10 sessions before computing baseline, show "building baseline" message until then
**Warning signs:** Drift alerts on first few sessions after model training
**Validation:** Check baseline MAE stability (should not change >5% when adding new session to 20-session window)

### Pitfall 3: Not Handling Missing Predictions
**What goes wrong:** Drift check crashes when no predictions logged for session
**Why it happens:** Predictions only logged if model exists and shot has valid carry data
**How to avoid:** Check prediction count before computing drift, skip drift check if <5 predictions
**Warning signs:** Error logs on `check_session_drift()` calls
**Validation:** Test with sessions containing only putting/chipping (no carry data)

### Pitfall 4: Over-Retraining on Transient Drift
**What goes wrong:** Model retrains after one bad session, then performs worse
**Why it happens:** Single outlier session isn't representative of true drift
**How to avoid:** Require 3 consecutive drift sessions before auto-retraining
**Warning signs:** Frequent retraining (e.g., weekly) with no MAE improvement
**Validation:** Track retraining frequency and MAE improvement after retraining

### Pitfall 5: Ignoring Feature Importance Changes
**What goes wrong:** Feature importance shifts dramatically but drift not detected
**Why it happens:** MAE stays stable but model is learning wrong patterns
**How to avoid:** Display feature importance in dashboard, alert on >50% change in top feature
**Warning signs:** Predictions feel wrong to user but MAE is normal
**Validation:** Compare feature importance between model versions, flag large shifts

## Code Examples

Verified patterns from official sources and codebase:

### Database Schema
```sql
-- Source: Existing golf_db.py table patterns + monitoring best practices
CREATE TABLE IF NOT EXISTS model_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shot_id TEXT NOT NULL,
    club TEXT,
    predicted_value REAL,
    actual_value REAL,
    absolute_error REAL,
    model_version TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shot_id) REFERENCES shots(shot_id)
);

CREATE INDEX IF NOT EXISTS idx_predictions_shot ON model_predictions(shot_id);
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON model_predictions(timestamp);

CREATE TABLE IF NOT EXISTS model_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    session_mae REAL,
    baseline_mae REAL,
    has_drift BOOLEAN,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_performance_session ON model_performance(session_id);
CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON model_performance(timestamp);
```

### MAE Computation
```python
# Source: Standard regression metrics + pandas operations
def compute_session_mae(session_id: str) -> Optional[float]:
    """
    Compute MAE for all predictions in a session.

    Returns:
        MAE in yards, or None if insufficient predictions
    """
    conn = sqlite3.connect(SQLITE_DB_PATH)
    df = pd.read_sql_query('''
        SELECT absolute_error
        FROM model_predictions
        WHERE shot_id IN (
            SELECT shot_id FROM shots WHERE session_id = ?
        )
    ''', conn, params=(session_id,))
    conn.close()

    if df.empty or len(df) < 5:
        return None

    return df['absolute_error'].mean()
```

### Drift Alert UI Component
```python
# Source: Existing Streamlit alert patterns
def render_drift_alert(drift_status: dict):
    """Render drift alert banner in UI."""
    if not drift_status or not drift_status.get('has_drift'):
        return

    consecutive = drift_status.get('consecutive_drift_sessions', 0)
    session_mae = drift_status.get('session_mae', 0)
    baseline_mae = drift_status.get('baseline_mae', 0)

    if consecutive >= 3:
        st.error(
            f"🚨 **Model Drift Alert**\n\n"
            f"Prediction error has been elevated for {consecutive} sessions.\n\n"
            f"- Current MAE: {session_mae:.1f} yards\n"
            f"- Baseline MAE: {baseline_mae:.1f} yards\n\n"
            f"**Action:** Retrain model on Model Health dashboard"
        )
    else:
        st.warning(
            f"⚠️ Elevated prediction error detected "
            f"(MAE {session_mae:.1f} vs baseline {baseline_mae:.1f})"
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed error thresholds | Adaptive baselines | 2024+ | Reduced false alarms, better seasonal adjustment |
| Statistical distribution tests (K-S, Chi-Square) | Prediction error monitoring (MAE/RMSE) | 2023+ | Direct measurement of what matters (prediction quality) |
| Manual periodic retraining | Drift-triggered automated retraining | 2025+ | Proactive response to degradation, reduced maintenance |
| Cloud-only monitoring dashboards | Local-first Streamlit dashboards | 2026 | Offline capability, no API dependencies |

**Deprecated/outdated:**
- Kolmogorov-Smirnov test for concept drift: Only detects input distribution changes, not prediction degradation
- Fixed thresholds (e.g., "retrain when MAE > 10 yards"): Ignores variance and baseline performance
- Real-time streaming drift detection: Overkill for batch golf session data; session-level checks sufficient

## Open Questions

1. **Prediction Logging Performance Impact**
   - What we know: Logging per shot could slow import, but batch logging at session-end is feasible
   - What's unclear: Actual latency impact on Uneekor scraper workflow
   - Recommendation: Implement async logging after session import completes, measure impact

2. **Optimal Drift Threshold Percentage**
   - What we know: 30% is research recommendation for adaptive thresholds
   - What's unclear: Whether 30% is appropriate for golf data (typical variance may be higher/lower)
   - Recommendation: Start with 30%, make configurable in settings, track false alarm rate after 50+ sessions

3. **Feature Importance Drift Detection**
   - What we know: Dramatic shifts in feature importance can indicate data quality issues
   - What's unclear: What percentage change should trigger alert? Top 1 feature or top 3?
   - Recommendation: Phase 4 displays feature importance but doesn't alert on it; defer alerting to Phase 5 based on user feedback

## Sources

### Primary (HIGH confidence)
- [Model Retraining Best Practices](https://research.aimultiple.com/model-retraining/) - 2026 guide on trigger strategies
- [Automated Retraining](https://www.sei.cmu.edu/blog/improving-automated-retraining-of-machine-learning-models/) - CMU SEI best practices
- [ML Model Monitoring](https://www.evidentlyai.com/ml-in-production/model-monitoring) - Comprehensive monitoring guide
- [Drift Detection Methods](https://labelyourdata.com/articles/machine-learning/data-drift) - Statistical tests vs error monitoring
- [Datadog ML Monitoring](https://www.datadoghq.com/blog/ml-model-monitoring-in-production-best-practices/) - Production monitoring patterns
- [MAE vs RMSE Metrics](https://apxml.com/courses/time-series-analysis-forecasting/chapter-6-model-evaluation-selection/evaluation-metrics-mae-mse-rmse) - Error metric selection

### Secondary (MEDIUM confidence)
- [Streamlit Dashboard Tutorial](https://www.evidentlyai.com/blog/ml-model-monitoring-dashboard-tutorial) - Evidently AI + Streamlit patterns
- [XGBoost Feature Importance](https://machinelearningmastery.com/feature-importance-and-feature-selection-with-xgboost-in-python/) - Feature importance interpretation
- [Adaptive Thresholds](https://magai.co/how-to-detect-and-manage-model-drift-in-ai/) - Adaptive vs fixed thresholds

### Tertiary (LOW confidence, validation needed)
- Web search results on drift detection thresholds (2026) - General guidance, needs project-specific tuning
- Web search results on retraining frequency - Domain knowledge, not ML-specific

## Metadata

**Confidence breakdown:**
- MAE/RMSE tracking: HIGH - Standard regression metrics, well-documented
- Adaptive thresholds: HIGH - Research-backed, multiple sources confirm
- Dashboard implementation: HIGH - Existing Streamlit patterns, Plotly already in use
- Automated retraining triggers: MEDIUM - Policy choices (3 consecutive sessions) need validation

**Research date:** 2026-02-10
**Valid until:** 2026-03-10 (30 days - monitoring patterns are stable)

**Key dependencies verified:**
- All required libraries already installed (pandas, numpy, scipy, plotly, streamlit, sqlite3)
- No new external dependencies needed
- `session_stats` table exists (Phase 1)
- `update_session_metrics()` exists (Phase 1)
- Model metadata with MAE exists (Phase 3)
- Retraining UI exists (Phase 3)

**Implementation notes:**
- Phase 4 requires 2 new tables: `model_predictions`, `model_performance`
- Prediction logging integrates into `save_shot()` (one-line addition)
- Drift detection runs in `update_session_metrics()` (call `DriftDetector.check_session_drift()`)
- Dashboard can be new page or new tab in existing Dashboard
- Auto-retraining is opt-in via settings (default: alert only)
