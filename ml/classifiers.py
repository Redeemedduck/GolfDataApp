"""
Shot Shape Classification for GolfDataApp.

Classifies shots based on ball flight characteristics:
- Straight: Minimal curve
- Draw: Right-to-left curve (for right-handed golfer)
- Fade: Left-to-right curve (for right-handed golfer)
- Hook: Severe draw
- Slice: Severe fade
- Push: Straight but right of target
- Pull: Straight but left of target

Classification is based on:
- Face angle at impact
- Club path
- Side spin
- Side distance

Usage:
    classifier = ShotShapeClassifier()
    shape = classifier.classify(face_angle=-2.0, club_path=-4.0, side_spin=-500)
    # Returns: 'draw'
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd

# ML imports - optional
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    import joblib
    HAS_ML_DEPS = True
except ImportError:
    HAS_ML_DEPS = False


class ShotShape(Enum):
    """Shot shape classifications."""
    STRAIGHT = 'straight'
    DRAW = 'draw'
    FADE = 'fade'
    HOOK = 'hook'
    SLICE = 'slice'
    PUSH = 'push'
    PULL = 'pull'
    UNKNOWN = 'unknown'


@dataclass
class ClassificationResult:
    """Result from shot shape classification."""
    shape: ShotShape
    confidence: float
    details: Dict[str, Any]


def classify_shot_shape(
    face_angle: Optional[float] = None,
    club_path: Optional[float] = None,
    side_spin: Optional[float] = None,
    side_distance: Optional[float] = None,
) -> ClassificationResult:
    """
    Classify a shot's shape based on impact conditions.

    Uses a rule-based approach that doesn't require training data.
    This is based on the D-plane theory of ball flight.

    Args:
        face_angle: Face angle at impact (degrees, negative = closed)
        club_path: Club path (degrees, negative = left of target)
        side_spin: Side spin in rpm (negative = left, positive = right)
        side_distance: Landing distance from target line (negative = left)

    Returns:
        ClassificationResult with shape, confidence, and details
    """
    # Track what data we have
    has_face = face_angle is not None
    has_path = club_path is not None
    has_spin = side_spin is not None
    has_distance = side_distance is not None

    if not any([has_face, has_path, has_spin, has_distance]):
        return ClassificationResult(
            shape=ShotShape.UNKNOWN,
            confidence=0.0,
            details={'reason': 'No data provided'},
        )

    # Thresholds (degrees)
    STRAIGHT_THRESHOLD = 2.0  # Within 2 degrees is "straight"
    SEVERE_THRESHOLD = 6.0    # More than 6 degrees is hook/slice

    # Calculate face-to-path (determines initial direction)
    face_to_path = None
    if has_face and has_path:
        face_to_path = face_angle - club_path

    # Determine curve direction from face-to-path or side spin
    curve_direction = 0  # -1 = left (draw), 0 = straight, 1 = right (fade)
    curve_magnitude = 0.0

    if face_to_path is not None:
        if face_to_path < -STRAIGHT_THRESHOLD:
            curve_direction = -1  # Draw
            curve_magnitude = abs(face_to_path)
        elif face_to_path > STRAIGHT_THRESHOLD:
            curve_direction = 1  # Fade
            curve_magnitude = abs(face_to_path)
    elif has_spin:
        # Estimate from side spin (rough approximation)
        if side_spin < -200:
            curve_direction = -1  # Draw (left spin)
            curve_magnitude = abs(side_spin) / 500  # Normalize
        elif side_spin > 200:
            curve_direction = 1  # Fade (right spin)
            curve_magnitude = abs(side_spin) / 500

    # Determine start direction from club path
    start_direction = 0  # -1 = left, 0 = center, 1 = right
    if has_path:
        if club_path < -STRAIGHT_THRESHOLD:
            start_direction = -1  # Pull
        elif club_path > STRAIGHT_THRESHOLD:
            start_direction = 1  # Push

    # Classify based on curve and start direction
    shape = ShotShape.STRAIGHT
    confidence = 0.5

    if curve_direction == 0:
        # No significant curve
        if start_direction == -1:
            shape = ShotShape.PULL
            confidence = 0.7
        elif start_direction == 1:
            shape = ShotShape.PUSH
            confidence = 0.7
        else:
            shape = ShotShape.STRAIGHT
            confidence = 0.8
    elif curve_direction == -1:
        # Drawing left
        if curve_magnitude > SEVERE_THRESHOLD:
            shape = ShotShape.HOOK
            confidence = 0.8
        else:
            shape = ShotShape.DRAW
            confidence = 0.75
    else:
        # Fading right
        if curve_magnitude > SEVERE_THRESHOLD:
            shape = ShotShape.SLICE
            confidence = 0.8
        else:
            shape = ShotShape.FADE
            confidence = 0.75

    # Adjust confidence based on data completeness
    data_completeness = sum([has_face, has_path, has_spin, has_distance]) / 4
    confidence *= (0.5 + 0.5 * data_completeness)

    details = {
        'face_angle': face_angle,
        'club_path': club_path,
        'face_to_path': face_to_path,
        'side_spin': side_spin,
        'side_distance': side_distance,
        'curve_direction': 'left' if curve_direction == -1 else 'right' if curve_direction == 1 else 'none',
        'curve_magnitude': curve_magnitude,
        'start_direction': 'left' if start_direction == -1 else 'right' if start_direction == 1 else 'center',
    }

    return ClassificationResult(
        shape=shape,
        confidence=confidence,
        details=details,
    )


class ShotShapeClassifier:
    """
    ML-based shot shape classifier with rule-based fallback.

    Can be trained on labeled data or uses rule-based classification.

    Usage:
        classifier = ShotShapeClassifier()

        # Rule-based (no training needed)
        result = classifier.classify(face_angle=-2.0, club_path=-4.0)

        # ML-based (requires training)
        classifier.train(shots_df)
        result = classifier.classify(face_angle=-2.0, club_path=-4.0)
    """

    def __init__(self):
        """Initialize classifier."""
        self.model = None
        self.scaler = None
        self._feature_names = ['face_angle', 'club_path', 'side_spin', 'side_distance']
        self._use_ml = False

    def is_trained(self) -> bool:
        """Check if ML model is trained."""
        return self.model is not None

    def train(self, df: pd.DataFrame, label_col: str = 'shot_shape') -> Dict[str, float]:
        """
        Train the classifier on labeled data.

        Args:
            df: DataFrame with shot data and labels
            label_col: Column name for shot shape labels

        Returns:
            Dict with training metrics
        """
        if not HAS_ML_DEPS:
            raise ImportError("ML dependencies not installed")

        if label_col not in df.columns:
            raise ValueError(f"Label column '{label_col}' not found")

        # Get features
        available_features = [f for f in self._feature_names if f in df.columns]
        if len(available_features) < 2:
            raise ValueError("Insufficient features for training")

        # Filter valid rows
        valid_mask = df[label_col].notna()
        for col in available_features:
            valid_mask &= df[col].notna()

        df_train = df[valid_mask].copy()

        if len(df_train) < 20:
            raise ValueError(f"Insufficient training data: {len(df_train)} samples")

        X = df_train[available_features]
        y = df_train[label_col]

        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Train classifier
        self.model = RandomForestClassifier(
            n_estimators=50,
            max_depth=10,
            random_state=42,
        )
        self.model.fit(X_scaled, y)

        self._use_ml = True
        self._feature_names = available_features

        # Calculate accuracy
        accuracy = self.model.score(X_scaled, y)

        return {
            'accuracy': accuracy,
            'samples': len(df_train),
            'features': available_features,
        }

    def classify(
        self,
        face_angle: Optional[float] = None,
        club_path: Optional[float] = None,
        side_spin: Optional[float] = None,
        side_distance: Optional[float] = None,
    ) -> ClassificationResult:
        """
        Classify a shot's shape.

        Uses ML model if trained, otherwise falls back to rule-based.

        Args:
            face_angle: Face angle at impact (degrees)
            club_path: Club path (degrees)
            side_spin: Side spin in rpm
            side_distance: Landing distance from target line

        Returns:
            ClassificationResult
        """
        # Use rule-based classification if ML not available/trained
        if not self._use_ml or not self.is_trained():
            return classify_shot_shape(
                face_angle=face_angle,
                club_path=club_path,
                side_spin=side_spin,
                side_distance=side_distance,
            )

        # Prepare features for ML model
        feature_values = {
            'face_angle': face_angle or 0.0,
            'club_path': club_path or 0.0,
            'side_spin': side_spin or 0.0,
            'side_distance': side_distance or 0.0,
        }

        features = [feature_values.get(f, 0.0) for f in self._feature_names]
        X = np.array([features])
        X_scaled = self.scaler.transform(X)

        # Predict
        prediction = self.model.predict(X_scaled)[0]
        probabilities = self.model.predict_proba(X_scaled)[0]
        confidence = float(max(probabilities))

        # Map to ShotShape enum
        try:
            shape = ShotShape(prediction.lower())
        except ValueError:
            shape = ShotShape.UNKNOWN

        return ClassificationResult(
            shape=shape,
            confidence=confidence,
            details={
                'face_angle': face_angle,
                'club_path': club_path,
                'side_spin': side_spin,
                'side_distance': side_distance,
                'method': 'ml',
                'class_probabilities': dict(zip(self.model.classes_, probabilities.tolist())),
            },
        )

    def classify_batch(self, df: pd.DataFrame) -> pd.Series:
        """
        Classify shot shapes for a batch of shots.

        Args:
            df: DataFrame with shot data

        Returns:
            Series of ShotShape values
        """
        results = []

        for _, row in df.iterrows():
            result = self.classify(
                face_angle=row.get('face_angle'),
                club_path=row.get('club_path'),
                side_spin=row.get('side_spin'),
                side_distance=row.get('side_distance'),
            )
            results.append(result.shape.value)

        return pd.Series(results, index=df.index)


def get_shot_shape_summary(shape_series: pd.Series) -> Dict[str, Any]:
    """
    Get summary statistics for shot shapes.

    Args:
        shape_series: Series of shot shape values

    Returns:
        Dict with shape distribution and dominant shape
    """
    counts = shape_series.value_counts()
    total = len(shape_series)

    distribution = {
        shape: count / total
        for shape, count in counts.items()
    }

    dominant = counts.idxmax() if len(counts) > 0 else 'unknown'

    return {
        'distribution': distribution,
        'dominant_shape': dominant,
        'total_shots': total,
        'consistency': max(distribution.values()) if distribution else 0.0,
    }
