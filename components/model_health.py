"""
Model health dashboard component.
"""
import streamlit as st
import pandas as pd
import sqlite3
from typing import Optional

# Plotly imports
try:
    import plotly.graph_objects as go
except ImportError:
    go = None

# ML imports with graceful degradation
try:
    from ml import ML_AVAILABLE
except ImportError:
    ML_AVAILABLE = False

try:
    from ml.train_models import (
        DistancePredictor,
        get_model_info,
        DISTANCE_MODEL_PATH,
        HAS_MAPIE
    )
except ImportError:
    DistancePredictor = None
    get_model_info = None
    DISTANCE_MODEL_PATH = None
    HAS_MAPIE = False

try:
    from ml.monitoring import DriftDetector
except ImportError:
    DriftDetector = None

try:
    import golf_db
except ImportError:
    golf_db = None


def render_model_health_dashboard() -> None:
    """
    Render model health dashboard with drift monitoring, feature importance, and retraining controls.

    Shows:
    - Current model info (version, date, samples, MAE)
    - Drift status alert with retrain button
    - Auto-retraining toggle
    - MAE trend chart over sessions
    - Feature importance bar chart
    - Performance history table
    """
    # Section 1: ML Availability Check
    if not ML_AVAILABLE:
        st.warning(
            "⚠️ ML features not available. Missing ML dependencies.\n\n"
            "Install with:\n"
            "```bash\n"
            "pip install xgboost scikit-learn joblib\n"
            "```"
        )
        return

    # Section 2: Current Model Info
    st.subheader("📊 Current Model Status")

    model_metadata = None
    if get_model_info and DISTANCE_MODEL_PATH:
        try:
            from pathlib import Path
            if Path(DISTANCE_MODEL_PATH).exists():
                model_metadata = get_model_info(DISTANCE_MODEL_PATH)
        except Exception as e:
            st.error(f"Error loading model info: {e}")

    if model_metadata:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Model Version", model_metadata.version)

        with col2:
            # Format training date
            trained_at = model_metadata.trained_at
            if 'T' in trained_at:
                trained_at = trained_at.split('T')[0]
            st.metric("Trained Date", trained_at)

        with col3:
            st.metric("Training Samples", f"{model_metadata.training_samples:,}")

        with col4:
            mae = model_metadata.metrics.get('mae', 0)
            st.metric("Training MAE", f"{mae:.1f} yd")

        # Show R2 if available
        r2 = model_metadata.metrics.get('r2')
        if r2 is not None:
            st.caption(f"📈 R² Score: {r2:.3f}")

        # Show interval status
        if HAS_MAPIE and model_metadata.model_type == 'xgboost_regressor_with_intervals':
            confidence = model_metadata.metrics.get('confidence_level', 0.95)
            st.caption(f"✅ Prediction intervals enabled ({confidence * 100:.0f}% confidence)")
        else:
            st.caption("ℹ️ Prediction intervals not available")
    else:
        st.info("ℹ️ No model trained yet. Train a model to see health metrics.")
        return

    st.divider()

    # Section 3: Drift Status Alert + Auto-Retrain Toggle
    st.subheader("🔍 Model Drift Detection")

    drift_detector = None
    consecutive_drift = 0
    recent_drift_sessions = []

    if DriftDetector:
        try:
            drift_detector = DriftDetector()
            consecutive_drift = drift_detector.get_consecutive_drift_count()
            recent_drift_sessions = drift_detector.get_drift_history(limit=5)
        except Exception as e:
            st.warning(f"Drift detection unavailable: {e}")

    # Drift Alert
    if consecutive_drift >= 3:
        st.error(
            f"⚠️ **Model Drift Detected**\n\n"
            f"The model has shown elevated error for {consecutive_drift} consecutive sessions. "
            f"Retraining is recommended to maintain prediction accuracy."
        )

        # Show MAE details
        if recent_drift_sessions:
            latest = recent_drift_sessions[0]
            baseline_mae = latest.get('baseline_mae', 0)
            session_mae = latest.get('session_mae', 0)
            drift_pct = latest.get('drift_percentage', 0)
            st.caption(
                f"Latest session MAE: {session_mae:.1f} yd "
                f"(baseline: {baseline_mae:.1f} yd, +{drift_pct:.0f}%)"
            )

        # Retrain button (primary)
        if st.button("🔄 Retrain Model Now", type="primary", key="health_retrain"):
            _trigger_retraining(model_metadata)

    elif any(s.get('has_drift', False) for s in recent_drift_sessions):
        st.warning(
            "⚡ **Elevated Error Detected**\n\n"
            "Some recent sessions show higher prediction error than baseline. "
            "Monitor performance or retrain if issues persist."
        )

        # Retrain button (secondary)
        if st.button("🔄 Retrain Model", key="health_retrain_warning"):
            _trigger_retraining(model_metadata)

    else:
        st.success(
            "✅ **Model Performing Well**\n\n"
            "Prediction error is within expected range. No drift detected."
        )

    # Auto-retrain toggle
    st.divider()

    if 'auto_retrain_enabled' not in st.session_state:
        st.session_state.auto_retrain_enabled = False

    auto_retrain = st.toggle(
        "Enable Auto-Retraining",
        value=st.session_state.auto_retrain_enabled,
        key="auto_retrain_toggle",
        help="When enabled, model automatically retrains after 3 consecutive drift sessions"
    )

    st.session_state.auto_retrain_enabled = auto_retrain

    if auto_retrain:
        st.caption("✅ Auto-retraining is **enabled**. Model will retrain after 3 consecutive drift sessions.")
    else:
        st.caption("ℹ️ Auto-retraining is **disabled**. Manual retraining required.")

    st.divider()

    # Section 4: MAE Trend Chart
    st.subheader("📈 Prediction Error Trend")

    perf_df = _load_performance_data()

    if perf_df.empty:
        st.info("No performance data available yet. Performance tracking begins after model predictions.")
    else:
        # Create Plotly figure
        if go:
            fig = go.Figure()

            # Get training MAE for reference line
            training_mae = model_metadata.metrics.get('mae', 0) if model_metadata else 0

            # Add session MAE line with color-coded markers
            colors = ['red' if row.get('has_drift', False) else 'blue' for _, row in perf_df.iterrows()]

            fig.add_trace(go.Scatter(
                x=perf_df['timestamp'],
                y=perf_df['session_mae'],
                mode='lines+markers',
                name='Session MAE',
                line=dict(color='blue', width=2),
                marker=dict(color=colors, size=8),
                hovertemplate='<b>%{x|%Y-%m-%d}</b><br>MAE: %{y:.1f} yd<extra></extra>'
            ))

            # Add baseline MAE line
            fig.add_trace(go.Scatter(
                x=perf_df['timestamp'],
                y=perf_df['baseline_mae'],
                mode='lines',
                name='Baseline MAE',
                line=dict(color='gray', width=2, dash='dash'),
                hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Baseline: %{y:.1f} yd<extra></extra>'
            ))

            # Add training MAE reference line
            if training_mae > 0:
                fig.add_trace(go.Scatter(
                    x=perf_df['timestamp'],
                    y=[training_mae] * len(perf_df),
                    mode='lines',
                    name='Training MAE',
                    line=dict(color='green', width=2, dash='dot'),
                    hovertemplate=f'Training MAE: {training_mae:.1f} yd<extra></extra>'
                ))

            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="MAE (yards)",
                height=400,
                hovermode='x unified',
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)
            st.caption("🔵 Normal session · 🔴 Drift detected · Gray dashed = Baseline · Green dotted = Training MAE")
        else:
            st.warning("Plotly not available for chart rendering")

    st.divider()

    # Section 5: Feature Importance
    st.subheader("🎯 Feature Importance")

    try:
        if DistancePredictor:
            predictor = DistancePredictor()
            predictor.load()

            # Get feature importances
            if hasattr(predictor, 'model') and predictor.model:
                # Handle both wrapped and direct models
                if isinstance(predictor.model, dict) and 'base_model' in predictor.model:
                    base_model = predictor.model['base_model']
                else:
                    base_model = predictor.model

                if hasattr(base_model, 'feature_importances_'):
                    importances = base_model.feature_importances_
                    feature_names = predictor._feature_names if hasattr(predictor, '_feature_names') else [f"Feature {i}" for i in range(len(importances))]

                    # Create DataFrame and sort
                    importance_df = pd.DataFrame({
                        'feature': feature_names,
                        'importance': importances
                    }).sort_values('importance', ascending=True)

                    # Create horizontal bar chart
                    if go:
                        fig = go.Figure(go.Bar(
                            x=importance_df['importance'],
                            y=importance_df['feature'],
                            orientation='h',
                            marker_color='lightblue'
                        ))

                        fig.update_layout(
                            xaxis_title="Importance Score",
                            yaxis_title="Feature",
                            height=300,
                            margin=dict(l=150)
                        )

                        st.plotly_chart(fig, use_container_width=True)
                        st.caption("Higher scores indicate features that contribute more to distance predictions.")
                    else:
                        st.dataframe(importance_df, use_container_width=True)
                else:
                    st.info("Feature importances not available for this model type")
            else:
                st.info("Model not loaded. Train a model to see feature importances.")
        else:
            st.info("DistancePredictor not available")
    except Exception as e:
        st.warning(f"Could not load feature importances: {e}")

    st.divider()

    # Section 6: Performance History Table
    st.subheader("📋 Session History")

    if not perf_df.empty:
        # Format table
        history_df = perf_df.tail(20).copy()
        history_df['Session'] = history_df['session_id']
        history_df['MAE (yd)'] = history_df['session_mae'].round(1)
        history_df['Baseline (yd)'] = history_df['baseline_mae'].round(1)
        history_df['Drift %'] = history_df['drift_percentage'].round(0).astype(int)
        history_df['Status'] = history_df['has_drift'].apply(lambda x: '🔴 Drift' if x else '✅ OK')

        display_cols = ['Session', 'MAE (yd)', 'Baseline (yd)', 'Drift %', 'Status']
        st.dataframe(
            history_df[display_cols],
            use_container_width=True,
            hide_index=True
        )

        st.caption(f"Showing last {min(20, len(history_df))} sessions")
    else:
        st.info("No session history available yet")


