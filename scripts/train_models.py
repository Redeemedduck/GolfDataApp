"""
Model Training Pipeline

Trains all ML models (distance predictor, shot classifier, anomaly detector)
using data from the SQLite database.

Usage:
    python scripts/train_models.py [--all | --distance | --shape | --anomaly]

Examples:
    python scripts/train_models.py --all        # Train all models
    python scripts/train_models.py --distance   # Train only distance predictor
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import argparse
import pandas as pd
from utils import golf_db, ai_coach


def load_training_data() -> pd.DataFrame:
    """
    Load all shot data from database for training

    Returns:
        DataFrame with all shots
    """
    print("📊 Loading training data from database...")
    golf_db.init_db()
    df = golf_db.get_all_shots()

    print(f"✅ Loaded {len(df)} shots")
    print(f"📅 Date range: {df['session_date'].min()} to {df['session_date'].max()}")
    print(f"🏌️ Clubs: {df['club'].nunique()} unique clubs")
    print(f"📍 Sessions: {df['session_id'].nunique()} sessions")

    return df


def train_distance_model(coach: ai_coach.AICoach, df: pd.DataFrame) -> None:
    """
    Train distance prediction model

    Args:
        coach: AICoach instance
        df: Training data
    """
    print("\n" + "="*60)
    print("🎯 TRAINING DISTANCE PREDICTOR (XGBoost)")
    print("="*60)

    # Check for sufficient data
    valid_shots = df[
        (df['carry'] > 0) &
        (df['carry'] < 400) &
        (df['ball_speed'] > 0) &
        (df['club_speed'] > 0)
    ]

    if len(valid_shots) < 50:
        print(f"❌ Insufficient data for distance model: {len(valid_shots)} shots")
        print("   Need at least 50 shots with valid carry, ball_speed, and club_speed")
        return

    # Train model
    results = coach.train_distance_predictor(df, target_col='carry')

    if 'error' in results:
        print(f"❌ Training failed: {results['error']}")
        return

    # Display results
    print(f"\n✅ Model trained successfully!")
    print(f"   Samples: {results['n_samples']}")
    print(f"   RMSE: {results['rmse']:.2f} yards")
    print(f"   R²: {results['r2']:.3f}")
    print(f"\n📊 Top 5 Important Features:")
    for i, (feature, importance) in enumerate(results['top_features'].items(), 1):
        print(f"   {i}. {feature}: {importance:.3f}")


def train_shape_classifier(coach: ai_coach.AICoach, df: pd.DataFrame) -> None:
    """
    Train shot shape classification model

    Args:
        coach: AICoach instance
        df: Training data
    """
    print("\n" + "="*60)
    print("🎯 TRAINING SHOT SHAPE CLASSIFIER")
    print("="*60)

    # Check for side_spin data
    valid_shots = df[
        (df['side_spin'].notna()) &
        (df['side_spin'] != 0) &
        (df['side_spin'] != 99999)
    ]

    if len(valid_shots) < 30:
        print(f"❌ Insufficient data for shape classifier: {len(valid_shots)} shots")
        print("   Need at least 30 shots with valid side_spin data")
        return

    # Train model
    results = coach.train_shot_shape_classifier(df)

    if 'error' in results:
        print(f"❌ Training failed: {results['error']}")
        return

    # Display results
    print(f"\n✅ Model trained successfully!")
    print(f"   Samples: {results['n_samples']}")
    print(f"   Accuracy: {results['accuracy']:.2%}")
    print(f"   F1 Score: {results['f1_weighted']:.3f}")
    print(f"\n📊 Shot Shape Classes:")
    for i, shape in enumerate(results['classes'], 1):
        print(f"   {i}. {shape}")


def train_anomaly_detector(coach: ai_coach.AICoach, df: pd.DataFrame) -> None:
    """
    Train swing anomaly detection model

    Args:
        coach: AICoach instance
        df: Training data
    """
    print("\n" + "="*60)
    print("🎯 TRAINING SWING ANOMALY DETECTOR")
    print("="*60)

    # Check for swing metrics
    swing_features = ['club_speed', 'ball_speed', 'smash_factor', 'attack_angle']
    available = [f for f in swing_features if f in df.columns and df[f].notna().any()]

    if len(available) < 2:
        print(f"❌ Insufficient swing data: only {len(available)} metrics available")
        return

    # Train model
    results = coach.train_anomaly_detector(df)

    if 'error' in results:
        print(f"❌ Training failed: {results['error']}")
        return

    # Display results
    print(f"\n✅ Model trained successfully!")
    print(f"   Samples: {results['n_samples']}")
    print(f"   Features used: {', '.join(results['features'])}")


def main():
    """Main training pipeline"""
    parser = argparse.ArgumentParser(description='Train ML models for golf analytics')
    parser.add_argument(
        '--all', action='store_true',
        help='Train all models'
    )
    parser.add_argument(
        '--distance', action='store_true',
        help='Train distance predictor only'
    )
    parser.add_argument(
        '--shape', action='store_true',
        help='Train shot shape classifier only'
    )
    parser.add_argument(
        '--anomaly', action='store_true',
        help='Train anomaly detector only'
    )

    args = parser.parse_args()

    # Default to --all if no flags specified
    if not any([args.all, args.distance, args.shape, args.anomaly]):
        args.all = True

    print("="*60)
    print("🤖 GOLF ML TRAINING PIPELINE")
    print("="*60)

    # Load data
    df = load_training_data()

    if len(df) == 0:
        print("\n❌ No data available for training!")
        print("   Please import some sessions first using the Data Import page.")
        return

    # Initialize AI Coach
    coach = ai_coach.get_coach()

    # Train models based on flags
    if args.all or args.distance:
        train_distance_model(coach, df)

    if args.all or args.shape:
        train_shape_classifier(coach, df)

    if args.all or args.anomaly:
        train_anomaly_detector(coach, df)

    # Save all models
    print("\n" + "="*60)
    print("💾 SAVING MODELS")
    print("="*60)

    if coach.save_models():
        print("\n✅ All models saved successfully!")
        print(f"   Location: {ai_coach.MODELS_DIR}")
        print("\n📝 Model files:")
        for model_file in ai_coach.MODELS_DIR.glob('*.pkl'):
            print(f"   - {model_file.name}")
        if ai_coach.METADATA_PATH.exists():
            print(f"   - {ai_coach.METADATA_PATH.name}")
    else:
        print("\n❌ Error saving models")

    print("\n" + "="*60)
    print("✅ TRAINING COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
