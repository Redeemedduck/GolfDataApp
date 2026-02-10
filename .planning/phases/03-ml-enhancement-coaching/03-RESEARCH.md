# Phase 3: ML Enhancement & Coaching - Research

**Researched:** 2026-02-10
**Domain:** Conformal prediction, XGBoost tuning, personalized coaching systems
**Confidence:** HIGH

## Summary

Phase 3 enhances ML predictions with trustworthy confidence intervals using conformal prediction and builds intelligent coaching features that leverage Phase 2 analytics. The core technical challenge is integrating MAPIE (Model Agnostic Prediction Interval Estimator) with the existing XGBoost distance predictor while maintaining the offline-first, graceful degradation architecture.

Three key insights drive this phase: (1) Conformal prediction provides distribution-free confidence intervals with theoretical guarantees, making it ideal for golf shot data which lacks clear parametric distributions; (2) Small dataset XGBoost tuning requires aggressive regularization (higher lambda/alpha, lower max_depth, early stopping) to prevent overfitting on 2000-5000 shot datasets; (3) Context-aware coaching requires structured analytics integration where the coach references specific computed statistics, not generic templates.

The project already has strong foundations: XGBoost distance predictor with versioning (Phase 1), LocalCoach with intent detection and rule-based responses, and comprehensive analytics utilities (Phase 2). Phase 3 builds on these by wrapping predictions with MAPIE for intervals, tuning XGBoost for small datasets, and evolving LocalCoach from template-based to analytics-driven responses.

**Primary recommendation:** Use MAPIE's `CrossConformalRegressor` with cv-plus method for distance prediction intervals (95% confidence), tune XGBoost with higher regularization (lambda=2.0, alpha=1.0, max_depth=4), and build structured practice plan generation that consumes analytics outputs and weakness detection from Phase 2 components.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| MAPIE | 1.3.0+ | Conformal prediction intervals for XGBoost | HIGH confidence: scikit-learn-contrib official, 119 code snippets, model-agnostic |
| XGBoost | 2.0.0+ | Distance prediction (already installed) | Already in use; quantile regression support added in 2.0 |
| scikit-learn | 1.4+ | MAPIE dependency, train/test split, cross-validation | Already installed (1.3.0+); MAPIE requires >=1.4 |
| pandas | 2.x | Analytics data manipulation | Already in use; foundation for coaching context |
| numpy | 1.23+ | Array operations, confidence interval calculations | Already in use; MAPIE requires >=1.23 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | 1.11+ | Statistical tests for confidence intervals | Already installed; validate coverage rates |
| joblib | 1.3.0+ | Model serialization including MAPIE wrappers | Already installed; save/load wrapped predictors |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| MAPIE | XGBoost quantile regression | MAPIE provides distribution-free guarantees; quantile regression assumes parametric form |
| CrossConformalRegressor | JackknifeAfterBootstrap | Jackknife+ faster but cv-plus has better coverage for small datasets |
| Structured plan generation | LLM-based generation | Offline-first constraint requires structured approach; LLM adds API dependency |

**Installation:**
```bash
# Add to requirements.txt
mapie>=1.3.0
scipy>=1.11.0  # Already present

# Upgrade if needed (MAPIE requires sklearn>=1.4)
pip install --upgrade scikit-learn>=1.4.0
```

## Architecture Patterns

### Recommended Module Structure
```
ml/
├── predictors.py           # Extend DistancePredictor with MAPIE wrapper
├── train_models.py         # Add conformal_train() for MAPIE-wrapped models
├── coaching/
│   ├── __init__.py
│   ├── practice_planner.py  # Structured practice plan generation
│   └── weakness_mapper.py   # Map analytics outputs to drills
├── tuning.py               # XGBoost hyperparameter tuning for small datasets

local_coach.py              # Extend with analytics-driven responses
components/
├── prediction_interval.py  # UI component for interval visualization
└── retraining_ui.py        # Model retraining trigger component

pages/4_🤖_AI_Coach.py       # Extend with practice plan generation
```

