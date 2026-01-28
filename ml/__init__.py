"""
ML Module for GolfDataApp.

Provides local machine learning models for:
- Distance prediction (carry/total based on launch conditions)
- Shot shape classification (draw, fade, straight, etc.)
- Swing flaw detection via anomaly detection

Note: Some features require ML dependencies (scikit-learn, xgboost, joblib).
Rule-based classification and detection work without these dependencies.
"""

# Lazy imports to avoid requiring ML deps for all uses
__all__ = [
    'train_distance_model',
    'load_model',
    'save_model',
    'DistancePredictor',
    'ShotShapeClassifier',
    'ShotShape',
    'classify_shot_shape',
    'SwingFlawDetector',
    'SwingFlaw',
    'detect_swing_flaws',
]


def __getattr__(name):
    """Lazy import attributes to avoid requiring all dependencies."""
    if name in ('train_distance_model', 'load_model', 'save_model', 'DistancePredictor'):
        from .train_models import train_distance_model, load_model, save_model, DistancePredictor
        return {
            'train_distance_model': train_distance_model,
            'load_model': load_model,
            'save_model': save_model,
            'DistancePredictor': DistancePredictor,
        }[name]
    elif name in ('ShotShapeClassifier', 'ShotShape', 'classify_shot_shape'):
        from .classifiers import ShotShapeClassifier, ShotShape, classify_shot_shape
        return {
            'ShotShapeClassifier': ShotShapeClassifier,
            'ShotShape': ShotShape,
            'classify_shot_shape': classify_shot_shape,
        }[name]
    elif name in ('SwingFlawDetector', 'SwingFlaw', 'detect_swing_flaws'):
        from .anomaly_detection import SwingFlawDetector, SwingFlaw, detect_swing_flaws
        return {
            'SwingFlawDetector': SwingFlawDetector,
            'SwingFlaw': SwingFlaw,
            'detect_swing_flaws': detect_swing_flaws,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
