"""
Swing Flaw Detection via Anomaly Detection for GolfDataApp.

Uses Isolation Forest to detect unusual patterns in swing data that may
indicate swing flaws:
- Over-the-top swing (steep club path)
- Casting / early release (low smash factor)
- Inconsistent contact (high impact variance)
- Clubface control issues (high face angle variance)

Usage:
    detector = SwingFlawDetector()
    detector.fit(shots_df)
    flaws = detector.detect(new_shot)
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd

# ML imports - optional
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    import joblib
    HAS_ML_DEPS = True
except ImportError:
    HAS_ML_DEPS = False


class SwingFlaw(Enum):
    """Common swing flaw types."""
    OVER_THE_TOP = 'over_the_top'
    EARLY_RELEASE = 'early_release'
    INCONSISTENT_CONTACT = 'inconsistent_contact'
    CLUBFACE_CONTROL = 'clubface_control'
    STEEP_ATTACK = 'steep_attack'
    SHALLOW_ATTACK = 'shallow_attack'
    LOW_COMPRESSION = 'low_compression'
    NONE = 'none'


@dataclass
class FlawDetectionResult:
    """Result from flaw detection."""
    flaws: List[SwingFlaw]
    anomaly_score: float
    is_outlier: bool
    details: Dict[str, Any]


@dataclass
class SwingMetrics:
    """Computed swing metrics for analysis."""
    smash_factor: float
    attack_angle: float
    club_path: float
    face_angle: float
    face_to_path: float
    impact_consistency: float
    spin_efficiency: float


def compute_swing_metrics(
    ball_speed: float,
    club_speed: float,
    attack_angle: float = 0.0,
    club_path: float = 0.0,
    face_angle: float = 0.0,
    impact_x: float = 0.0,
    impact_y: float = 0.0,
    launch_angle: float = 0.0,
    back_spin: float = 0.0,
    dynamic_loft: Optional[float] = None,
) -> SwingMetrics:
    """
    Compute derived swing metrics for analysis.

    Args:
        ball_speed: Ball speed in mph
        club_speed: Club speed in mph
        attack_angle: Attack angle in degrees
        club_path: Club path in degrees
        face_angle: Face angle at impact in degrees
        impact_x: Impact location X (mm from center)
        impact_y: Impact location Y (mm from center)
        launch_angle: Launch angle in degrees
        back_spin: Back spin in rpm
        dynamic_loft: Dynamic loft at impact in degrees

    Returns:
        SwingMetrics object
    """
    # Smash factor
    smash = ball_speed / club_speed if club_speed > 0 else 0.0

    # Face to path (determines curve)
    face_to_path = face_angle - club_path

    # Impact consistency (distance from center)
    impact_consistency = np.sqrt(impact_x**2 + impact_y**2)

    # Spin efficiency (ratio of useful spin to total spin)
    # Higher launch + lower spin = more efficient for distance
    if dynamic_loft and launch_angle > 0:
        spin_efficiency = (launch_angle / dynamic_loft) if dynamic_loft > 0 else 0.0
    else:
        # Estimate from spin rate
        expected_spin = 2500  # Baseline for driver
        spin_efficiency = min(1.0, expected_spin / max(1, back_spin))

    return SwingMetrics(
        smash_factor=smash,
        attack_angle=attack_angle,
        club_path=club_path,
        face_angle=face_angle,
        face_to_path=face_to_path,
        impact_consistency=impact_consistency,
        spin_efficiency=spin_efficiency,
    )


def detect_swing_flaws(
    ball_speed: Optional[float] = None,
    club_speed: Optional[float] = None,
    attack_angle: Optional[float] = None,
    club_path: Optional[float] = None,
    face_angle: Optional[float] = None,
    impact_x: Optional[float] = None,
    impact_y: Optional[float] = None,
    back_spin: Optional[float] = None,
    smash: Optional[float] = None,
) -> FlawDetectionResult:
    """
    Detect potential swing flaws using rule-based analysis.

    This is a heuristic approach that doesn't require training data.

    Args:
        ball_speed: Ball speed in mph
        club_speed: Club speed in mph
        attack_angle: Attack angle in degrees
        club_path: Club path in degrees
        face_angle: Face angle at impact in degrees
        impact_x: Impact location X (mm from center)
        impact_y: Impact location Y (mm from center)
        back_spin: Back spin in rpm
        smash: Pre-computed smash factor

    Returns:
        FlawDetectionResult
    """
    flaws = []
    details = {}
    anomaly_score = 0.0

    # Calculate smash factor if not provided
    if smash is None and ball_speed and club_speed and club_speed > 0:
        smash = ball_speed / club_speed

    # Check for over-the-top (club path too far left/outside)
    if club_path is not None:
        if club_path < -6.0:  # More than 6 degrees out-to-in
            flaws.append(SwingFlaw.OVER_THE_TOP)
            anomaly_score += abs(club_path) / 10
            details['club_path'] = f"{club_path:.1f}° (out-to-in)"

    # Check for early release / casting (low smash factor)
    if smash is not None:
        if smash < 1.35:  # Low compression
            flaws.append(SwingFlaw.EARLY_RELEASE)
            anomaly_score += (1.45 - smash) * 2
            details['smash_factor'] = f"{smash:.2f} (low)"
        elif smash > 1.52:  # Unusually high - possible data issue
            details['smash_factor'] = f"{smash:.2f} (check data)"
            anomaly_score += 0.5

    # Check for inconsistent contact (impact away from center)
    if impact_x is not None and impact_y is not None:
        impact_distance = np.sqrt(impact_x**2 + impact_y**2)
        if impact_distance > 15:  # More than 15mm from center
            flaws.append(SwingFlaw.INCONSISTENT_CONTACT)
            anomaly_score += impact_distance / 20
            details['impact_location'] = f"{impact_distance:.1f}mm from center"

    # Check for steep attack angle
    if attack_angle is not None:
        if attack_angle < -5.0:  # Too steep (hitting down too much)
            flaws.append(SwingFlaw.STEEP_ATTACK)
            anomaly_score += abs(attack_angle) / 8
            details['attack_angle'] = f"{attack_angle:.1f}° (steep)"
        elif attack_angle > 8.0:  # Too shallow (uppercutting)
            flaws.append(SwingFlaw.SHALLOW_ATTACK)
            anomaly_score += attack_angle / 10
            details['attack_angle'] = f"{attack_angle:.1f}° (shallow)"

    # Check for clubface control issues
    if face_angle is not None:
        if abs(face_angle) > 6.0:  # Face significantly open or closed
            flaws.append(SwingFlaw.CLUBFACE_CONTROL)
            anomaly_score += abs(face_angle) / 8
            direction = "open" if face_angle > 0 else "closed"
            details['face_angle'] = f"{face_angle:.1f}° ({direction})"

    # Check for low compression (high spin + low ball speed for given club speed)
    if back_spin is not None and ball_speed is not None:
        # High spin with low ball speed often indicates poor compression
        spin_ratio = back_spin / max(1, ball_speed)
        if spin_ratio > 25:  # Very high spin relative to speed
            if SwingFlaw.EARLY_RELEASE not in flaws:
                flaws.append(SwingFlaw.LOW_COMPRESSION)
            anomaly_score += (spin_ratio - 20) / 10
            details['spin_ratio'] = f"{spin_ratio:.1f} (high)"

    # Normalize anomaly score
    anomaly_score = min(1.0, anomaly_score / 3)

    # Determine if this is an outlier
    is_outlier = anomaly_score > 0.5 or len(flaws) >= 2

    if not flaws:
        flaws.append(SwingFlaw.NONE)

    return FlawDetectionResult(
        flaws=flaws,
        anomaly_score=anomaly_score,
        is_outlier=is_outlier,
        details=details,
    )


class SwingFlawDetector:
    """
    ML-based swing flaw detector using Isolation Forest.

    Trains on normal swings to detect anomalous patterns.

    Usage:
        detector = SwingFlawDetector()
        detector.fit(shots_df)

        # Detect flaws in new shot
        result = detector.detect(shot_data)

        # Analyze session for patterns
        analysis = detector.analyze_session(session_df)
    """

    def __init__(self, contamination: float = 0.1):
        """
        Initialize detector.

        Args:
            contamination: Expected proportion of outliers in training data
        """
        self.contamination = contamination
        self.model = None
        self.scaler = None
        self._feature_names = [
            'smash',
            'attack_angle',
            'club_path',
            'face_angle',
            'impact_x',
            'impact_y',
        ]
        self._is_fitted = False

    def is_fitted(self) -> bool:
        """Check if model is fitted."""
        return self._is_fitted

    def fit(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Fit the anomaly detector on shot data.

        Args:
            df: DataFrame with shot data

        Returns:
            Dict with fitting metrics
        """
        if not HAS_ML_DEPS:
            raise ImportError("ML dependencies not installed")

        # Get available features
        available = [f for f in self._feature_names if f in df.columns]
        if len(available) < 3:
            raise ValueError("Insufficient features for training")

        # Filter valid rows
        valid_mask = pd.Series(True, index=df.index)
        for col in available:
            valid_mask &= df[col].notna()

        df_train = df[valid_mask].copy()

        if len(df_train) < 20:
            raise ValueError(f"Insufficient training data: {len(df_train)} samples")

        X = df_train[available]

        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Train Isolation Forest
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100,
        )
        self.model.fit(X_scaled)

        self._feature_names = available
        self._is_fitted = True

        # Get outlier predictions for training data
        predictions = self.model.predict(X_scaled)
        n_outliers = (predictions == -1).sum()

        return {
            'samples': len(df_train),
            'features': available,
            'outliers_detected': n_outliers,
            'outlier_rate': n_outliers / len(df_train),
        }

    def detect(
        self,
        ball_speed: Optional[float] = None,
        club_speed: Optional[float] = None,
        attack_angle: Optional[float] = None,
        club_path: Optional[float] = None,
        face_angle: Optional[float] = None,
        impact_x: Optional[float] = None,
        impact_y: Optional[float] = None,
        back_spin: Optional[float] = None,
        smash: Optional[float] = None,
    ) -> FlawDetectionResult:
        """
        Detect potential swing flaws in a single shot.

        Uses ML model if fitted, otherwise falls back to rules.

        Args:
            Various swing parameters

        Returns:
            FlawDetectionResult
        """
        # Always run rule-based detection first
        rule_result = detect_swing_flaws(
            ball_speed=ball_speed,
            club_speed=club_speed,
            attack_angle=attack_angle,
            club_path=club_path,
            face_angle=face_angle,
            impact_x=impact_x,
            impact_y=impact_y,
            back_spin=back_spin,
            smash=smash,
        )

        # If ML model not fitted, return rule-based result
        if not self._is_fitted:
            return rule_result

        # Compute smash factor if needed
        if smash is None and ball_speed and club_speed and club_speed > 0:
            smash = ball_speed / club_speed

        # Prepare features for ML
        feature_values = {
            'smash': smash or 0.0,
            'attack_angle': attack_angle or 0.0,
            'club_path': club_path or 0.0,
            'face_angle': face_angle or 0.0,
            'impact_x': impact_x or 0.0,
            'impact_y': impact_y or 0.0,
        }

        features = [feature_values.get(f, 0.0) for f in self._feature_names]
        X = np.array([features])
        X_scaled = self.scaler.transform(X)

        # Get anomaly score from Isolation Forest
        # score_samples returns negative values where more negative = more anomalous
        # Typical range is roughly -0.5 (normal) to -1.0 (anomaly)
        raw_ml_score = self.model.score_samples(X_scaled)[0]

        # Normalize to 0-1 range: -0.5 -> 0, -1.0 -> 1.0
        # Formula: 1 - (raw_score - (-1)) / ((-0.5) - (-1)) = 1 - (raw_score + 1) / 0.5
        ml_score = max(0.0, min(1.0, 1 - (raw_ml_score + 1) / 0.5))

        ml_prediction = self.model.predict(X_scaled)[0]
        is_ml_outlier = ml_prediction == -1

        # Combine rule-based and ML results (both now 0-1 normalized)
        combined_score = (rule_result.anomaly_score + ml_score) / 2
        is_outlier = rule_result.is_outlier or is_ml_outlier

        # Add ML info to details
        details = rule_result.details.copy()
        details['ml_score'] = ml_score
        details['ml_outlier'] = is_ml_outlier

        return FlawDetectionResult(
            flaws=rule_result.flaws,
            anomaly_score=combined_score,
            is_outlier=is_outlier,
            details=details,
        )

    def analyze_session(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a full session for swing patterns and issues.

        Args:
            df: DataFrame with session shot data

        Returns:
            Dict with session analysis
        """
        if df.empty:
            return {'error': 'No data provided'}

        results = []
        for _, row in df.iterrows():
            result = self.detect(
                ball_speed=row.get('ball_speed'),
                club_speed=row.get('club_speed'),
                attack_angle=row.get('attack_angle'),
                club_path=row.get('club_path'),
                face_angle=row.get('face_angle'),
                impact_x=row.get('impact_x'),
                impact_y=row.get('impact_y'),
                back_spin=row.get('back_spin'),
                smash=row.get('smash'),
            )
            results.append(result)

        # Aggregate flaw counts
        flaw_counts = {}
        for result in results:
            for flaw in result.flaws:
                if flaw != SwingFlaw.NONE:
                    flaw_counts[flaw.value] = flaw_counts.get(flaw.value, 0) + 1

        # Sort by frequency
        sorted_flaws = sorted(flaw_counts.items(), key=lambda x: x[1], reverse=True)

        # Calculate outlier rate
        outlier_count = sum(1 for r in results if r.is_outlier)
        outlier_rate = outlier_count / len(results)

        # Average anomaly score
        avg_score = sum(r.anomaly_score for r in results) / len(results)

        return {
            'total_shots': len(df),
            'outlier_count': outlier_count,
            'outlier_rate': outlier_rate,
            'average_anomaly_score': avg_score,
            'flaw_counts': dict(sorted_flaws),
            'most_common_flaw': sorted_flaws[0][0] if sorted_flaws else None,
            'recommendations': _generate_recommendations(sorted_flaws),
        }


def _generate_recommendations(flaw_counts: List[Tuple[str, int]]) -> List[str]:
    """Generate practice recommendations based on detected flaws."""
    recommendations = []

    flaw_map = {
        'over_the_top': "Work on shallowing the downswing. Try the 'headcover under arm' drill.",
        'early_release': "Focus on lag retention. Practice the 'pump drill' for better compression.",
        'inconsistent_contact': "Work on center-face contact. Use impact tape to track strike location.",
        'clubface_control': "Practice face awareness drills. Check grip pressure and alignment.",
        'steep_attack': "Shallow your attack angle. Focus on sweeping the ball for more distance.",
        'shallow_attack': "Steepen your downswing slightly. Check ball position isn't too far forward.",
        'low_compression': "Focus on striking down on the ball with forward shaft lean.",
    }

    for flaw, count in flaw_counts[:3]:  # Top 3 flaws
        if flaw in flaw_map:
            recommendations.append(flaw_map[flaw])

    if not recommendations:
        recommendations.append("Great swing patterns! Focus on consistency.")

    return recommendations
