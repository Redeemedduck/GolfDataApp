"""
Dispersion chart component for shot pattern visualization.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from analytics.utils import filter_outliers_iqr, check_min_samples


def render_dispersion_chart(df: pd.DataFrame, selected_club: str = None) -> None:
    """
    Render a scatter plot showing shot dispersion patterns.

    Args:
        df: DataFrame containing shot data with carry, side_distance, club
        selected_club: Optional club name to filter to (e.g., "Driver")

    Notes:
        - Applies IQR outlier filtering on carry distance
        - Color codes points by smash factor
        - Shows median crosshair lines
        - Requires 3+ shots for analysis
    """
    st.subheader("Shot Dispersion Pattern")

    if df.empty:
        st.info("No data available for dispersion chart")
        return

    # Filter to selected club if provided
    if selected_club:
        df_filtered = df[df['club'] == selected_club].copy()
        chart_title = f"{selected_club} Dispersion"
    else:
        df_filtered = df.copy()
        chart_title = "All Clubs Dispersion"

    # Check required columns
    required_cols = ['carry', 'side_distance']
    missing_cols = [col for col in required_cols if col not in df_filtered.columns]
    if missing_cols:
        st.warning(f"Missing required columns: {', '.join(missing_cols)}")
        return

    # Drop rows with missing carry or side_distance
    df_filtered = df_filtered.dropna(subset=['carry', 'side_distance'])

    # Check minimum samples
    is_sufficient, msg = check_min_samples(df_filtered, min_n=3, context=selected_club or "shots")
    if not is_sufficient:
        st.info(msg)
        return

    # Track original count before filtering
    original_count = len(df_filtered)

    # Apply IQR outlier filtering on carry distance
    df_filtered = filter_outliers_iqr(df_filtered, 'carry')

    if df_filtered.empty:
        st.info("All shots filtered as outliers")
        return

    outliers_removed = original_count - len(df_filtered)

    # Calculate median values for crosshairs
    median_carry = df_filtered['carry'].median()
    median_side = 0  # Target is straight (zero side distance)

    # Create scatter plot
    fig = go.Figure()

    # Determine color data (prefer smash factor)
    if 'smash' in df_filtered.columns and df_filtered['smash'].notna().any():
        color_data = df_filtered['smash']
        colorbar_title = "Smash Factor"
        colorscale = 'Viridis'
    elif 'ball_speed' in df_filtered.columns and df_filtered['ball_speed'].notna().any():
        color_data = df_filtered['ball_speed']
        colorbar_title = "Ball Speed (mph)"
        colorscale = 'Viridis'
    else:
        color_data = None
        colorbar_title = None
        colorscale = None

    # Build hover template with customdata for extra fields
    import numpy as np

    customdata_cols = []
    hover_parts = ["<b>%{text}</b><br>"]
    hover_parts.append("Carry: %{y:.1f} yds<br>")
    hover_parts.append("Side: %{x:.1f} yds<br>")

    idx = 0
    if 'ball_speed' in df_filtered.columns:
        customdata_cols.append(df_filtered['ball_speed'].values)
        hover_parts.append(f"Ball Speed: %{{customdata[{idx}]:.1f}} mph<br>")
        idx += 1
    if 'launch_angle' in df_filtered.columns:
        customdata_cols.append(df_filtered['launch_angle'].values)
        hover_parts.append(f"Launch: %{{customdata[{idx}]:.1f}}\u00b0<br>")
        idx += 1
    if 'smash' in df_filtered.columns:
        customdata_cols.append(df_filtered['smash'].values)
        hover_parts.append(f"Smash: %{{customdata[{idx}]:.2f}}")
        idx += 1

    hover_template = "".join(hover_parts) + "<extra></extra>"
    customdata = np.column_stack(customdata_cols) if customdata_cols else None

    # Add scatter trace
    fig.add_trace(go.Scatter(
        x=df_filtered['side_distance'],
        y=df_filtered['carry'],
        mode='markers',
        marker=dict(
            size=10,
            color=color_data if color_data is not None else 'royalblue',
            colorscale=colorscale,
            showscale=color_data is not None,
            colorbar=dict(title=colorbar_title) if colorbar_title else None,
            line=dict(width=1, color='white'),
            opacity=0.7
        ),
        text=df_filtered['club'] if 'club' in df_filtered.columns else None,
        customdata=customdata,
        hovertemplate=hover_template,
        name='Shots'
    ))

    # Add median crosshair lines
    # Horizontal line at median carry
    fig.add_hline(
        y=median_carry,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text=f"Median Carry: {median_carry:.1f} yds",
        annotation_position="right"
    )

    # Vertical line at zero (straight)
    fig.add_vline(
        x=median_side,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text="Target Line",
        annotation_position="top"
    )

    # Update layout
    fig.update_layout(
        title=f"{chart_title} ({len(df_filtered)} shots)",
        xaxis_title="Side Distance (yds) — Left (-) / Right (+)",
        yaxis_title="Carry Distance (yds)",
        hovermode='closest',
        height=500,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Display statistics
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Median Carry",
        f"{median_carry:.1f} yds",
        help="Typical carry distance (50th percentile)"
    )

    # IQR spread (Q75-Q25)
    q25_carry = df_filtered['carry'].quantile(0.25)
    q75_carry = df_filtered['carry'].quantile(0.75)
    iqr_spread = q75_carry - q25_carry
    col2.metric(
        "IQR Spread",
        f"{iqr_spread:.1f} yds",
        help="Middle 50% range (Q75 - Q25)"
    )

    # Side spread (standard deviation)
    side_std = df_filtered['side_distance'].std()
    col3.metric(
        "Side Spread",
        f"{side_std:.1f} yds",
        help="Side-to-side consistency (std dev)"
    )

    col4.metric(
        "Shots Shown",
        len(df_filtered),
        help="Number of shots after outlier filtering"
    )

    # Show filtering caption
    if outliers_removed > 0:
        st.caption(f"📊 {len(df_filtered)} shots shown ({outliers_removed} outliers filtered using IQR method)")
    else:
        st.caption(f"📊 {len(df_filtered)} shots shown (no outliers detected)")
