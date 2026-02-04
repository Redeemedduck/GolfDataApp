"""
Session Compare Page - Compare 2-3 sessions side-by-side

This is the #1 user-requested feature. Allows users to:
- Select 2-3 sessions to compare
- View side-by-side KPI cards with deltas
- See overlaid trend lines
- Compare club-by-club performance
"""
import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import golf_db
from services.data_access import get_unique_sessions, get_session_data
from utils.session_state import get_read_mode
from utils.responsive import add_responsive_css
from components import (
    render_shared_sidebar,
    render_comparison_empty_state,
)
from components.session_comparison import (
    render_session_comparison,
    render_comparison_selector,
)

st.set_page_config(layout="wide", page_title="Session Compare - My Golf Lab")

# Add responsive CSS
add_responsive_css()

# Initialize DB
golf_db.init_db()

# Get read mode
read_mode = get_read_mode()

# Shared sidebar
render_shared_sidebar(
    show_navigation=True,
    show_data_source=True,
    show_sync_status=True,
    current_page="compare"
)

# Session selector in sidebar
with st.sidebar:
    st.divider()
    st.header("Select Sessions")

    sessions = get_unique_sessions(read_mode=read_mode)
    selected_sessions = render_comparison_selector(sessions, max_sessions=3)

    if len(selected_sessions) >= 2:
        st.success(f"Comparing {len(selected_sessions)} sessions")
    elif len(selected_sessions) == 1:
        st.info("Select 1 more session to compare")
    else:
        st.info("Select 2-3 sessions to compare")

    st.divider()

    # Metric selector
    st.subheader("Metrics to Compare")

    available_metrics = {
        'carry': 'Carry Distance',
        'ball_speed': 'Ball Speed',
        'smash': 'Smash Factor',
        'launch_angle': 'Launch Angle',
        'back_spin': 'Back Spin',
        'club_speed': 'Club Speed',
        'total': 'Total Distance',
    }

    selected_metrics = st.multiselect(
        "Choose metrics",
        options=list(available_metrics.keys()),
        default=['carry', 'ball_speed', 'smash'],
        format_func=lambda x: available_metrics[x],
        key="comparison_metrics"
    )

# Main content
st.title("Session Comparison")
st.markdown("""
Compare your performance across multiple practice sessions to track improvement
and identify areas that need work.
""")

st.divider()

# Check if we have enough sessions selected
if len(selected_sessions) < 2:
    render_comparison_empty_state()
else:
    # Render the comparison
    render_session_comparison(
        session_ids=selected_sessions,
        metrics=selected_metrics if selected_metrics else None,
        read_mode=read_mode
    )

    st.divider()

    # Additional analysis section
    with st.expander("Detailed Statistics"):
        # Show per-session breakdown
        for session_id in selected_sessions:
            st.subheader(f"Session: {session_id}")
            df = get_session_data(session_id, read_mode=read_mode)

            if not df.empty:
                cols = st.columns(4)

                # Basic stats
                with cols[0]:
                    st.metric("Total Shots", len(df))

                with cols[1]:
                    if 'club' in df.columns:
                        st.metric("Clubs Used", df['club'].nunique())

                with cols[2]:
                    if 'carry' in df.columns:
                        valid_carry = df[df['carry'] > 0]['carry']
                        if len(valid_carry) > 0:
                            st.metric(
                                "Best Carry",
                                f"{valid_carry.max():.1f} yds"
                            )

                with cols[3]:
                    if 'smash' in df.columns:
                        valid_smash = df[(df['smash'] > 0) & (df['smash'] < 2)]['smash']
                        if len(valid_smash) > 0:
                            st.metric(
                                "Best Smash",
                                f"{valid_smash.max():.2f}"
                            )

                st.divider()

# Help section
with st.expander("How to Use Session Comparison"):
    st.markdown("""
    ### Getting Started

    1. **Select Sessions**: Use the sidebar to choose 2-3 sessions to compare
    2. **Choose Metrics**: Select which metrics you want to compare
    3. **Review Results**: See side-by-side comparisons with delta indicators

    ### Understanding the Comparison

    **Color Indicators:**
    - **Green ↑**: Improvement from baseline
    - **Red ↓**: Decline from baseline
    - **Gray →**: No significant change

    **Baseline Session:**
    The first session you select becomes the "baseline" for comparison.
    All deltas are calculated relative to this session.

    ### Tips

    - Compare sessions with similar clubs for best results
    - Look for consistent trends across multiple metrics
    - Use this to track progress over time
    - Select sessions from different time periods to see improvement
    """)

# Footer
st.divider()
st.caption("Session Compare - Track your progress over time")
