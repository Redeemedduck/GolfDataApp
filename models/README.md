# Models Directory

This directory stores trained machine learning models for golf performance analysis.

## Model Files

### distance_predictor.pkl
- **Type**: XGBoost Regressor
- **Purpose**: Predict carry distance based on swing metrics
- **Features**: ball_speed, club_speed, launch_angle, back_spin, attack_angle, smash_factor, club (one-hot)
- **Target**: carry distance (yards)
- **Metrics**: RMSE (yards), R² score

### shot_shape_classifier.pkl
- **Type**: Logistic Regression Classifier
- **Purpose**: Classify shot shape (Draw, Fade, Straight, Hook, Slice)
- **Features**: side_spin, club_path, face_angle, ball_speed
- **Target**: shot shape category
- **Metrics**: Accuracy, F1 score

### swing_anomaly_detector.pkl
- **Type**: Isolation Forest
- **Purpose**: Detect unusual swing patterns and outliers
- **Features**: club_speed, ball_speed, smash_factor, launch_angle, back_spin, attack_angle, club_path, face_angle
- **Output**: Anomaly score (-1 = anomaly, 1 = normal)
- **Metrics**: Contamination rate (10%)

### feature_scaler.pkl
- **Type**: Standard Scaler
- **Purpose**: Normalize features for distance prediction
- **Transform**: z-score normalization (mean=0, std=1)

### model_metadata.json
- **Type**: JSON metadata file
- **Purpose**: Store training info, metrics, and feature names
- **Contents**:
  - Training date
  - Number of samples
  - Model metrics (RMSE, accuracy, etc.)
  - Feature lists
  - Feature importance (for tree models)

## Training

To train models, run:

```bash
# Train all models
python scripts/train_models.py --all

# Train specific models
python scripts/train_models.py --distance
python scripts/train_models.py --shape
python scripts/train_models.py --anomaly
```

## Evaluation

To evaluate trained models:

```bash
# Quick evaluation
python scripts/evaluate_models.py

# Detailed evaluation with examples
python scripts/evaluate_models.py --detailed
```

## Usage in Code

```python
from utils import ai_coach

# Get AI Coach instance
coach = ai_coach.get_coach()

# Predict distance
prediction = coach.predict_distance({
    'ball_speed': 165,
    'club_speed': 110,
    'launch_angle': 12,
    'back_spin': 2500,
    'attack_angle': 3,
    'club': 'Driver'
})

# Predict shot shape
shape = coach.predict_shot_shape({
    'side_spin': -300,
    'club_path': -2.5,
    'face_angle': -1.5,
    'ball_speed': 165
})

# Detect anomalies
df_with_anomalies = coach.detect_swing_anomalies(df)
anomalies = df_with_anomalies[df_with_anomalies['anomaly'] == -1]

# Generate insights
insights = coach.generate_insights(df, club='Driver')
for insight in insights:
    print(insight)
```

## Requirements

Minimum data requirements for training:
- **Distance Predictor**: 50+ shots with valid carry, ball_speed, club_speed
- **Shape Classifier**: 30+ shots with valid side_spin data
- **Anomaly Detector**: 20+ shots with swing metrics

## File Size

Trained models are typically:
- distance_predictor.pkl: ~500 KB - 2 MB
- shot_shape_classifier.pkl: ~100 KB
- swing_anomaly_detector.pkl: ~200 KB
- feature_scaler.pkl: ~10 KB
- model_metadata.json: ~5 KB

**Note**: .pkl files are excluded from git (see .gitignore) to keep repository size small.

## Retraining

Models should be retrained when:
1. Significant new data is available (50+ new shots)
2. Performance degrades (high prediction errors)
3. Swing changes occur (new equipment, lessons, etc.)
4. Seasonally (every 1-3 months)

## Future Enhancements

Phase 5 & 6 will add:
- Vertex AI cloud models (optional)
- Auto-retraining pipeline
- A/B testing framework
- Model versioning
- Performance monitoring dashboard
