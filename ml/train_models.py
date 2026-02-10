"""
Model Training Pipeline for GolfDataApp.

Trains XGBoost models for distance prediction based on launch conditions.
Models are saved as joblib files for fast loading.

Usage:
    # Train a new model
    python -m ml.train_models

    # Or use programmatically
    from ml.train_models import train_distance_model, DistancePredictor
    predictor = DistancePredictor()
    predictor.train()
    predicted_carry = predictor.predict(club='Driver', ball_speed=165, launch_angle=12)
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

# ML imports - these are optional and may not be installed
# Note: XGBoost may raise XGBoostError (not ImportError) if libomp is missing
try:
    import joblib
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.preprocessing import LabelEncoder
    import xgboost as xgb
    HAS_ML_DEPS = True
except (ImportError, Exception) as e:
    # Catch both ImportError and XGBoostError (missing libomp.dylib)
    HAS_ML_DEPS = False
    joblib = None  # Will error if used without deps
    xgb = None

# MAPIE import for prediction intervals (graceful degradation)
try:
    from mapie.regression import CrossConformalRegressor
    HAS_MAPIE = True
except ImportError:
    HAS_MAPIE = False
    CrossConformalRegressor = None

# Import golf_db for data access
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    import golf_db
    HAS_GOLF_DB = True
except ImportError:
    HAS_GOLF_DB = False

# Import tuning utilities
try:
    from .tuning import get_small_dataset_params
except ImportError:
    # Fallback if tuning module not available
    def get_small_dataset_params(n_samples: int) -> dict:
        return {
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.1,
            'objective': 'reg:squarederror',
            'random_state': 42,
        }


# Model storage paths
MODELS_DIR = Path(__file__).parent.parent / 'models'
DISTANCE_MODEL_PATH = MODELS_DIR / 'distance_model.joblib'
MODEL_METADATA_PATH = MODELS_DIR / 'model_metadata.json'

# Trusted directory for model loading (security: prevent path traversal)
TRUSTED_MODEL_DIR = MODELS_DIR


@dataclass
class ModelMetadata:
    """Metadata for a trained model."""
    model_type: str
    version: str
    trained_at: str
    training_samples: int
    features: List[str]
    target: str
    metrics: Dict[str, float]
    hyperparameters: Dict[str, Any]


@dataclass
class PredictionResult:
    """Result from a prediction."""
    predicted_value: float
    confidence: float
    feature_importance: Dict[str, float]


def check_ml_deps():
    """Check if ML dependencies are installed."""
    if not HAS_ML_DEPS:
        raise ImportError(
            "ML dependencies not installed. Run: pip install scikit-learn xgboost joblib"
        )


def save_model(model, path: Path, metadata: ModelMetadata) -> None:
    """
    Save a model with metadata.

    Args:
        model: Trained model to save
        path: Path to save the model
        metadata: Model metadata
    """
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Save the model
    joblib.dump(model, path)

    # Save metadata
    metadata_path = path.with_suffix('.metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(asdict(metadata), f, indent=2)

    print(f"Model saved to {path}")


def load_model(path: Path) -> Tuple[Any, Optional[ModelMetadata]]:
    """
    Load a model with its metadata.

    Args:
        path: Path to the model file

    Returns:
        Tuple of (model, metadata)

    Raises:
        ValueError: If path is outside trusted model directory (security)
        FileNotFoundError: If model file doesn't exist
    """
    # Security: Validate path is within trusted directory to prevent RCE via path traversal
    resolved_path = Path(path).resolve()
    trusted_resolved = TRUSTED_MODEL_DIR.resolve()
    if not str(resolved_path).startswith(str(trusted_resolved)):
        raise ValueError(
            f"Security: Model path must be within {TRUSTED_MODEL_DIR}. "
            f"Got: {path}"
        )

    if not resolved_path.exists():
        raise FileNotFoundError(f"Model not found: {path}")

    model = joblib.load(resolved_path)

    # Try to load metadata
    metadata = None
    metadata_path = path.with_suffix('.metadata.json')
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            data = json.load(f)
            metadata = ModelMetadata(**data)

            # Validate feature compatibility
            if metadata.features:
                # Get expected features from model
                if hasattr(model, 'n_features_in_'):
                    expected_count = model.n_features_in_
                    actual_count = len(metadata.features)
                    if expected_count != actual_count:
                        print(f"Warning: Feature count mismatch - model expects {expected_count}, metadata has {actual_count}")

    return model, metadata


def get_model_info(model_path: Path) -> Optional[ModelMetadata]:
    """
    Get model metadata without loading the full model (fast check).

    Args:
        model_path: Path to the model file

    Returns:
        ModelMetadata if metadata exists, None otherwise (backward compatibility)

    Note:
        This is useful for UI showing model details before prediction.
        Does not validate the model file itself.
    """
    metadata_path = model_path.with_suffix('.metadata.json')
    if not metadata_path.exists():
        return None

    try:
        with open(metadata_path, 'r') as f:
            data = json.load(f)
            return ModelMetadata(**data)
    except Exception as e:
        print(f"Warning: Could not load metadata from {metadata_path}: {e}")
        return None


def get_training_data() -> pd.DataFrame:
    """
    Get training data from the database.

    Returns:
        DataFrame with shot data
    """
    if not HAS_GOLF_DB:
        raise RuntimeError("golf_db not available")

    # Get all shots
    df = golf_db.get_session_data()

    if df is None or df.empty:
        raise ValueError("No training data available")

    return df


def prepare_features(df: pd.DataFrame, target: str = 'carry') -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepare features for training.

    Args:
        df: Raw shot data
        target: Target column to predict

    Returns:
        Tuple of (features DataFrame, target Series)
    """
    # Required features for distance prediction
    feature_cols = [
        'ball_speed',
        'launch_angle',
        'back_spin',
        'club_speed',
        'attack_angle',
        'dynamic_loft',
    ]

    # Filter to rows with valid data
    valid_mask = df[target].notna() & (df[target] > 0) & (df[target] < 400)
    for col in feature_cols:
        if col in df.columns:
            valid_mask &= df[col].notna()

    df_clean = df[valid_mask].copy()

    if len(df_clean) < 50:
        raise ValueError(f"Insufficient training data: {len(df_clean)} samples")

    # Extract features that exist
    available_features = [c for c in feature_cols if c in df_clean.columns]
    X = df_clean[available_features].copy()
    y = df_clean[target].copy()

    # Handle missing values with median imputation
    for col in X.columns:
        if X[col].isna().any():
            X[col] = X[col].fillna(X[col].median())

    return X, y


