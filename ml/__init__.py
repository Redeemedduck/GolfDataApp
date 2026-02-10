"""
ML Module for GolfDataApp.

Provides local machine learning models for:
- Distance prediction (carry/total based on launch conditions)
- Shot shape classification (draw, fade, straight, etc.)
- Swing flaw detection via anomaly detection

Feature Flags:
    ML_AVAILABLE: True if all ML dependencies are installed and importable
    ML_MISSING_DEPS: List of missing dependency descriptions (empty if all present)

Note: Some features require ML dependencies (scikit-learn, xgboost, joblib).
Rule-based classification and detection work without these dependencies.

Usage:
    import ml
    if ml.ML_AVAILABLE:
        predictor = ml.DistancePredictor()
        # Use ML features
    else:
        print(f"ML features unavailable: {ml.ML_MISSING_DEPS}")
"""

# Feature flags for ML availability
ML_AVAILABLE = True
ML_MISSING_DEPS = []

# Explicit imports with graceful degradation
# Import distance prediction models
try:
    from .train_models import (
        DistancePredictor,
        train_distance_model,
        load_model,
        save_model,
        HAS_MAPIE,
    )
except ImportError as e:
    DistancePredictor = None
    train_distance_model = None
    load_model = None
    save_model = None
    HAS_MAPIE = False
    ML_AVAILABLE = False
    if "xgboost" in str(e).lower():
        ML_MISSING_DEPS.append("xgboost")
    if "sklearn" in str(e).lower() or "scikit" in str(e).lower():
        ML_MISSING_DEPS.append("scikit-learn")
    if "joblib" in str(e).lower():
        ML_MISSING_DEPS.append("joblib")
    # Generic fallback if we can't determine specific package
    if not ML_MISSING_DEPS:
        ML_MISSING_DEPS.append("ML dependencies (xgboost, scikit-learn, joblib)")

# Import tuning utilities
try:
    from .tuning import get_small_dataset_params
except ImportError:
    get_small_dataset_params = None
    if ML_AVAILABLE:
        # ML deps present but tuning module missing (shouldn't happen)
        print("Warning: tuning module not available")

# Import shot shape classifiers
try:
    from .classifiers import (
        ShotShapeClassifier,
        ShotShape,
        classify_shot_shape,
    )
except ImportError as e:
    ShotShapeClassifier = None
    ShotShape = None
    classify_shot_shape = None
    ML_AVAILABLE = False
    if "sklearn" in str(e).lower() or "scikit" in str(e).lower():
        if "scikit-learn" not in ML_MISSING_DEPS:
            ML_MISSING_DEPS.append("scikit-learn")
    if "joblib" in str(e).lower():
        if "joblib" not in ML_MISSING_DEPS:
            ML_MISSING_DEPS.append("joblib")
    # Generic fallback
    if not ML_MISSING_DEPS:
        ML_MISSING_DEPS.append("ML dependencies (scikit-learn, joblib)")

# Import anomaly detection
try:
    from .anomaly_detection import (
        SwingFlawDetector,
        SwingFlaw,
        detect_swing_flaws,
    )
except ImportError as e:
    SwingFlawDetector = None
    SwingFlaw = None
    detect_swing_flaws = None
    ML_AVAILABLE = False
    if "sklearn" in str(e).lower() or "scikit" in str(e).lower():
        if "scikit-learn" not in ML_MISSING_DEPS:
            ML_MISSING_DEPS.append("scikit-learn")
    if "joblib" in str(e).lower():
        if "joblib" not in ML_MISSING_DEPS:
            ML_MISSING_DEPS.append("joblib")
    # Generic fallback
    if not ML_MISSING_DEPS:
        ML_MISSING_DEPS.append("ML dependencies (scikit-learn, joblib)")

# Export all symbols for backward compatibility
__all__ = [
    # Feature flags
    'ML_AVAILABLE',
    'ML_MISSING_DEPS',
    'HAS_MAPIE',
    # Distance prediction
    'train_distance_model',
    'load_model',
    'save_model',
    'DistancePredictor',
    # Tuning
    'get_small_dataset_params',
    # Shot shape classification
    'ShotShapeClassifier',
    'ShotShape',
    'classify_shot_shape',
    # Anomaly detection
    'SwingFlawDetector',
    'SwingFlaw',
    'detect_swing_flaws',
]
