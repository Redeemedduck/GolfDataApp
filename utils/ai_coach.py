"""
AI Coach Module - Machine Learning Engine for Golf Performance Analysis

This module provides ML-powered insights including:
- Distance prediction (XGBoost regressor)
- Shot shape classification (Logistic Regression)
- Swing diagnostics and anomaly detection
- Personalized coaching recommendations
- User profile and baseline tracking

Phase 4: Local ML Foundation
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import joblib
from pathlib import Path

# Scikit-learn imports
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import IsolationForest
from sklearn.metrics import mean_squared_error, r2_score, classification_report, accuracy_score

# XGBoost for distance prediction
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("Warning: XGBoost not available. Install with: pip install xgboost")

# Paths
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / 'models'
MODELS_DIR.mkdir(exist_ok=True)

# Model file paths
DISTANCE_MODEL_PATH = MODELS_DIR / 'distance_predictor.pkl'
SHAPE_MODEL_PATH = MODELS_DIR / 'shot_shape_classifier.pkl'
ANOMALY_MODEL_PATH = MODELS_DIR / 'swing_anomaly_detector.pkl'
SCALER_PATH = MODELS_DIR / 'feature_scaler.pkl'
METADATA_PATH = MODELS_DIR / 'model_metadata.json'


class AICoach:
    """
    AI-powered golf coach with ML capabilities
    """

    def __init__(self):
        """Initialize AI Coach with models (load if available)"""
        self.distance_model = None
        self.shape_classifier = None
        self.anomaly_detector = None
        self.scaler = None
        self.metadata = {}

        # Load models if they exist
        self.load_models()

    def load_models(self) -> bool:
        """
        Load trained models from disk

        Returns:
            bool: True if models loaded successfully
        """
        try:
            if DISTANCE_MODEL_PATH.exists():
                self.distance_model = joblib.load(DISTANCE_MODEL_PATH)
                print(f"✅ Loaded distance predictor from {DISTANCE_MODEL_PATH}")

            if SHAPE_MODEL_PATH.exists():
                self.shape_classifier = joblib.load(SHAPE_MODEL_PATH)
                print(f"✅ Loaded shot shape classifier from {SHAPE_MODEL_PATH}")

            if ANOMALY_MODEL_PATH.exists():
                self.anomaly_detector = joblib.load(ANOMALY_MODEL_PATH)
                print(f"✅ Loaded anomaly detector from {ANOMALY_MODEL_PATH}")

            if SCALER_PATH.exists():
                self.scaler = joblib.load(SCALER_PATH)
                print(f"✅ Loaded feature scaler from {SCALER_PATH}")

            if METADATA_PATH.exists():
                with open(METADATA_PATH, 'r') as f:
                    self.metadata = json.load(f)
                print(f"✅ Loaded model metadata from {METADATA_PATH}")

            return True
        except Exception as e:
            print(f"⚠️ Error loading models: {e}")
            return False

    def save_models(self) -> bool:
        """
        Save trained models to disk

        Returns:
            bool: True if models saved successfully
        """
        try:
            if self.distance_model:
                joblib.dump(self.distance_model, DISTANCE_MODEL_PATH)
                print(f"💾 Saved distance predictor to {DISTANCE_MODEL_PATH}")

            if self.shape_classifier:
                joblib.dump(self.shape_classifier, SHAPE_MODEL_PATH)
                print(f"💾 Saved shot shape classifier to {SHAPE_MODEL_PATH}")

            if self.anomaly_detector:
                joblib.dump(self.anomaly_detector, ANOMALY_MODEL_PATH)
                print(f"💾 Saved anomaly detector to {ANOMALY_MODEL_PATH}")

            if self.scaler:
                joblib.dump(self.scaler, SCALER_PATH)
                print(f"💾 Saved feature scaler to {SCALER_PATH}")

            # Update metadata
            self.metadata['last_updated'] = datetime.now().isoformat()
            with open(METADATA_PATH, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            print(f"💾 Saved model metadata to {METADATA_PATH}")

            return True
        except Exception as e:
            print(f"❌ Error saving models: {e}")
            return False

    # ==================== DISTANCE PREDICTION ====================

    def train_distance_predictor(self, df: pd.DataFrame, target_col: str = 'carry') -> Dict:
        """
        Train XGBoost model to predict carry distance

        Features used:
        - ball_speed, club_speed, launch_angle, back_spin, attack_angle
        - club (one-hot encoded)

        Args:
            df: Training data with shot metrics
            target_col: Column to predict (default: 'carry')

        Returns:
            dict: Training metrics (RMSE, R2, feature importance)
        """
        if not XGBOOST_AVAILABLE:
            return {"error": "XGBoost not installed"}

        # Filter valid data
        df_clean = df[
            (df[target_col] > 0) &
            (df[target_col] < 400) &
            (df['ball_speed'] > 0) &
            (df['club_speed'] > 0)
        ].copy()

        if len(df_clean) < 50:
            return {"error": f"Insufficient data. Need 50+ shots, got {len(df_clean)}"}

        # Feature engineering
        features = ['ball_speed', 'club_speed', 'launch_angle', 'back_spin', 'attack_angle']

        # Add smash factor if not present
        if 'smash_factor' not in df_clean.columns:
            df_clean['smash_factor'] = df_clean['ball_speed'] / df_clean['club_speed']
            features.append('smash_factor')

        # One-hot encode club
        club_dummies = pd.get_dummies(df_clean['club'], prefix='club')
        X = pd.concat([df_clean[features], club_dummies], axis=1)
        y = df_clean[target_col]

        # Handle missing values
        X = X.fillna(X.mean())

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train XGBoost model
        self.distance_model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            objective='reg:squarederror'
        )

        self.distance_model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = self.distance_model.predict(X_test_scaled)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        # Feature importance
        feature_importance = dict(zip(
            X.columns,
            self.distance_model.feature_importances_
        ))
        top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]

        # Save metadata
        self.metadata['distance_predictor'] = {
            'trained_date': datetime.now().isoformat(),
            'n_samples': len(df_clean),
            'rmse': float(rmse),
            'r2': float(r2),
            'features': list(X.columns),
            'top_features': dict(top_features)
        }

        return {
            'model': 'XGBoost Regressor',
            'n_samples': len(df_clean),
            'rmse': float(rmse),
            'r2': float(r2),
            'top_features': dict(top_features)
        }

    def predict_distance(self, features: Dict) -> Optional[float]:
        """
        Predict carry distance for given shot parameters

        Args:
            features: Dict with keys like ball_speed, club_speed, launch_angle, etc.

        Returns:
            Predicted carry distance (yards) or None if model not trained
        """
        if not self.distance_model or not self.scaler:
            return None

        try:
            # Create feature vector matching training data
            feature_df = pd.DataFrame([features])

            # Add smash factor if needed
            if 'smash_factor' not in feature_df.columns and 'ball_speed' in feature_df and 'club_speed' in feature_df:
                feature_df['smash_factor'] = feature_df['ball_speed'] / feature_df['club_speed']

            # One-hot encode club if present
            if 'club' in feature_df.columns:
                club_dummies = pd.get_dummies(feature_df['club'], prefix='club')
                feature_df = pd.concat([feature_df.drop('club', axis=1), club_dummies], axis=1)

            # Align with training features
            expected_features = self.metadata['distance_predictor']['features']
            for feat in expected_features:
                if feat not in feature_df.columns:
                    feature_df[feat] = 0

            feature_df = feature_df[expected_features]

            # Scale and predict
            X_scaled = self.scaler.transform(feature_df)
            prediction = self.distance_model.predict(X_scaled)[0]

            return float(prediction)
        except Exception as e:
            print(f"Prediction error: {e}")
            return None

    # ==================== SHOT SHAPE CLASSIFICATION ====================

    def train_shot_shape_classifier(self, df: pd.DataFrame) -> Dict:
        """
        Train classifier to identify shot shape (Draw, Fade, Straight, Hook, Slice)

        Based on:
        - side_spin (primary indicator)
        - club_path, face_angle (secondary)

        Args:
            df: Training data with side_spin column

        Returns:
            dict: Classification metrics (accuracy, F1 score)
        """
        # Filter valid data
        df_clean = df[
            (df['side_spin'].notna()) &
            (df['side_spin'] != 0) &
            (df['side_spin'] != 99999)
        ].copy()

        if len(df_clean) < 30:
            return {"error": f"Insufficient data. Need 30+ shots, got {len(df_clean)}"}

        # Label shots based on side_spin
        def classify_shape(side_spin):
            if side_spin < -500:
                return 'Draw'
            elif side_spin < -200:
                return 'Slight Draw'
            elif side_spin > 500:
                return 'Fade'
            elif side_spin > 200:
                return 'Slight Fade'
            else:
                return 'Straight'

        df_clean['shape'] = df_clean['side_spin'].apply(classify_shape)

        # Features
        features = ['side_spin', 'club_path', 'face_angle', 'ball_speed']
        available_features = [f for f in features if f in df_clean.columns]

        X = df_clean[available_features].fillna(0)
        y = df_clean['shape']

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Train logistic regression
        self.shape_classifier = LogisticRegression(max_iter=1000, random_state=42)
        self.shape_classifier.fit(X_train, y_train)

        # Evaluate
        y_pred = self.shape_classifier.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)

        # Save metadata
        self.metadata['shape_classifier'] = {
            'trained_date': datetime.now().isoformat(),
            'n_samples': len(df_clean),
            'accuracy': float(accuracy),
            'features': available_features,
            'classes': list(self.shape_classifier.classes_)
        }

        return {
            'model': 'Logistic Regression',
            'n_samples': len(df_clean),
            'accuracy': float(accuracy),
            'classes': list(self.shape_classifier.classes_),
            'f1_weighted': float(report['weighted avg']['f1-score'])
        }

    def predict_shot_shape(self, features: Dict) -> Optional[str]:
        """
        Predict shot shape from swing metrics

        Args:
            features: Dict with side_spin, club_path, face_angle, etc.

        Returns:
            Shot shape label or None if model not trained
        """
        if not self.shape_classifier:
            return None

        try:
            expected_features = self.metadata['shape_classifier']['features']
            feature_df = pd.DataFrame([features])

            # Align features
            for feat in expected_features:
                if feat not in feature_df.columns:
                    feature_df[feat] = 0

            feature_df = feature_df[expected_features]

            shape = self.shape_classifier.predict(feature_df)[0]
            return shape
        except Exception as e:
            print(f"Shape prediction error: {e}")
            return None

    # ==================== SWING DIAGNOSTICS ====================

    def train_anomaly_detector(self, df: pd.DataFrame) -> Dict:
        """
        Train Isolation Forest to detect unusual swing patterns

        Args:
            df: Swing data with metrics like club_speed, attack_angle, etc.

        Returns:
            dict: Model stats
        """
        # Features for anomaly detection
        features = ['club_speed', 'ball_speed', 'smash_factor', 'launch_angle',
                   'back_spin', 'attack_angle', 'club_path', 'face_angle']

        available_features = [f for f in features if f in df.columns]

        if not available_features:
            return {"error": "No swing metrics available"}

        df_clean = df[available_features].fillna(0)
        df_clean = df_clean[(df_clean != 0).any(axis=1)]

        if len(df_clean) < 20:
            return {"error": f"Insufficient data. Need 20+ shots, got {len(df_clean)}"}

        # Train Isolation Forest
        self.anomaly_detector = IsolationForest(
            contamination=0.1,  # Expect 10% outliers
            random_state=42
        )

        self.anomaly_detector.fit(df_clean)

        # Save metadata
        self.metadata['anomaly_detector'] = {
            'trained_date': datetime.now().isoformat(),
            'n_samples': len(df_clean),
            'features': available_features
        }

        return {
            'model': 'Isolation Forest',
            'n_samples': len(df_clean),
            'features': available_features
        }

    def detect_swing_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Identify shots with unusual swing patterns

        Args:
            df: Shot data to analyze

        Returns:
            DataFrame with anomaly scores (-1 = anomaly, 1 = normal)
        """
        if not self.anomaly_detector:
            return df

        try:
            expected_features = self.metadata['anomaly_detector']['features']
            X = df[expected_features].fillna(0)

            df['anomaly'] = self.anomaly_detector.predict(X)
            df['anomaly_score'] = self.anomaly_detector.score_samples(X)

            return df
        except Exception as e:
            print(f"Anomaly detection error: {e}")
            return df

    # ==================== USER PROFILE & BASELINES ====================

    def calculate_user_profile(self, df: pd.DataFrame) -> Dict:
        """
        Calculate user's baseline statistics per club

        Args:
            df: User's shot history

        Returns:
            dict: Profile with avg/std metrics per club
        """
        profile = {}

        for club in df['club'].unique():
            club_data = df[df['club'] == club]

            # Clean data
            carry = club_data[(club_data['carry'] > 0) & (club_data['carry'] < 400)]['carry']
            ball_speed = club_data[(club_data['ball_speed'] > 0)]['ball_speed']
            smash = club_data[(club_data['smash_factor'] > 0) & (club_data['smash_factor'] < 1.6)]['smash_factor']

            profile[club] = {
                'n_shots': len(club_data),
                'carry_avg': float(carry.mean()) if len(carry) > 0 else 0,
                'carry_std': float(carry.std()) if len(carry) > 0 else 0,
                'ball_speed_avg': float(ball_speed.mean()) if len(ball_speed) > 0 else 0,
                'smash_avg': float(smash.mean()) if len(smash) > 0 else 0,
                'consistency_score': self._calculate_consistency(carry) if len(carry) > 5 else 0
            }

        return profile

    def _calculate_consistency(self, values: pd.Series) -> float:
        """
        Calculate consistency score (0-100) based on coefficient of variation

        Lower CV = higher consistency
        """
        if len(values) == 0 or values.mean() == 0:
            return 0

        cv = values.std() / values.mean()
        consistency = max(0, 100 - (cv * 100))
        return float(consistency)

    # ==================== COACHING RECOMMENDATIONS ====================

    def generate_insights(self, df: pd.DataFrame, club: str = None) -> List[str]:
        """
        Generate coaching insights based on shot data

        Args:
            df: Shot data to analyze
            club: Optional club filter

        Returns:
            List of insight strings
        """
        insights = []

        if club:
            df = df[df['club'] == club]

        if len(df) == 0:
            return ["No data available for analysis"]

        # Carry distance analysis
        carry = df[(df['carry'] > 0) & (df['carry'] < 400)]['carry']
        if len(carry) > 5:
            avg_carry = carry.mean()
            std_carry = carry.std()
            cv = std_carry / avg_carry if avg_carry > 0 else 0

            if cv > 0.15:
                insights.append(f"⚠️ High carry distance variance ({std_carry:.1f} yds). Focus on tempo and rhythm.")
            else:
                insights.append(f"✅ Excellent carry consistency ({std_carry:.1f} yds std dev).")

        # Smash factor analysis
        smash = df[(df['smash_factor'] > 0) & (df['smash_factor'] < 1.6)]['smash_factor']
        if len(smash) > 5:
            avg_smash = smash.mean()

            if avg_smash < 1.35:
                insights.append(f"📉 Low smash factor ({avg_smash:.2f}). Check centeredness of contact.")
            elif avg_smash > 1.48:
                insights.append(f"🎯 Elite smash factor ({avg_smash:.2f})! Great ball striking.")

        # Launch angle analysis
        launch = df[(df['launch_angle'] > 0) & (df['launch_angle'] < 30)]['launch_angle']
        if len(launch) > 5 and club:
            avg_launch = launch.mean()

            if 'Driver' in club and avg_launch < 10:
                insights.append(f"⬆️ Launch angle too low ({avg_launch:.1f}°). Try teeing higher or adjusting ball position.")
            elif 'Driver' in club and avg_launch > 16:
                insights.append(f"⬇️ Launch angle too high ({avg_launch:.1f}°). May be losing distance.")

        # Spin analysis
        spin = df[(df['back_spin'] > 0) & (df['back_spin'] < 10000)]['back_spin']
        if len(spin) > 5 and club:
            avg_spin = spin.mean()

            if 'Driver' in club and avg_spin > 3000:
                insights.append(f"🌀 High driver spin ({avg_spin:.0f} rpm). May benefit from delofting or ball position adjustment.")

        if not insights:
            insights.append("📊 Solid performance overall. Keep up the good work!")

        return insights


# ==================== MODULE-LEVEL FUNCTIONS ====================

def get_coach() -> AICoach:
    """
    Get singleton AI Coach instance

    Returns:
        AICoach instance
    """
    if not hasattr(get_coach, 'instance'):
        get_coach.instance = AICoach()
    return get_coach.instance
