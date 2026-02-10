"""
Model retraining UI component.
"""
import streamlit as st
from pathlib import Path
import time

# Import ML components with graceful degradation
try:
    from ml import (
        DistancePredictor,
        HAS_MAPIE,
        ML_AVAILABLE,
        ML_MISSING_DEPS
    )
    from ml.train_models import get_model_info, DISTANCE_MODEL_PATH
except ImportError:
    ML_AVAILABLE = False
    ML_MISSING_DEPS = ["ML dependencies (xgboost, scikit-learn, joblib)"]
    DistancePredictor = None
    HAS_MAPIE = False
    get_model_info = None
    DISTANCE_MODEL_PATH = None

# Import golf_db for data access
try:
    import golf_db
except ImportError:
    golf_db = None

# Import prediction interval component
try:
    from .prediction_interval import render_prediction_interval
except ImportError:
    # Fallback if not in package context
    try:
        from components.prediction_interval import render_prediction_interval
    except ImportError:
        render_prediction_interval = None


def render_retraining_ui() -> None:
    """
    Render model retraining UI with current model info and retrain button.

    Shows:
    - Current model version, training date, samples, metrics
    - Retrain button with progress feedback
    - Optional prediction tester with interval visualization
    """
    st.subheader("🔧 Model Management")

    if not ML_AVAILABLE:
        st.warning(
            f"⚠️ ML features not available. Missing: {', '.join(ML_MISSING_DEPS)}\n\n"
            "Install with:\n"
            "```bash\n"
            "pip install xgboost scikit-learn joblib\n"
            "pip install mapie>=1.3.0  # Optional, for confidence intervals\n"
            "```"
        )
        return

    # Check if golf_db is available
    if golf_db is None:
        st.error("Database module not available")
        return

    # Show current model info
    st.markdown("#### Current Model")

    metadata = None
    if get_model_info and DISTANCE_MODEL_PATH and Path(DISTANCE_MODEL_PATH).exists():
        metadata = get_model_info(DISTANCE_MODEL_PATH)

    if metadata:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Version", metadata.version)

        with col2:
            # Format training date
            trained_at = metadata.trained_at
            if 'T' in trained_at:
                trained_at = trained_at.split('T')[0]
            st.metric("Trained", trained_at)

        with col3:
            st.metric("Samples", f"{metadata.training_samples:,}")

        with col4:
            mae = metadata.metrics.get('mae', 0)
            st.metric("MAE", f"{mae:.1f} yd")

        # Show R2 if available
        r2 = metadata.metrics.get('r2')
        if r2 is not None:
            st.caption(f"📈 R² Score: {r2:.3f}")

        # Show if intervals are available
        if HAS_MAPIE and metadata.model_type == 'xgboost_regressor_with_intervals':
            confidence = metadata.metrics.get('confidence_level', 0.95)
            st.caption(f"✅ Prediction intervals enabled ({confidence * 100:.0f}% confidence)")
        else:
            st.caption("ℹ️ Prediction intervals not available (train with MAPIE)")
    else:
        st.info("No model trained yet")

    # Retrain button
    st.divider()

    # Check data availability
    golf_db.init_db()
    df = golf_db.get_all_shots()

    if df.empty:
        st.warning("⚠️ No shot data available. Import data before training.")
        return

    shot_count = len(df)
    st.caption(f"📊 {shot_count:,} shots available for training")

    if shot_count < 50:
        st.error(f"⚠️ Need at least 50 shots to train (have {shot_count})")
        return

    # Determine training method
    can_train_with_intervals = HAS_MAPIE and shot_count >= 1000

    if can_train_with_intervals:
        button_label = "🔄 Retrain Model (with intervals)"
        help_text = f"Train XGBoost + MAPIE for confidence intervals ({shot_count:,} shots)"
    else:
        button_label = "🔄 Retrain Model"
        if shot_count < 1000:
            help_text = f"Train XGBoost model (need 1,000+ shots for intervals, have {shot_count:,})"
        else:
            help_text = f"Train XGBoost model ({shot_count:,} shots)"

    if st.button(button_label, type="primary", use_container_width=True, help=help_text):
        # Training flow
        with st.spinner("Training model... This takes <60 seconds"):
            try:
                start_time = time.time()

                predictor = DistancePredictor()

                # Train with or without intervals
                if can_train_with_intervals:
                    new_metadata = predictor.train_with_intervals(df=df, save=True)
                    training_method = "with intervals"
                else:
                    new_metadata = predictor.train(df=df, save=True)
                    training_method = "point estimates"

                elapsed = time.time() - start_time

                # Show success
                st.success(
                    f"✅ Model trained successfully ({training_method})!\n\n"
                    f"- **Samples:** {new_metadata.training_samples:,}\n"
                    f"- **MAE:** {new_metadata.metrics['mae']:.2f} yards\n"
                    f"- **R² Score:** {new_metadata.metrics.get('r2', 0):.3f}\n"
                    f"- **Training time:** {elapsed:.1f}s"
                )

                # Store in session state for persistence
                st.session_state.last_training = {
                    'metadata': new_metadata,
                    'timestamp': time.time(),
                    'elapsed': elapsed
                }

                # Suggest rerun to refresh model info
                st.info("🔄 Refresh the page to see updated model info")

            except ValueError as e:
                st.error(f"❌ Training failed: {str(e)}")
            except Exception as e:
                st.error(f"❌ Unexpected error during training: {str(e)}")

    # Show last training result if available
    if 'last_training' in st.session_state:
        last_training = st.session_state.last_training
        st.caption(
            f"Last trained: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_training['timestamp']))} "
            f"({last_training['elapsed']:.1f}s)"
        )

    # Prediction tester
    if metadata:
        st.divider()

        with st.expander("🎯 Try a Prediction", expanded=False):
            st.markdown("Test the current model with sample launch conditions.")

            col1, col2, col3 = st.columns(3)

            with col1:
                ball_speed = st.slider(
                    "Ball Speed (mph)",
                    min_value=100,
                    max_value=200,
                    value=150,
                    step=1,
                    help="Typical driver ball speed: 140-180 mph"
                )

            with col2:
                launch_angle = st.slider(
                    "Launch Angle (°)",
                    min_value=5,
                    max_value=25,
                    value=12,
                    step=1,
                    help="Optimal driver launch: 10-15°"
                )

            with col3:
                back_spin = st.slider(
                    "Back Spin (rpm)",
                    min_value=1000,
                    max_value=5000,
                    value=2500,
                    step=100,
                    help="Lower spin = more roll. Driver: 1500-3000 rpm"
                )

            if st.button("🔮 Predict Distance", use_container_width=True):
                try:
                    predictor = DistancePredictor()
                    predictor.load()

                    # Use predict_with_intervals if available
                    if can_train_with_intervals or (metadata and metadata.model_type == 'xgboost_regressor_with_intervals'):
                        prediction = predictor.predict_with_intervals(
                            ball_speed=ball_speed,
                            launch_angle=launch_angle,
                            back_spin=back_spin
                        )
                    else:
                        # Fallback to point estimate
                        result = predictor.predict(
                            ball_speed=ball_speed,
                            launch_angle=launch_angle,
                            back_spin=back_spin
                        )
                        prediction = {
                            'predicted_value': result.predicted_value,
                            'has_intervals': False,
                            'message': 'Model not trained with intervals'
                        }

                    # Render prediction with interval visualization
                    if render_prediction_interval:
                        render_prediction_interval(prediction, club="Driver (estimated)")
                    else:
                        # Fallback rendering
                        st.metric(
                            "Predicted Carry",
                            f"{prediction['predicted_value']:.0f} yards"
                        )
                        if prediction.get('has_intervals'):
                            st.caption(
                                f"{prediction['confidence_level'] * 100:.0f}% CI: "
                                f"{prediction['lower_bound']:.0f}-{prediction['upper_bound']:.0f} yards"
                            )

                except Exception as e:
                    st.error(f"Prediction failed: {str(e)}")
