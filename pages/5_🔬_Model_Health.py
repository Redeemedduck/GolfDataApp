"""
Model Health Page - Monitor ML model performance and trigger retraining.

Provides real-time visibility into model drift detection, prediction error trends,
feature importance, and manual/auto-retraining controls.
"""
import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import golf_db
from components import render_model_health_dashboard

# Page config
st.set_page_config(
    page_title="Model Health - My Golf Lab",
    page_icon="🔬",
    layout="wide"
)

# Initialize database
golf_db.init_db()

# Main title
st.title("🔬 Model Health Monitor")

st.markdown("""
Track your ML model's performance over time. This dashboard shows prediction error trends,
drift detection alerts, and provides controls for model retraining.

**Key Features:**
- 📊 Real-time model performance metrics
- 🔍 Drift detection with adaptive baselines
- 📈 Prediction error trends over sessions
- 🎯 Feature importance visualization
- 🔄 Manual and automatic retraining controls
""")

st.divider()

# Sidebar: Navigation and Quick Status
with st.sidebar:
    st.header("🔗 Navigation")
    st.page_link("pages/2_📊_Dashboard.py", label="📊 Dashboard", icon="📊")
    st.page_link("pages/4_🤖_AI_Coach.py", label="🤖 AI Coach", icon="🤖")

    st.divider()

    st.header("⚡ Quick Status")

    # Try to show quick model status
    try:
        from ml.train_models import get_model_info, DISTANCE_MODEL_PATH

        if Path(DISTANCE_MODEL_PATH).exists():
            metadata = get_model_info(DISTANCE_MODEL_PATH)

            if metadata:
                st.metric("Model Version", metadata.version)

                # Format date
                trained_at = metadata.trained_at
                if 'T' in trained_at:
                    trained_at = trained_at.split('T')[0]
                st.caption(f"Trained: {trained_at}")

                # Show MAE
                mae = metadata.metrics.get('mae', 0)
                st.metric("MAE", f"{mae:.1f} yd")
            else:
                st.info("No model metadata available")
        else:
            st.info("No model trained yet")

    except ImportError:
        st.warning("ML features not available")
    except Exception as e:
        st.error(f"Error loading model info: {e}")

# Main content: Render the full dashboard
render_model_health_dashboard()