def train_distance_model(
    df: Optional[pd.DataFrame] = None,
    target: str = 'carry',
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[Any, ModelMetadata]:
    """
    Train an XGBoost model for distance prediction.

    Args:
        df: Training data (loads from database if not provided)
        target: Target column ('carry' or 'total')
        test_size: Fraction for test set
        random_state: Random seed

    Returns:
        Tuple of (trained model, metadata)
    """
    check_ml_deps()

    # Get data
    if df is None:
        df = get_training_data()

    # Prepare features
    X, y = prepare_features(df, target)
    features = list(X.columns)

    print(f"Training with {len(X)} samples, {len(features)} features")
    print(f"Features: {features}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # Get dataset-size-aware hyperparameters
    tuned_params = get_small_dataset_params(len(X))

    # Train XGBoost model with tuned parameters
    model = xgb.XGBRegressor(**tuned_params)

    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"Test MAE: {mae:.2f} yards")
    print(f"Test RMSE: {rmse:.2f} yards")
    print(f"Test R2: {r2:.3f}")

    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='neg_mean_absolute_error')
    cv_mae = -cv_scores.mean()
    print(f"Cross-validation MAE: {cv_mae:.2f} yards (+/- {cv_scores.std():.2f})")

    # Create metadata with tuned hyperparameters
    metadata = ModelMetadata(
        model_type='xgboost_regressor',
        version='1.0.0',
        trained_at=datetime.utcnow().isoformat(),
        training_samples=len(X),
        features=features,
        target=target,
        metrics={
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'cv_mae': cv_mae,
        },
        hyperparameters=tuned_params,
    )

    return model, metadata