def _load_performance_data() -> pd.DataFrame:
    """Load model performance data from database."""
    if not golf_db:
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(golf_db.SQLITE_DB_PATH)
        query = """
            SELECT
                session_id,
                timestamp,
                session_mae,
                baseline_mae,
                drift_percentage,
                has_drift,
                model_version
            FROM model_performance
            ORDER BY timestamp ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Convert timestamp to datetime
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df
    except Exception as e:
        st.warning(f"Could not load performance data: {e}")
        return pd.DataFrame()


def _trigger_retraining(current_metadata) -> None:
    """Trigger model retraining with progress feedback."""
    if not DistancePredictor or not golf_db:
        st.error("Required components not available for retraining")
        return

    with st.spinner("Training model... This may take up to 60 seconds"):
        try:
            import time
            start_time = time.time()

            # Get data
            golf_db.init_db()
            df = golf_db.get_all_shots()

            if df.empty:
                st.error("No shot data available for training")
                return

            shot_count = len(df)

            # Initialize predictor
            predictor = DistancePredictor()

            # Train with appropriate method
            can_use_intervals = HAS_MAPIE and shot_count >= 1000

            if can_use_intervals:
                new_metadata = predictor.train_with_intervals(df=df, save=True)
                method = "with intervals"
            else:
                new_metadata = predictor.train(df=df, save=True)
                method = "point estimates"

            elapsed = time.time() - start_time

            # Show success
            new_mae = new_metadata.metrics.get('mae', 0)
            old_mae = current_metadata.metrics.get('mae', 0) if current_metadata else 0
            improvement = ((old_mae - new_mae) / old_mae * 100) if old_mae > 0 else 0

            st.success(
                f"✅ Model retrained successfully ({method})!\n\n"
                f"- **Samples:** {new_metadata.training_samples:,}\n"
                f"- **New MAE:** {new_mae:.2f} yards\n"
                f"- **Previous MAE:** {old_mae:.2f} yards\n"
                f"- **Improvement:** {improvement:+.1f}%\n"
                f"- **Training time:** {elapsed:.1f}s"
            )

            # Trigger rerun to refresh dashboard
            st.rerun()

        except ValueError as e:
            st.error(f"❌ Training failed: {str(e)}")
        except Exception as e:
            st.error(f"❌ Unexpected error during training: {str(e)}")