### Pattern 1: MAPIE Wrapper for XGBoost Predictor
**What:** Wrap existing XGBoost distance predictor with MAPIE for confidence intervals
**When to use:** Distance prediction (COACH-03)
**Example:**
```python
# Source: Context7 MAPIE documentation + existing predictors.py pattern
from mapie.regression import CrossConformalRegressor
from ml.train_models import DistancePredictor, prepare_features
import numpy as np

class DistancePredictorWithIntervals(DistancePredictor):
    """
    Extended distance predictor with conformal prediction intervals.

    Wraps XGBoost model with MAPIE for distribution-free confidence intervals.
    """

    def __init__(self, confidence_level: float = 0.95):
        super().__init__()
        self.confidence_level = confidence_level
        self.mapie_model = None

    def train_with_intervals(self, df: pd.DataFrame, save: bool = True):
        """
        Train XGBoost model and wrap with MAPIE for confidence intervals.

        Uses cv-plus method (cross-validation with jackknife+) for better
        coverage on small datasets.
        """
        # Prepare data using existing pipeline
        X, y = prepare_features(df, target='carry')

        # Split: 70% train, 30% conformalization (MAPIE requires separate sets)
        from sklearn.model_selection import train_test_split
        X_train, X_conform, y_train, y_conform = train_test_split(
            X, y, test_size=0.3, random_state=42
        )

        # Train base XGBoost model (with small-dataset tuning)
        from xgboost import XGBRegressor
        base_model = XGBRegressor(
            n_estimators=100,
            max_depth=4,          # Reduced from 5 (small dataset)
            learning_rate=0.1,
            reg_lambda=2.0,       # L2 regularization (prevent overfitting)
            reg_alpha=1.0,        # L1 regularization (feature selection)
            subsample=0.8,        # Row sampling
            colsample_bytree=0.8, # Column sampling
            objective='reg:squarederror',
            random_state=42,
        )

        base_model.fit(X_train, y_train)

        # Wrap with MAPIE using cv-plus method
        self.mapie_model = CrossConformalRegressor(
            base_model,
            method="plus",        # Jackknife+ (conservative, good for small data)
            cv=5,                 # 5-fold CV
            confidence_level=self.confidence_level,
        )

        # Conformalize using held-out data
        self.mapie_model.fit_conformalize(X_conform, y_conform)

        # Store base model for feature importance
        self.model = base_model
        self._feature_names = list(X.columns)

        if save:
            self.save_with_intervals()

    def predict_with_intervals(self, **kwargs) -> dict:
        """
        Predict distance with confidence intervals.

        Returns:
            Dict with:
            - predicted_value: Point estimate
            - lower_bound: Lower CI bound
            - upper_bound: Upper CI bound
            - confidence_level: e.g., 0.95
            - interval_width: upper - lower
        """
        if not self.mapie_model:
            self.load()

        # Build feature array (reuse existing logic)
        features = self._build_feature_array(**kwargs)
        X = np.array([features])

        # Predict with intervals
        y_pred, y_pis = self.mapie_model.predict_interval(X)

        return {
            'predicted_value': float(y_pred[0]),
            'lower_bound': float(y_pis[0, 0]),
            'upper_bound': float(y_pis[0, 1]),
            'confidence_level': self.confidence_level,
            'interval_width': float(y_pis[0, 1] - y_pis[0, 0]),
            'feature_importance': self.get_feature_importance(),
        }
```

