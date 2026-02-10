# Stack Research: Local AI/ML Golf Analytics

**Researched:** 2026-02-10
**Context:** Adding enhanced local ML capabilities to existing Python/Streamlit golf analytics app

---

## Current Stack (Already In Use)

| Component | Version | Status |
|-----------|---------|--------|
| Python | 3.10-3.12 | Stable, CI tested |
| Streamlit | 1.x | Core UI framework |
| scikit-learn | >=1.3.0 | Classification, anomaly detection |
| XGBoost | >=2.0.0 | Distance prediction |
| joblib | >=1.3.0 | Model serialization |
| pandas/numpy | Current | Data manipulation |
| plotly | Current | Visualization |
| SQLite | Built-in | Primary data store |

---

## Recommended Additions

### Model Management & Versioning

**MLflow (Lightweight Mode)** — Confidence: HIGH
- **What:** Model tracking, versioning, and experiment logging
- **Why:** No model versioning currently exists. MLflow's lightweight file-based tracking works without a server
- **Version:** mlflow>=2.10 (2025+)
- **Use case:** Track model metrics, parameters, and artifacts per training run
- **Alternative considered:** DVC — overkill for single-user app, requires Git LFS setup
- **What NOT to use:** Weights & Biases — cloud-dependent, violates offline-first constraint

### Prediction Uncertainty

**MAPIE** — Confidence: HIGH
- **What:** Model-agnostic prediction intervals for scikit-learn and XGBoost
- **Why:** Current predictions show point estimates with no confidence. MAPIE wraps existing models to produce prediction intervals
- **Version:** mapie>=0.8
- **Use case:** "Your 7-iron carry: 148-156 yards (80% confidence)"
- **Alternative considered:** Quantile regression in XGBoost — works but MAPIE is simpler and model-agnostic

### Model Explainability

**SHAP** — Confidence: HIGH
- **What:** SHapley Additive exPlanations for feature importance and prediction explanations
- **Why:** Users need to understand WHY the AI recommends something. SHAP explains individual predictions
- **Version:** shap>=0.44
- **Use case:** "Recommended 7-iron because: club speed (+5y), wind (-3y), uphill (-2y)"
- **What NOT to use:** LIME — less stable, harder to interpret for tabular data

### Statistical Analysis

**scipy.stats** — Confidence: HIGH
- **What:** Statistical tests for drift detection, significance testing
- **Why:** Already a transitive dependency (via scikit-learn). Needed for Kolmogorov-Smirnov drift tests, t-tests for progress significance
- **Version:** Already installed
- **Use case:** Detect when model predictions drift from actuals, validate that improvement trends are statistically significant

### Data Validation

**pydantic** — Confidence: MEDIUM
- **What:** Data validation and schema enforcement
- **Why:** Current sentinel handling (99999) is scattered. Pydantic enforces valid ranges at data entry
- **Version:** pydantic>=2.0
- **Use case:** Validate shot data before training: `club_speed: confloat(gt=0, lt=200)`
- **Alternative considered:** dataclasses + manual validation — works but more boilerplate

---

## Libraries to AVOID

| Library | Why Avoid |
|---------|-----------|
| **TensorFlow/PyTorch** | Overkill for tabular data. XGBoost/sklearn outperform deep learning on structured data at this scale |
| **Weights & Biases** | Cloud-dependent experiment tracking. Violates offline-first constraint |
| **LangChain** | For LLM orchestration — not needed for local ML coaching |
| **Hugging Face Transformers** | NLP models too heavy for local coaching. Template + rules are better |
| **Ray/Dask** | Distributed computing — dataset is 2000-5000 rows, single-threaded is fine |
| **Great Expectations** | Data quality framework — too heavyweight for personal app. Pydantic sufficient |

---

## Dependency Strategy

### Tiers
1. **Core (required):** streamlit, pandas, numpy, plotly, sqlite3
2. **Enhanced (recommended):** scikit-learn, xgboost, joblib, shap, mapie
3. **Optional (nice-to-have):** mlflow, pydantic
4. **Cloud (soft dependency):** supabase, google-generativeai

### Installation
```
# Core
pip install streamlit pandas numpy plotly

# Enhanced ML
pip install scikit-learn xgboost joblib shap mapie

# Optional
pip install mlflow pydantic
```

### Graceful Degradation
All Enhanced/Optional packages must follow the existing pattern:
```python
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
```

---

## Build Tool Recommendations

| Tool | Purpose | Already Have? |
|------|---------|---------------|
| pytest | Better test runner for ML tests (parametrize, fixtures) | Compatible (unittest works) |
| freezegun | Time mocking for rate limiter tests | No — add |
| hypothesis | Property-based testing for data validation | No — optional |

---
*Stack research completed: 2026-02-10*
