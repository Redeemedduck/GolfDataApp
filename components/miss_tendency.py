"""
Miss tendency analysis component using D-plane theory.

Analyzes shot shape patterns (straight/draw/fade/hook/slice) per club
using face angle, club path, and side spin data.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from analytics.utils import check_min_samples


def _classify_shot_shape(face_angle: float, club_path: float, side_spin: int) -> str:
    """
    Classify shot shape using D-plane theory.

    Args:
        face_angle: Club face angle at impact (degrees, positive = open)
        club_path: Club path angle (degrees, positive = out-to-in)
        side_spin: Side spin (rpm, positive = clockwise/fade)

    Returns:
        Shot shape: 'Straight', 'Draw', 'Fade', 'Hook', or 'Slice'

    Notes:
        - face_to_path difference is the primary determinant of curve
        - Side spin validates the classification
        - Thresholds based on D-plane theory research (02-RESEARCH.md)
    """
    # Calculate face-to-path difference (primary curve determinant)
    face_to_path = face_angle - club_path

    # Straight shot: minimal face-to-path difference and side spin
    if abs(face_to_path) < 2.0 and abs(side_spin) < 300:
        return 'Straight'

    # Hooks and draws (right-to-left for right-handed golfer)
    if face_to_path < -6.0:
        return 'Hook'
    elif face_to_path < -2.0:
        return 'Draw'

    # Slices and fades (left-to-right for right-handed golfer)
    if face_to_path > 6.0:
        return 'Slice'
    elif face_to_path > 2.0:
        return 'Fade'

    # Default to straight if between -2 and +2
    return 'Straight'


def render_miss_tendency(df: pd.DataFrame, selected_club: str = None) -> None:
    """
    Render miss tendency analysis showing shot shape breakdown per club.

    Args:
        df: DataFrame containing shot data
        selected_club: Optional club name to filter by

    Required columns: face_angle, club_path, side_spin
    Optional columns: club (for filtering)

    Displays:
        - Horizontal bar chart with percentage breakdown by shot shape
        - Dominant tendency with coaching tip
        - Educational explanation of D-plane theory
    """
    st.subheader("Miss Tendency Analysis")

    # Empty check
    if df.empty:
        st.info("No data available for miss tendency analysis")
        return

    # Check required columns
    required_cols = ['face_angle', 'club_path', 'side_spin']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.warning(f"Missing required columns for miss tendency analysis: {', '.join(missing_cols)}")
        return

    # Filter by club if specified
    df_filtered = df.copy()
    if selected_club and 'club' in df.columns:
        df_filtered = df_filtered[df_filtered['club'] == selected_club]
        if df_filtered.empty:
            st.info(f"No data available for {selected_club}")
            return

    # Check minimum samples
    context_msg = f"{selected_club}" if selected_club else "this dataset"
    has_min_samples, message = check_min_samples(df_filtered, min_n=5, context=context_msg)
    if not has_min_samples:
        st.warning(message)
        return

    # Drop rows with missing required values
    df_filtered = df_filtered.dropna(subset=required_cols)

    if df_filtered.empty:
        st.info("No shots with complete data for miss tendency analysis")
        return

    # Classify each shot
    df_filtered['shot_shape'] = df_filtered.apply(
        lambda row: _classify_shot_shape(row['face_angle'], row['club_path'], row['side_spin']),
        axis=1
    )

    # Count by shape and calculate percentages
    shape_counts = df_filtered['shot_shape'].value_counts()
    total_shots = len(df_filtered)
    shape_percentages = (shape_counts / total_shots * 100).round(1)

    # Define color map and order
    shape_order = ['Straight', 'Draw', 'Fade', 'Hook', 'Slice']
    color_map = {
        'Straight': '#4CAF50',  # green
        'Draw': '#2196F3',      # blue
        'Fade': '#FF9800',      # orange
        'Hook': '#F44336',      # red
        'Slice': '#9C27B0'      # purple
    }

    # Create ordered lists for plotting (only shapes that exist)
    shapes_present = [shape for shape in shape_order if shape in shape_percentages.index]
    percentages_ordered = [shape_percentages[shape] for shape in shapes_present]
    colors_ordered = [color_map[shape] for shape in shapes_present]

    # Create horizontal bar chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=shapes_present,
        x=percentages_ordered,
        orientation='h',
        marker=dict(color=colors_ordered),
        text=[f"{pct:.1f}%" for pct in percentages_ordered],
        textposition='auto',
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "Percentage: %{x:.1f}%<br>" +
            f"Count: %{{customdata}}<extra></extra>"
        ),
        customdata=[shape_counts[shape] for shape in shapes_present]
    ))

    # Update layout
    title_text = "Shot Shape Distribution"
    if selected_club:
        title_text += f" - {selected_club}"
    title_text += f" ({total_shots} shots)"

    fig.update_layout(
        title=title_text,
        xaxis_title="Percentage",
        yaxis_title="Shot Shape",
        height=400,
        showlegend=False,
        xaxis=dict(range=[0, 100])
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show dominant tendency with coaching tip
    dominant_shape = shape_percentages.idxmax()
    dominant_pct = shape_percentages.max()

    # Calculate average face-to-path for context
    avg_face_to_path = (df_filtered['face_angle'] - df_filtered['club_path']).mean()

    # Generate coaching tip based on dominant tendency
    if dominant_shape == 'Straight':
        st.success(f"✅ **Dominant tendency:** {dominant_shape} ({dominant_pct:.1f}%)")
        st.info("Great ball-striking! Your shots are predominantly straight.")
    elif dominant_shape == 'Draw':
        st.info(f"📊 **Dominant tendency:** {dominant_shape} ({dominant_pct:.1f}%)")
        st.write(f"Your dominant miss is a draw. Average face-to-path: {avg_face_to_path:.1f} degrees.")
        st.caption("💡 A controlled draw is often preferred by better players.")
    elif dominant_shape == 'Fade':
        st.info(f"📊 **Dominant tendency:** {dominant_shape} ({dominant_pct:.1f}%)")
        st.write(f"Your dominant miss is a fade. Average face-to-path: {avg_face_to_path:.1f} degrees.")
        st.caption("💡 A controlled fade is a reliable shot shape.")
    elif dominant_shape == 'Hook':
        st.warning(f"⚠️ **Dominant tendency:** {dominant_shape} ({dominant_pct:.1f}%)")
        st.write(f"You're hooking frequently. Average face-to-path: {avg_face_to_path:.1f} degrees.")
        st.caption("💡 **Fix:** Check grip pressure and face control at impact. The club face is likely closing too much relative to path.")
    else:  # Slice
        st.warning(f"⚠️ **Dominant tendency:** {dominant_shape} ({dominant_pct:.1f}%)")
        st.write(f"You're slicing frequently. Average face-to-path: {avg_face_to_path:.1f} degrees.")
        st.caption("💡 **Fix:** Work on an in-to-out swing path and closing the face. The face is too open relative to path.")

    # Educational explanation in expander
    with st.expander("📚 Understanding miss tendencies"):
        st.write("""
        **D-Plane Theory Basics:**

        - **Face Angle** determines the initial direction of the ball
        - **Face-to-Path Difference** determines the amount of curve
        - **Side Spin** confirms the shot shape

        **Shot Shape Guide:**
        - **Straight:** Face-to-path < 2° and minimal side spin
        - **Draw:** Face-to-path between -2° and -6° (right-to-left curve)
        - **Hook:** Face-to-path < -6° (severe right-to-left)
        - **Fade:** Face-to-path between +2° and +6° (left-to-right curve)
        - **Slice:** Face-to-path > +6° (severe left-to-right)

        A consistent miss pattern is often better than random dispersion — it means
        your swing is repeatable and can be adjusted with setup or aim.
        """)
