"""
Big 3 Detail View — full tabbed analysis of all three Impact Laws.

Tab 1: Face Angle (tendency + consistency)
Tab 2: Club Path (tendency + consistency)
Tab 3: Face-to-Path (D-plane + shot shape distribution)
Tab 4: Strike Location (enhanced heatmap + consistency score)
"""
import streamlit as st
import pandas as pd

from components.big3_summary import render_big3_summary
from components.face_path_diagram import render_face_path_diagram
from components.direction_tendency import (
    render_face_tendency,
    render_path_tendency,
    render_shot_shape_distribution,
)
from components.heatmap_chart import render_impact_heatmap


def render_big3_detail_view(df: pd.DataFrame) -> None:
    """Render the full Big 3 tabbed detail view.

    Args:
        df: DataFrame with shot data including Big 3 columns.
    """
    if df.empty:
        st.info("No data available for Big 3 analysis")
        return

    # Summary panel at top
    render_big3_summary(df)

    st.divider()

    # Tabbed detail views
    tab1, tab2, tab3, tab4 = st.tabs([
        "Face Angle",
        "Club Path",
        "D-Plane / Shot Shape",
        "Strike Location",
    ])

    with tab1:
        st.markdown("#### Face Angle Analysis")
        st.caption(
            "Face angle at impact determines ~75% of the ball's initial start direction. "
            "A square face (0 degrees) starts the ball at the target."
        )
        render_face_tendency(df)

        if 'face_angle' in df.columns:
            face = df['face_angle'].dropna()
            if len(face) > 0:
                col1, col2, col3 = st.columns(3)
                col1.metric("Average", f"{face.mean():+.1f}")
                col2.metric("Std Dev", f"{face.std():.1f}" if len(face) > 1 else "—")
                col3.metric("Range", f"{face.min():+.1f} to {face.max():+.1f}")

    with tab2:
        st.markdown("#### Club Path Analysis")
        st.caption(
            "Club path determines ~25% of initial direction and is the primary factor "
            "in ball curvature. Positive = in-to-out (draw tendency), "
            "negative = out-to-in (fade tendency)."
        )
        render_path_tendency(df)

        if 'club_path' in df.columns:
            path = df['club_path'].dropna()
            if len(path) > 0:
                col1, col2, col3 = st.columns(3)
                col1.metric("Average", f"{path.mean():+.1f}")
                col2.metric("Std Dev", f"{path.std():.1f}" if len(path) > 1 else "—")
                col3.metric("Range", f"{path.min():+.1f} to {path.max():+.1f}")

    with tab3:
        st.markdown("#### Face-to-Path (D-Plane)")
        st.caption(
            "The difference between face angle and club path determines ball curvature. "
            "Face-to-Path > 0 = draw spin, < 0 = fade spin. "
            "Points on the diagonal = straight shots."
        )
        render_face_path_diagram(df)
        st.divider()
        render_shot_shape_distribution(df)

    with tab4:
        st.markdown("#### Strike Location")
        st.caption(
            "Where the ball contacts the club face is the biggest factor in distance "
            "consistency. Center strikes maximize energy transfer (smash factor)."
        )
        render_impact_heatmap(df)