**Why cv-plus method:**
- Better coverage for small datasets than base method
- Jackknife+ is conservative (intervals slightly wider, guaranteed coverage)
- 5-fold CV provides good bias-variance tradeoff for 2000-5000 samples
- Source: [MAPIE documentation](https://mapie.readthedocs.io/), [AlgoTrading101 - Conformal Prediction Guide](https://algotrading101.com/learn/conformal-prediction-guide/)

### Pattern 2: XGBoost Regularization for Small Datasets
**What:** Tune XGBoost hyperparameters to prevent overfitting on 2000-5000 shots
**When to use:** Model retraining (MONTR-02 partial), distance prediction training
**Example:**
```python
# Source: XGBoost official docs + web research on small dataset tuning
def get_small_dataset_params(n_samples: int) -> dict:
    """
    Get XGBoost hyperparameters tuned for small datasets.

    Args:
        n_samples: Number of training samples

    Returns:
        Dict of hyperparameters with aggressive regularization
    """
    # Base parameters
    params = {
        'objective': 'reg:squarederror',
        'random_state': 42,
    }

    if n_samples < 1000:
        # Very small dataset: maximum regularization
        params.update({
            'n_estimators': 50,
            'max_depth': 3,
            'learning_rate': 0.05,
            'reg_lambda': 3.0,      # High L2
            'reg_alpha': 1.5,       # High L1
            'subsample': 0.7,       # Aggressive sampling
            'colsample_bytree': 0.7,
            'min_child_weight': 3,  # Prevent small leaves
        })
    elif n_samples < 3000:
        # Small dataset: strong regularization
        params.update({
            'n_estimators': 75,
            'max_depth': 4,
            'learning_rate': 0.08,
            'reg_lambda': 2.0,
            'reg_alpha': 1.0,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 2,
        })
    else:
        # Medium dataset: moderate regularization
        params.update({
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.1,
            'reg_lambda': 1.0,
            'reg_alpha': 0.5,
            'subsample': 0.8,
            'colsample_bytree': 0.9,
            'min_child_weight': 1,
        })

    return params

# Usage in training
def train_distance_model_tuned(df: pd.DataFrame) -> XGBRegressor:
    """Train XGBoost with small-dataset-aware hyperparameters."""
    X, y = prepare_features(df)

    params = get_small_dataset_params(len(X))

    model = XGBRegressor(**params)

    # Early stopping to prevent overfitting
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        early_stopping_rounds=10,
        verbose=False
    )

    return model
```

**Key regularization parameters:**
- `max_depth`: Lower depth (3-5) prevents memorizing training data
- `reg_lambda` (L2): Penalizes large weights, smooths predictions (1.0-3.0)
- `reg_alpha` (L1): Drives weights to zero, performs feature selection (0.5-1.5)
- `subsample`/`colsample_bytree`: Sample rows/cols to reduce overfitting (0.7-0.9)
- `min_child_weight`: Prevents tiny leaf nodes (1-3)
- Early stopping: Stops when validation error increases
- Source: [XGBoost Parameter Tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [XGBoost Robust to Small Datasets](https://xgboosting.com/xgboost-robust-to-small-datasets/)

### Pattern 3: Analytics-Driven Coaching Responses
**What:** LocalCoach generates responses by querying Phase 2 analytics, not templates
**When to use:** COACH-01 (context-aware coaching)
**Example:**
```python
# Source: existing local_coach.py + Phase 2 analytics components
from analytics.utils import calculate_distance_stats, filter_outliers_iqr
from components.miss_tendency import classify_shot_shapes
from components.session_quality import calculate_session_quality

class LocalCoach:
    """Extended with analytics-driven responses."""

    def get_club_analysis_response(self, club: str) -> CoachResponse:
        """
        Generate response with actual analytics data, not templates.

        Example output:
        "Your 7-iron dispersion is 18 yards (IQR). Your median carry is
        152 yards (148-156 range). You're hitting 65% straight, 30% fade.
        Focus on: Setup consistency to reduce dispersion."
        """
        df = golf_db.get_all_shots()
        club_df = df[df['club'] == club]

        if club_df.empty or len(club_df) < 5:
            return CoachResponse(
                message=f"Need at least 5 {club} shots for analysis (have {len(club_df)})",
                confidence=0.9
            )

        # Calculate actual stats using Phase 2 utilities
        distance_stats = calculate_distance_stats(club_df, club)

        # Dispersion (IQR of lateral distance)
        if 'side_total' in club_df.columns:
            side_clean = filter_outliers_iqr(club_df, 'side_total')
            dispersion_iqr = side_clean['side_total'].quantile(0.75) - side_clean['side_total'].quantile(0.25)
        else:
            dispersion_iqr = None

        # Miss tendency (using D-plane classification from Phase 2)
        shapes = classify_shot_shapes(club_df)
        shape_dist = shapes.value_counts(normalize=True)
        dominant_shape = shape_dist.idxmax()
        dominant_pct = shape_dist.max() * 100

        # Build response with actual numbers
        parts = [f"Your {club} analysis:"]

        if distance_stats:
            parts.append(
                f"  - Median carry: {distance_stats['median']:.0f} yards "
                f"({distance_stats['q25']:.0f}-{distance_stats['q75']:.0f} range)"
            )

        if dispersion_iqr:
            parts.append(f"  - Dispersion: {dispersion_iqr:.0f} yards (IQR)")

        parts.append(f"  - Shot shape: {dominant_pct:.0f}% {dominant_shape}")

        # Generate actionable suggestions based on actual data
        suggestions = []
        if dispersion_iqr and dispersion_iqr > 15:
            suggestions.append("High dispersion - focus on setup consistency")
        if dominant_shape in ['slice', 'fade'] and dominant_pct > 60:
            suggestions.append("Consistent fade pattern - work on face control")

        return CoachResponse(
            message="\n".join(parts),
            data={
                'distance_stats': distance_stats,
                'dispersion_iqr': dispersion_iqr,
                'shape_distribution': shape_dist.to_dict(),
            },
            suggestions=suggestions,
            confidence=0.85
        )
```

**Key principle:** No more generic templates like "Your driver is doing well!" Instead, reference specific computed metrics from analytics engine.

### Pattern 4: Structured Practice Plan Generation
**What:** Generate 15-30 min practice plans by mapping detected weaknesses to drills
**When to use:** COACH-02 (personalized practice plans)
**Example:**
```python
# Source: Research on ML recommendation systems + golf coaching domain knowledge
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Drill:
    """Single practice drill."""
    name: str
    duration_min: int
    focus: str           # "alignment", "tempo", "contact", etc.
    instructions: str
    reps: int

@dataclass
class PracticePlan:
    """Complete practice session plan."""
    duration_min: int
    drills: List[Drill]
    focus_areas: List[str]
    rationale: str       # Why these drills were chosen

class PracticePlanner:
    """
    Generate structured practice plans based on detected weaknesses.

    Uses Phase 2 analytics to identify weak areas and map to drills.
    """

    # Drill database (could be JSON file in future)
    DRILL_LIBRARY = {
        'high_dispersion': Drill(
            name="Alignment Stick Setup Drill",
            duration_min=10,
            focus="alignment",
            instructions="Place alignment sticks parallel to target line. "
                        "Hit 20 shots focusing on setup consistency.",
            reps=20,
        ),
        'fade_pattern': Drill(
            name="Face Control with Headcover",
            duration_min=15,
            focus="clubface_control",
            instructions="Place headcover 6 inches inside ball. Practice "
                        "in-to-out path without hitting headcover.",
            reps=15,
        ),
        'low_smash': Drill(
            name="Impact Tape Center Contact",
            duration_min=10,
            focus="contact",
            instructions="Use impact tape. Focus on center-face contact. "
                        "Track strike location.",
            reps=20,
        ),
        'inconsistent_distance': Drill(
            name="Tempo Drill with Metronome",
            duration_min=15,
            focus="tempo",
            instructions="Use metronome app (80 BPM). Match backswing and "
                        "downswing to beats. Focus on rhythm.",
            reps=15,
        ),
    }

    def generate_plan(self, target_duration: int = 30) -> PracticePlan:
        """
        Generate practice plan by analyzing user's shot data.

        Args:
            target_duration: Desired plan duration in minutes (15-30)

        Returns:
            Structured practice plan with drills and rationale
        """
        df = golf_db.get_all_shots()

        if df.empty:
            return self._default_plan()

        # Detect weaknesses using Phase 2 analytics
        weaknesses = self._detect_weaknesses(df)

        # Map weaknesses to drills
        selected_drills = []
        remaining_time = target_duration
        focus_areas = []

        for weakness, severity in sorted(weaknesses.items(), key=lambda x: x[1], reverse=True):
            if remaining_time < 10:
                break

            if weakness in self.DRILL_LIBRARY:
                drill = self.DRILL_LIBRARY[weakness]
                if drill.duration_min <= remaining_time:
                    selected_drills.append(drill)
                    focus_areas.append(drill.focus)
                    remaining_time -= drill.duration_min

        # Build rationale
        weakness_desc = [f"{w.replace('_', ' ')}" for w in list(weaknesses.keys())[:3]]
        rationale = (
            f"Detected primary issues: {', '.join(weakness_desc)}. "
            f"This plan targets your top weaknesses with proven drills."
        )

        return PracticePlan(
            duration_min=target_duration - remaining_time,
            drills=selected_drills,
            focus_areas=focus_areas,
            rationale=rationale,
        )

    def _detect_weaknesses(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Detect weaknesses by analyzing shot data.

        Returns:
            Dict of {weakness_key: severity_score (0-1)}
        """
        weaknesses = {}

        # High dispersion check (using Phase 2 analytics)
        for club in ['Driver', '7 Iron']:
            club_df = df[df['club'] == club]
            if len(club_df) >= 5:
                stats = calculate_distance_stats(club_df, club)
                if stats and stats['iqr'] > 15:
                    weaknesses['high_dispersion'] = min(1.0, stats['iqr'] / 25)

        # Miss pattern check (using Phase 2 shot shape classification)
        shapes = classify_shot_shapes(df)
        shape_counts = shapes.value_counts(normalize=True)
        if 'fade' in shape_counts and shape_counts['fade'] > 0.6:
            weaknesses['fade_pattern'] = shape_counts['fade']

        # Low smash factor check
        if 'smash' in df.columns:
            avg_smash = df['smash'].replace([0, 99999], np.nan).mean()
            if avg_smash < 1.40:
                weaknesses['low_smash'] = 1.0 - (avg_smash / 1.45)

        # Distance consistency check
        if 'carry' in df.columns:
            carry_cv = df['carry'].replace([0, 99999], np.nan).std() / df['carry'].replace([0, 99999], np.nan).mean()
            if carry_cv > 0.08:  # CV > 8%
                weaknesses['inconsistent_distance'] = min(1.0, carry_cv / 0.15)

        return weaknesses
```

**Design rationale:**
- Structured drills (not LLM-generated) maintain offline-first constraint
- Drill library is extensible (add more drills as JSON/database)
- Severity scoring prioritizes most impactful weaknesses
- Drills are time-boxed and rep-based (concrete action items)
- Source: [GPT4Rec - Generative Recommendations](https://www.amazon.science/publications/gpt4rec-a-generative-framework-for-personalized-recommendation-and-user-interests-interpretation)

### Anti-Patterns to Avoid

- **Anti-pattern: Using raw XGBoost predictions without intervals**
  - Problem: Users can't assess prediction reliability
  - Solution: Always wrap with MAPIE for confidence intervals (COACH-03)

- **Anti-pattern: Template-based coaching responses**
  - Problem: Generic advice not actionable ("Your driver is good!")
  - Solution: Reference specific analytics metrics in responses (COACH-01)

- **Anti-pattern: Overfitting on small datasets**
  - Problem: Model memorizes training data, poor generalization
  - Solution: Use regularization params tuned for dataset size (Pattern 2)

- **Anti-pattern: Trying to train MAPIE without conformalization set**
  - Problem: MAPIE requires separate conformalization data
  - Solution: Always split data (70% train, 30% conformalize) before MAPIE

- **Anti-pattern: LLM-generated practice plans**
  - Problem: Requires API, breaks offline-first constraint
  - Solution: Use structured drill database with weakness mapping (Pattern 4)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Confidence intervals | Custom bootstrap/percentile methods | MAPIE `CrossConformalRegressor` | Theoretical coverage guarantees, handles non-normal distributions, model-agnostic |
| Hyperparameter tuning | Manual trial-and-error | Grid search with small-dataset params (Pattern 2) | Systematic exploration, early stopping prevents overfitting |
| Practice plan generation | Rule-based if/else trees | Structured drill library + weakness scoring (Pattern 4) | Extensible, maintainable, separates detection from prescription |
| Prediction interval visualization | Custom matplotlib uncertainty plots | Streamlit + Plotly with shaded intervals | Interactive hover, matches existing UI patterns |

**Key insight:** Conformal prediction solves the "how reliable is this prediction?" problem without assuming parametric distributions. Don't build custom confidence interval methods when MAPIE provides distribution-free guarantees.

## Common Pitfalls

### Pitfall 1: MAPIE Conformalization Set Too Small
**What goes wrong:** Confidence intervals too narrow, poor coverage (< 95%)
**Why it happens:** MAPIE needs sufficient conformalization samples (30%+ of data)
**How to avoid:** Always use 30% split for conformalization (70% train, 30% conform)
**Warning signs:** Coverage < 90% on test set, intervals suspiciously tight
**Validation:** Check empirical coverage on held-out test set

### Pitfall 2: Overfitting XGBoost on Small Datasets
**What goes wrong:** Model has 100% training accuracy but poor test accuracy
**Why it happens:** Default XGBoost params designed for large datasets (10k+ samples)
**How to avoid:** Use Pattern 2 (small-dataset regularization params), always use early stopping
**Warning signs:** Train MAE < 2 yards but test MAE > 10 yards, feature importance dominated by noise features
**Validation:** Check train vs test MAE gap; gap > 5 yards indicates overfitting

### Pitfall 3: Context-Free Coaching Responses
**What goes wrong:** Coach says "Your 7-iron is inconsistent" without specifics
**Why it happens:** Falling back to templates instead of computing actual metrics
**How to avoid:** Always query analytics before generating response (Pattern 3)
**Warning signs:** User asks "how inconsistent?" and coach can't answer with numbers
**Validation:** Every coaching response should cite at least one specific metric

### Pitfall 4: Practice Plans Not Actionable
**What goes wrong:** Plan says "work on alignment" without specific drill/reps
**Why it happens:** LLM-style vague instructions instead of structured drills
**How to avoid:** Use Pattern 4 (structured Drill objects with reps, time, instructions)
**Warning signs:** User asks "how do I do that?" after reading plan
**Validation:** Every drill has duration_min, reps, and step-by-step instructions

### Pitfall 5: Ignoring MAPIE scikit-learn Version Requirement
**What goes wrong:** MAPIE import fails with scikit-learn 1.3.x
**Why it happens:** MAPIE 1.3+ requires scikit-learn >= 1.4
**How to avoid:** Upgrade scikit-learn to 1.4+ before installing MAPIE
**Warning signs:** `ImportError: cannot import name '...' from 'sklearn'`
**Validation:** Check `sklearn.__version__ >= '1.4.0'` before MAPIE import

## Code Examples

Verified patterns from official sources:

### MAPIE Basic Workflow
```python
# Source: MAPIE GitHub - tutorial_regression.ipynb
from mapie.regression import CrossConformalRegressor
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split

# Split data
X_train, X_conform, y_train, y_conform = train_test_split(
    X, y, test_size=0.3, random_state=42
)

# Train base model
base_model = XGBRegressor(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    reg_lambda=2.0,
    reg_alpha=1.0,
)
base_model.fit(X_train, y_train)

# Wrap with MAPIE
mapie = CrossConformalRegressor(
    base_model,
    method="plus",
    cv=5,
    confidence_level=0.95,
)
mapie.fit_conformalize(X_conform, y_conform)

# Predict with intervals
y_pred, y_pis = mapie.predict_interval(X_test)

# y_pred: point estimates
# y_pis: shape (n_samples, 2) with [lower_bound, upper_bound]
```

### XGBoost Early Stopping
```python
# Source: XGBoost official parameter tuning docs
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split

X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = XGBRegressor(
    n_estimators=100,
    max_depth=4,
    reg_lambda=2.0,
    reg_alpha=1.0,
)

model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    early_stopping_rounds=10,
    verbose=False
)

print(f"Best iteration: {model.best_iteration}")
```

### Prediction Interval Visualization
```python
# Source: Streamlit + Plotly patterns (existing codebase)
import streamlit as st
import plotly.graph_objects as go

def render_prediction_with_intervals(
    club: str,
    point_estimate: float,
    lower_bound: float,
    upper_bound: float,
    confidence_level: float = 0.95,
):
    """Render prediction with confidence interval."""

    st.subheader(f"{club} Distance Prediction")

    # Text display
    st.metric(
        "Predicted Carry",
        f"{point_estimate:.0f} yards",
        delta=f"±{(upper_bound - lower_bound) / 2:.0f} yards",
    )

    st.caption(
        f"{confidence_level * 100:.0f}% confidence interval: "
        f"{lower_bound:.0f}-{upper_bound:.0f} yards"
    )

    # Visual representation
    fig = go.Figure()

    # Point estimate
    fig.add_trace(go.Scatter(
        x=[point_estimate],
        y=[1],
        mode='markers',
        marker=dict(size=12, color='blue'),
        name='Prediction',
    ))

    # Confidence interval
    fig.add_shape(
        type="line",
        x0=lower_bound, x1=upper_bound,
        y0=1, y1=1,
        line=dict(color="lightblue", width=8),
    )

    fig.update_layout(
        xaxis_title="Carry Distance (yards)",
        yaxis_visible=False,
        showlegend=False,
        height=150,
    )

    st.plotly_chart(fig, use_container_width=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bootstrapped percentiles for CI | Conformal prediction (MAPIE) | 2020+ | Distribution-free guarantees, better coverage |
| Single point predictions | Prediction intervals standard | 2023+ | Users understand uncertainty |
| Template-based coaching | Analytics-driven responses | 2024+ (GPT4Rec, RAG) | Personalized, actionable advice |
| Manual hyperparameter tuning | Optuna/GridSearch with early stopping | 2022+ | Systematic, reproducible tuning |
| LLM-generated plans | Structured recommendation systems | 2025+ | Offline-first, deterministic |

**Deprecated/outdated:**
- Bootstrapped confidence intervals: MAPIE provides better guarantees
- Mean ± 2*std for prediction intervals: Assumes normality (golf data is not normal)
- Generic coaching templates: Modern systems use context-aware generation

## Open Questions

1. **MAPIE Performance on Ultra-Small Datasets (<1000 shots)**
   - What we know: MAPIE requires conformalization set (30% of data), so 1000 shots → 300 for conformalization
   - What's unclear: Does MAPIE maintain 95% coverage with < 1000 total samples?
   - Recommendation: Implement with minimum sample check (require 1000+ shots for intervals), fall back to "not enough data" message otherwise

2. **Model Retraining Trigger Threshold**
   - What we know: Drift detection should compare prediction vs actual
   - What's unclear: What MAE increase (yards) should trigger retraining? 5 yards? 10 yards?
   - Recommendation: Start with 10 yards (>10% error for typical 100-150 yard shots), make configurable

3. **Drill Library Expansion**
   - What we know: Structured drill database works for offline-first
   - What's unclear: How to scale beyond 10-20 drills without manual curation?
   - Recommendation: Phase 3 uses curated 10-drill library, Phase 4+ could add JSON import or community contributions

## Sources

### Primary (HIGH confidence)
- [MAPIE Documentation](https://mapie.readthedocs.io/) - Official docs, API reference
- [MAPIE GitHub - tutorial_regression.ipynb](https://github.com/scikit-learn-contrib/MAPIE) - Working code examples
- Context7: `/scikit-learn-contrib/mapie` - 119 code snippets, HIGH reputation
- [XGBoost Parameter Tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) - Official tuning guide
- [XGBoost Robust to Small Datasets](https://xgboosting.com/xgboost-robust-to-small-datasets/) - Small dataset best practices

### Secondary (MEDIUM confidence)
- [AlgoTrading101 - Conformal Prediction Guide](https://algotrading101.com/learn/conformal-prediction-guide/) - MAPIE tutorial with examples
- [Conformalized Quantile Regression with XGBoost 2.0](https://medium.com/@newhardwarefound/conformalized-quantile-regression-with-xgboost-2-0-e70bbc939f6b) - Alternative approach comparison
- [Model Context Protocol](https://mixpanel.com/blog/model-context-protocol/) - Context-aware analytics integration patterns
- [GPT4Rec - Generative Recommendations](https://www.amazon.science/publications/gpt4rec-a-generative-framework-for-personalized-recommendation-and-user-interests-interpretation) - Personalized recommendation systems

### Tertiary (LOW confidence, validation needed)
- Web search results on LLM coaching practices (2026) - General trends, needs project-specific validation
- Web search results on practice plan generation - Domain knowledge, not ML-specific

## Metadata

**Confidence breakdown:**
- MAPIE integration: HIGH - Official docs, verified code examples, clear API
- XGBoost tuning: HIGH - Official docs, multiple sources confirm small-dataset params
- Practice plan generation: MEDIUM - Pattern is sound but drill effectiveness needs domain validation
- Analytics-driven coaching: HIGH - Clear pattern from existing analytics (Phase 2)

**Research date:** 2026-02-10
**Valid until:** 2026-03-10 (30 days - MAPIE/XGBoost are stable libraries)

**Key dependencies verified:**
- MAPIE requires scikit-learn >= 1.4 (current: 1.3.0+, upgrade needed)
- MAPIE requires numpy >= 1.23 (current: satisfied)
- XGBoost 2.0+ already installed
- All other dependencies already present (scipy, pandas, plotly, joblib)

**Implementation notes:**
- Phase 3 does NOT require new database tables (uses existing shots + analytics from Phase 2)
- MAPIE models can be serialized with joblib (same as XGBoost)
- Practice plan drill library starts small (10 drills), expand in Phase 4 if needed
- Model retraining UI can reuse existing Streamlit patterns (buttons, progress bars)
