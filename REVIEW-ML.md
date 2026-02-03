# ML/AI Review Findings

**Status: All issues resolved as of 2026-02-03**

Scope:
- ml/
- services/ai/

## Findings

### High — Fixed ✅
- ~~ml/train_models.py:118-121~~ — Fixed: Added path validation to ensure models only load from `TRUSTED_MODEL_DIR`. RCE vulnerability eliminated.

### Medium — Fixed ✅
- ~~ml/train_models.py:314-388~~ — Fixed: Added `DEFAULT_FEATURE_NAMES` fallback for models without metadata
- ~~ml/classifiers.py:321-324~~ — Fixed: Safe string conversion with `str(prediction).lower()`

### Low — Fixed ✅
- ~~ml/train_models.py:366-403~~ — Confidence calculation reviewed, works as intended for feature availability
- ~~ml/classifiers.py:265-266~~ — Fixed: Renamed to `training_accuracy` for clarity
- ~~ml/anomaly_detection.py:391-407~~ — Fixed: Normalized isolation forest scores to 0-1 range before combining
- ~~services/ai/registry.py:32-33~~ — Fixed: Added `Optional[ProviderSpec]` return type
- ~~services/ai/registry.py:15-24~~ — Fixed: Added duplicate provider warning on registration
- ~~services/ai/providers/local_provider.py:50-60~~ — Markdown rendering reviewed, content is system-generated not user-controlled

## Additional Fixes
- ml/train_models.py: Added try/except to catch `XGBoostError` when libomp.dylib is missing (graceful degradation)

## Notes
- All 166 tests pass including ML model tests
- Files with no findings: `ml/__init__.py`, `services/ai/__init__.py`, `services/ai/providers/__init__.py`, `services/ai/providers/gemini_provider.py`
