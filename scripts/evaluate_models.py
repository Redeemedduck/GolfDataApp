"""
Model Evaluation Script

Evaluates trained ML models and generates performance reports.

Usage:
    python scripts/evaluate_models.py [--detailed]

Examples:
    python scripts/evaluate_models.py            # Quick evaluation
    python scripts/evaluate_models.py --detailed # Detailed metrics with examples
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import argparse
import pandas as pd
import numpy as np
from utils import golf_db, ai_coach


def evaluate_distance_model(coach: ai_coach.AICoach, df: pd.DataFrame, detailed: bool = False) -> None:
    """
    Evaluate distance prediction model

    Args:
        coach: AICoach instance
        df: Test data
        detailed: Show detailed metrics and examples
    """
    print("\n" + "="*60)
    print("🎯 DISTANCE PREDICTOR EVALUATION")
    print("="*60)

    if not coach.distance_model:
        print("❌ Distance model not trained. Run train_models.py first.")
        return

    # Load metadata
    if 'distance_predictor' not in coach.metadata:
        print("⚠️  No metadata available")
        return

    meta = coach.metadata['distance_predictor']

    print(f"\n📊 Training Info:")
    print(f"   Trained: {meta['trained_date']}")
    print(f"   Samples: {meta['n_samples']}")
    print(f"   RMSE: {meta['rmse']:.2f} yards")
    print(f"   R²: {meta['r2']:.3f}")

    if detailed:
        print(f"\n🔬 Feature Importance:")
        for feature, importance in meta['top_features'].items():
            bar_length = int(importance * 50)
            bar = "█" * bar_length
            print(f"   {feature:20s} {bar} {importance:.3f}")

        # Test predictions
        print(f"\n🧪 Sample Predictions (first 5 valid shots):")
        print(f"   {'Actual':>8} {'Predicted':>10} {'Error':>8}  Club")
        print(f"   {'-'*8} {'-'*10} {'-'*8}  {'-'*15}")

        valid_shots = df[
            (df['carry'] > 0) &
            (df['carry'] < 400) &
            (df['ball_speed'] > 0) &
            (df['club_speed'] > 0)
        ].head(5)

        for _, row in valid_shots.iterrows():
            features = {
                'ball_speed': row['ball_speed'],
                'club_speed': row['club_speed'],
                'launch_angle': row.get('launch_angle', 0),
                'back_spin': row.get('back_spin', 0),
                'attack_angle': row.get('attack_angle', 0),
                'club': row['club']
            }

            prediction = coach.predict_distance(features)

            if prediction:
                error = prediction - row['carry']
                print(f"   {row['carry']:8.1f} {prediction:10.1f} {error:+8.1f}  {row['club']}")


def evaluate_shape_classifier(coach: ai_coach.AICoach, df: pd.DataFrame, detailed: bool = False) -> None:
    """
    Evaluate shot shape classification model

    Args:
        coach: AICoach instance
        df: Test data
        detailed: Show detailed metrics and examples
    """
    print("\n" + "="*60)
    print("🎯 SHOT SHAPE CLASSIFIER EVALUATION")
    print("="*60)

    if not coach.shape_classifier:
        print("❌ Shape classifier not trained. Run train_models.py first.")
        return

    # Load metadata
    if 'shape_classifier' not in coach.metadata:
        print("⚠️  No metadata available")
        return

    meta = coach.metadata['shape_classifier']

    print(f"\n📊 Training Info:")
    print(f"   Trained: {meta['trained_date']}")
    print(f"   Samples: {meta['n_samples']}")
    print(f"   Accuracy: {meta['accuracy']:.2%}")
    print(f"   Classes: {', '.join(meta['classes'])}")

    if detailed:
        print(f"\n🧪 Sample Predictions (first 5 valid shots):")
        print(f"   {'Side Spin':>10} {'Club Path':>10} {'Predicted Shape':>20}")
        print(f"   {'-'*10} {'-'*10} {'-'*20}")

        valid_shots = df[
            (df['side_spin'].notna()) &
            (df['side_spin'] != 0) &
            (df['side_spin'] != 99999)
        ].head(5)

        for _, row in valid_shots.iterrows():
            features = {
                'side_spin': row['side_spin'],
                'club_path': row.get('club_path', 0),
                'face_angle': row.get('face_angle', 0),
                'ball_speed': row.get('ball_speed', 0)
            }

            shape = coach.predict_shot_shape(features)

            if shape:
                print(f"   {row['side_spin']:10.0f} {row.get('club_path', 0):10.2f} {shape:>20}")


def evaluate_anomaly_detector(coach: ai_coach.AICoach, df: pd.DataFrame, detailed: bool = False) -> None:
    """
    Evaluate swing anomaly detection model

    Args:
        coach: AICoach instance
        df: Test data
        detailed: Show detailed metrics and examples
    """
    print("\n" + "="*60)
    print("🎯 SWING ANOMALY DETECTOR EVALUATION")
    print("="*60)

    if not coach.anomaly_detector:
        print("❌ Anomaly detector not trained. Run train_models.py first.")
        return

    # Load metadata
    if 'anomaly_detector' not in coach.metadata:
        print("⚠️  No metadata available")
        return

    meta = coach.metadata['anomaly_detector']

    print(f"\n📊 Training Info:")
    print(f"   Trained: {meta['trained_date']}")
    print(f"   Samples: {meta['n_samples']}")
    print(f"   Features: {', '.join(meta['features'])}")

    if detailed:
        # Detect anomalies in test set
        df_with_anomalies = coach.detect_swing_anomalies(df.head(100))

        anomalies = df_with_anomalies[df_with_anomalies['anomaly'] == -1]

        print(f"\n🚨 Anomalies Detected: {len(anomalies)} / {len(df_with_anomalies)} ({len(anomalies)/len(df_with_anomalies)*100:.1f}%)")

        if len(anomalies) > 0:
            print(f"\n🔍 Top 5 Anomalous Swings:")
            print(f"   {'Shot ID':>10} {'Club':>10} {'Smash':>8} {'Launch':>8} {'Score':>10}")
            print(f"   {'-'*10} {'-'*10} {'-'*8} {'-'*8} {'-'*10}")

            top_anomalies = anomalies.nsmallest(5, 'anomaly_score')

            for _, row in top_anomalies.iterrows():
                print(f"   {row['shot_id']:>10} {row['club']:>10} {row.get('smash_factor', 0):8.2f} "
                     f"{row.get('launch_angle', 0):8.1f} {row['anomaly_score']:10.3f}")


def generate_insights_report(coach: ai_coach.AICoach, df: pd.DataFrame) -> None:
    """
    Generate coaching insights report

    Args:
        coach: AICoach instance
        df: Shot data
    """
    print("\n" + "="*60)
    print("💡 COACHING INSIGHTS")
    print("="*60)

    # Overall insights
    insights = coach.generate_insights(df)

    print(f"\n📋 Overall Performance:")
    for insight in insights:
        print(f"   {insight}")

    # Per-club insights
    print(f"\n📋 Club-Specific Insights:")

    clubs = df['club'].value_counts().head(5).index

    for club in clubs:
        club_insights = coach.generate_insights(df, club=club)
        if club_insights:
            print(f"\n   {club}:")
            for insight in club_insights:
                print(f"      {insight}")


def generate_user_profile(coach: ai_coach.AICoach, df: pd.DataFrame) -> None:
    """
    Generate user profile report

    Args:
        coach: AICoach instance
        df: Shot data
    """
    print("\n" + "="*60)
    print("👤 USER PROFILE")
    print("="*60)

    profile = coach.calculate_user_profile(df)

    print(f"\n📊 Baseline Statistics by Club:")
    print(f"   {'Club':>15} {'Shots':>8} {'Carry Avg':>10} {'Carry Std':>10} {'Smash':>8} {'Consistency':>12}")
    print(f"   {'-'*15} {'-'*8} {'-'*10} {'-'*10} {'-'*8} {'-'*12}")

    for club, stats in sorted(profile.items(), key=lambda x: x[1]['carry_avg'], reverse=True):
        if stats['n_shots'] > 0:
            print(f"   {club:>15} {stats['n_shots']:8d} {stats['carry_avg']:10.1f} "
                 f"{stats['carry_std']:10.1f} {stats['smash_avg']:8.2f} {stats['consistency_score']:12.0f}/100")


def main():
    """Main evaluation pipeline"""
    parser = argparse.ArgumentParser(description='Evaluate trained ML models')
    parser.add_argument(
        '--detailed', action='store_true',
        help='Show detailed metrics and examples'
    )

    args = parser.parse_args()

    print("="*60)
    print("📊 GOLF ML MODEL EVALUATION")
    print("="*60)

    # Load data
    print("\n📊 Loading test data from database...")
    golf_db.init_db()
    df = golf_db.get_all_shots()

    if len(df) == 0:
        print("\n❌ No data available for evaluation!")
        return

    print(f"✅ Loaded {len(df)} shots for evaluation")

    # Initialize AI Coach
    coach = ai_coach.get_coach()

    # Check if models exist
    models_exist = any([
        coach.distance_model,
        coach.shape_classifier,
        coach.anomaly_detector
    ])

    if not models_exist:
        print("\n❌ No models found! Run train_models.py first.")
        return

    # Evaluate each model
    evaluate_distance_model(coach, df, detailed=args.detailed)
    evaluate_shape_classifier(coach, df, detailed=args.detailed)
    evaluate_anomaly_detector(coach, df, detailed=args.detailed)

    # Generate insights
    generate_insights_report(coach, df)

    # Generate user profile
    generate_user_profile(coach, df)

    print("\n" + "="*60)
    print("✅ EVALUATION COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