class DistancePredictor:
    """
    High-level interface for distance prediction.

    Usage:
        predictor = DistancePredictor()
        predictor.load()  # Load existing model
        carry = predictor.predict(
            ball_speed=165,
            launch_angle=12.5,
            back_spin=2500,
        )
    """

    def __init__(self, model_path: Optional[Path] = None):
        """
        Initialize predictor.

        Args:
            model_path: Path to model file (uses default if not specified)
        """
        self.model_path = model_path or DISTANCE_MODEL_PATH
        self.model = None
        self.metadata = None
        self._feature_names = None
        self.mapie_model = None

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None

    # Default feature names in case model was saved without metadata
    DEFAULT_FEATURE_NAMES = [
        'ball_speed',
        'launch_angle',
        'back_spin',
        'club_speed',
        'attack_angle',
        'dynamic_loft',
    ]

    def load(self) -> None:
        """Load the model from disk."""
        loaded_model, self.metadata = load_model(self.model_path)

        # Handle backward compatibility: old models are XGBRegressor, new models are dicts
        if isinstance(loaded_model, dict):
            # New format: dict with 'base_model' and optionally 'mapie_model'
            self.model = loaded_model.get('base_model')
            self.mapie_model = loaded_model.get('mapie_model')
        else:
            # Old format: just the XGBRegressor model
            self.model = loaded_model
            self.mapie_model = None

        # Validate metadata and set feature names
        if self.metadata and self.metadata.features:
            self._feature_names = self.metadata.features

            # Validate features match model expectations
            if hasattr(self.model, 'n_features_in_'):
                expected_count = self.model.n_features_in_
                actual_count = len(self.metadata.features)
                if expected_count != actual_count:
                    print(f"Warning: Feature count mismatch - model expects {expected_count}, metadata has {actual_count}")
                    print(f"Warning: Falling back to default feature names")
                    self._feature_names = self.DEFAULT_FEATURE_NAMES
        else:
            # Fallback to defaults if metadata is missing (backward compatibility)
            self._feature_names = self.DEFAULT_FEATURE_NAMES
            print("Warning: Model loaded without metadata, using default feature names")

        print(f"Loaded distance model: {self.model_path}")

    def train(self, df: Optional[pd.DataFrame] = None, save: bool = True) -> ModelMetadata:
        """
        Train a new model.

        Args:
            df: Training data (loads from database if not provided)
            save: Whether to save the model

        Returns:
            Model metadata
        """
        self.model, self.metadata = train_distance_model(df)
        self._feature_names = self.metadata.features

        if save:
            save_model(self.model, self.model_path, self.metadata)

        return self.metadata

    def train_with_intervals(
        self,
        df: Optional[pd.DataFrame] = None,
        confidence_level: float = 0.95,
        save: bool = True
    ) -> ModelMetadata:
        """
        Train XGBoost model and wrap with MAPIE for confidence intervals.

        Uses cross-conformal prediction (cv-plus method) for distribution-free
        confidence intervals. Requires MAPIE to be installed and at least 1000 shots.

        Args:
            df: Training data (loads from database if not provided)
            confidence_level: Confidence level for intervals (default 0.95)
            save: Whether to save the model

        Returns:
            Model metadata

        Raises:
            ImportError: If MAPIE not installed
            ValueError: If fewer than 1000 shots available
        """
        if not HAS_MAPIE:
            raise ImportError(
                "MAPIE not installed. Run: pip install mapie>=1.3.0\n"
                "Also requires: pip install --upgrade scikit-learn>=1.4.0"
            )

        check_ml_deps()

        # Get data
        if df is None:
            df = get_training_data()

        # Prepare features
        X, y = prepare_features(df, target='carry')
        features = list(X.columns)

        # Minimum sample check for reliable intervals
        if len(X) < 1000:
            raise ValueError(
                f"Need at least 1000 shots for confidence intervals (have {len(X)}). "
                "Use train() method for point predictions with smaller datasets."
            )

        print(f"Training with intervals: {len(X)} samples, {len(features)} features")
        print(f"Features: {features}")

        # Split: 70% train, 30% conformalization (MAPIE requires separate sets)
        X_train_full, X_conform, y_train_full, y_conform = train_test_split(
            X, y, test_size=0.3, random_state=42
        )

        # Further split train for early stopping validation
        X_train, X_val, y_train, y_val = train_test_split(
            X_train_full, y_train_full, test_size=0.2, random_state=42
        )

        # Get dataset-size-aware hyperparameters
        tuned_params = get_small_dataset_params(len(X))
        print(f"Using tuned params for {len(X)} samples: max_depth={tuned_params['max_depth']}, "
              f"reg_lambda={tuned_params['reg_lambda']}")

        # Train base XGBoost model with early stopping
        base_model = xgb.XGBRegressor(**tuned_params)
        base_model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=10,
            verbose=False
        )

        # Wrap with MAPIE using cv-plus method
        self.mapie_model = CrossConformalRegressor(
            base_model,
            method="plus",        # Jackknife+ (conservative, good for small data)
            cv=5,                 # 5-fold CV
        )

        # Conformalize using held-out data
        self.mapie_model.fit(X_conform, y_conform)

        # Store base model for feature importance and backward compat
        self.model = base_model
        self._feature_names = features

        # Evaluate on conformalization set
        y_pred = base_model.predict(X_conform)
        mae = mean_absolute_error(y_conform, y_pred)
        rmse = np.sqrt(mean_squared_error(y_conform, y_pred))
        r2 = r2_score(y_conform, y_pred)

        print(f"Conformalization set MAE: {mae:.2f} yards")
        print(f"Conformalization set RMSE: {rmse:.2f} yards")
        print(f"Conformalization set R2: {r2:.3f}")

        # Cross-validation on full dataset
        cv_scores = cross_val_score(base_model, X, y, cv=5, scoring='neg_mean_absolute_error')
        cv_mae = -cv_scores.mean()
        print(f"Cross-validation MAE: {cv_mae:.2f} yards (+/- {cv_scores.std():.2f})")

        # Create metadata
        self.metadata = ModelMetadata(
            model_type='xgboost_regressor_with_intervals',
            version='1.0.0',
            trained_at=datetime.utcnow().isoformat(),
            training_samples=len(X),
            features=features,
            target='carry',
            metrics={
                'mae': mae,
                'rmse': rmse,
                'r2': r2,
                'cv_mae': cv_mae,
                'confidence_level': confidence_level,
            },
            hyperparameters=tuned_params,
        )

        if save:
            # Save both models as a dict
            model_dict = {
                'base_model': self.model,
                'mapie_model': self.mapie_model,
            }
            save_model(model_dict, self.model_path, self.metadata)

        return self.metadata

    def _build_feature_array(
        self,
        ball_speed: float,
        launch_angle: float = 12.0,
        back_spin: float = 2500,
        club_speed: Optional[float] = None,
        attack_angle: Optional[float] = None,
        dynamic_loft: Optional[float] = None,
    ) -> np.ndarray:
        """
        Build feature array for prediction (internal helper).

        Args:
            ball_speed: Ball speed in mph
            launch_angle: Launch angle in degrees
            back_spin: Back spin in rpm
            club_speed: Club speed in mph (estimated if not provided)
            attack_angle: Attack angle in degrees
            dynamic_loft: Dynamic loft in degrees

        Returns:
            Feature array ready for model.predict()
        """
        # Estimate missing values
        if club_speed is None:
            # Rough estimate: ball_speed / 1.5 for driver
            club_speed = ball_speed / 1.5
        if attack_angle is None:
            attack_angle = 0.0  # Neutral
        if dynamic_loft is None:
            dynamic_loft = launch_angle + 1.0  # Rough estimate

        # Build feature array in the correct order
        feature_values = {
            'ball_speed': ball_speed,
            'launch_angle': launch_angle,
            'back_spin': back_spin,
            'club_speed': club_speed,
            'attack_angle': attack_angle,
            'dynamic_loft': dynamic_loft,
        }

        # Create feature array
        features = []
        for name in self._feature_names:
            features.append(feature_values.get(name, 0.0))

        return np.array([features])

    def predict(
        self,
        ball_speed: float,
        launch_angle: float = 12.0,
        back_spin: float = 2500,
        club_speed: Optional[float] = None,
        attack_angle: Optional[float] = None,
        dynamic_loft: Optional[float] = None,
    ) -> PredictionResult:
        """
        Predict carry distance.

        Args:
            ball_speed: Ball speed in mph
            launch_angle: Launch angle in degrees
            back_spin: Back spin in rpm
            club_speed: Club speed in mph (estimated if not provided)
            attack_angle: Attack angle in degrees
            dynamic_loft: Dynamic loft in degrees

        Returns:
            PredictionResult with predicted distance and confidence
        """
        if not self.is_loaded():
            self.load()

        # Build feature array
        X = self._build_feature_array(
            ball_speed=ball_speed,
            launch_angle=launch_angle,
            back_spin=back_spin,
            club_speed=club_speed,
            attack_angle=attack_angle,
            dynamic_loft=dynamic_loft,
        )

        # Predict
        predicted = float(self.model.predict(X)[0])

        # Get feature importance
        importance = dict(zip(
            self._feature_names,
            self.model.feature_importances_.tolist()
        ))

        # Estimate confidence based on feature availability
        provided_features = sum(1 for v in [ball_speed, launch_angle, back_spin, club_speed, attack_angle, dynamic_loft] if v is not None)
        confidence = min(1.0, provided_features / len(self._feature_names))

        return PredictionResult(
            predicted_value=predicted,
            confidence=confidence,
            feature_importance=importance,
        )

    def predict_with_intervals(
        self,
        ball_speed: float,
        launch_angle: float = 12.0,
        back_spin: float = 2500,
        club_speed: Optional[float] = None,
        attack_angle: Optional[float] = None,
        dynamic_loft: Optional[float] = None,
        confidence_level: float = 0.95,
    ) -> Dict[str, Any]:
        """
        Predict carry distance with confidence intervals.

        Returns prediction intervals using MAPIE conformal prediction if available.
        Falls back to point estimate only if MAPIE not available or model not
        trained with intervals.

        Args:
            ball_speed: Ball speed in mph
            launch_angle: Launch angle in degrees
            back_spin: Back spin in rpm
            club_speed: Club speed in mph (estimated if not provided)
            attack_angle: Attack angle in degrees
            dynamic_loft: Dynamic loft in degrees
            confidence_level: Confidence level for intervals (default 0.95)

        Returns:
            Dict with:
            - predicted_value: Point estimate (float)
            - lower_bound: Lower CI bound (float, if has_intervals=True)
            - upper_bound: Upper CI bound (float, if has_intervals=True)
            - confidence_level: Confidence level (float, if has_intervals=True)
            - interval_width: Width of interval (float, if has_intervals=True)
            - has_intervals: Whether intervals are available (bool)
            - message: Explanation if intervals not available (str, optional)

        Example:
            >>> predictor.predict_with_intervals(ball_speed=165, launch_angle=12)
            {
                'predicted_value': 250.5,
                'lower_bound': 245.2,
                'upper_bound': 255.8,
                'confidence_level': 0.95,
                'interval_width': 10.6,
                'has_intervals': True
            }
        """
        if not self.is_loaded():
            self.load()

        # Build feature array
        X = self._build_feature_array(
            ball_speed=ball_speed,
            launch_angle=launch_angle,
            back_spin=back_spin,
            club_speed=club_speed,
            attack_angle=attack_angle,
            dynamic_loft=dynamic_loft,
        )

        # Try to use MAPIE for intervals
        if self.mapie_model is not None and HAS_MAPIE:
            try:
                # Predict with intervals
                y_pred, y_pis = self.mapie_model.predict(X, alpha=1 - confidence_level)

                return {
                    'predicted_value': float(y_pred[0]),
                    'lower_bound': float(y_pis[0, 0, 0]),
                    'upper_bound': float(y_pis[0, 1, 0]),
                    'confidence_level': confidence_level,
                    'interval_width': float(y_pis[0, 1, 0] - y_pis[0, 0, 0]),
                    'has_intervals': True,
                }
            except Exception as e:
                print(f"Warning: MAPIE prediction failed: {e}")
                # Fall through to point estimate

        # Fallback: point estimate only
        predicted = float(self.model.predict(X)[0])

        result = {
            'predicted_value': predicted,
            'has_intervals': False,
        }

        # Add explanation
        if not HAS_MAPIE:
            result['message'] = "Install MAPIE for confidence intervals: pip install mapie>=1.3.0"
        elif self.mapie_model is None:
            result['message'] = "Model not trained with intervals. Use train_with_intervals() method."
        else:
            result['message'] = "Intervals not available for this prediction."

        return result

    def predict_batch(self, df: pd.DataFrame) -> pd.Series:
        """
        Predict carry distances for a batch of shots.

        Args:
            df: DataFrame with shot data

        Returns:
            Series of predicted distances
        """
        if not self.is_loaded():
            self.load()

        # Extract features
        available = [c for c in self._feature_names if c in df.columns]
        if len(available) < len(self._feature_names):
            missing = set(self._feature_names) - set(available)
            print(f"Warning: Missing features will use defaults: {missing}")

        X = pd.DataFrame(index=df.index)
        for name in self._feature_names:
            if name in df.columns:
                X[name] = df[name]
            else:
                X[name] = 0.0

        return pd.Series(self.model.predict(X), index=df.index)


def main():
    """Train models from command line."""
    print("=" * 60)
    print("GolfDataApp Model Training")
    print("=" * 60)
    print()

    check_ml_deps()

    # Initialize predictor
    predictor = DistancePredictor()

    # Train
    print("Training distance prediction model...")
    print()
    metadata = predictor.train()

    print()
    print("Training complete!")
    print(f"Model saved to: {predictor.model_path}")
    print(f"Samples used: {metadata.training_samples}")
    print(f"MAE: {metadata.metrics['mae']:.2f} yards")


if __name__ == '__main__':
    main()
