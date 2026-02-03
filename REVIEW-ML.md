# ML/AI Review Findings

Scope:
- ml/
- services/ai/

## Findings

### High
- ml/train_models.py:118-121
  - joblib.load is used to load a model from disk without any trust boundary checks. If the model path is user-controlled or can be replaced on disk, this allows arbitrary code execution via pickle payloads.
  - Recommendation: only load models from trusted paths, verify file hashes/signatures, or switch to a safe serialization format.

### Medium
- ml/train_models.py:314-388
  - `DistancePredictor.load()` does not guarantee `_feature_names` is set when metadata is missing or corrupted, but `predict()` iterates over `_feature_names`. This can raise a `TypeError`/`AttributeError` at runtime.
  - Recommendation: validate metadata on load and fall back to a known feature list or raise a clear error before prediction.

- ml/classifiers.py:321-324
  - `prediction.lower()` assumes labels are strings. If the model was trained with enums or non-string labels, this will raise `AttributeError` and classification fails.
  - Recommendation: normalize labels during training or map predictions via a safe string conversion.

### Low
- ml/train_models.py:366-403
  - `predict()` sets defaults for missing inputs before computing `confidence`, so `confidence` will always be 1.0. This is misleading and defeats the stated intent of “feature availability.”
  - Recommendation: compute confidence from the originally provided inputs (before defaulting).

- ml/classifiers.py:265-266
  - Reported `accuracy` is measured on the training set only, which is overly optimistic and can mislead users.
  - Recommendation: report validation accuracy (train/test split or cross-validation) or label it explicitly as training accuracy.

- ml/anomaly_detection.py:391-407
  - The ML anomaly score is not normalized before averaging with the rule-based score (0–1). IsolationForest scores are unbounded and can dominate the combined score, making comparisons inconsistent.
  - Recommendation: normalize `ml_score` to a 0–1 range (e.g., min/max or percentile scaling) before combining.

- services/ai/registry.py:32-33
  - `get_provider()` is annotated to return `ProviderSpec` but returns `None` when not found. This can propagate `None` unexpectedly and cause runtime errors.
  - Recommendation: return `Optional[ProviderSpec]` or raise a KeyError for missing providers.

- services/ai/registry.py:15-24
  - `register_provider()` overwrites existing providers with the same ID without warning, which can hide accidental duplicates.
  - Recommendation: guard against duplicates or log/raise on re-registration.

- services/ai/providers/local_provider.py:50-60
  - Suggestions are interpolated into markdown without escaping. If suggestions can contain user-controlled content and the UI renders markdown as HTML, this can lead to injection risks.
  - Recommendation: escape or sanitize suggestion content before rendering.

## Notes
- No critical issues found in this pass.
- Files with no findings: `ml/__init__.py`, `services/ai/__init__.py`, `services/ai/providers/__init__.py`, `services/ai/providers/gemini_provider.py`.
