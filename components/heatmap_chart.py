"""
Heatmap chart component for impact location visualization.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils.chart_theme import themed_figure


def render_impact_heatmap(df: pd.DataFrame, use_optix: bool = True) -> None:
    """
    Render a heatmap of impact locations on the club face.

    Args:
        df: DataFrame containing shot data with impact_x, impact_y or optix_x, optix_y
        use_optix: If True, use optix_x/optix_y (more precise), else use impact_x/impact_y
    """
    st.subheader("Impact Location Heatmap")

    if df.empty:
        st.info("No data available for heatmap")
        return

    # Choose which impact data to use
    if use_optix and 'optix_x' in df.columns and 'optix_y' in df.columns:
        x_col, y_col = 'optix_x', 'optix_y'
        caption = "Uneekor Optix Impact Location"
    elif 'impact_x' in df.columns and 'impact_y' in df.columns:
        x_col, y_col = 'impact_x', 'impact_y'
        caption = "Standard Impact Location"
    else:
        st.warning("No impact location data available")
        return

    # Filter out invalid data (zeros and NaN)
    df_filtered = df[(df[x_col] != 0) & (df[y_col] != 0)].copy()
    df_filtered = df_filtered.dropna(subset=[x_col, y_col])

    if df_filtered.empty:
        st.info("No valid impact location data in this dataset")
        return

    # Create heatmap using hexbin style
    fig = themed_figure()

    # Add scatter points with color based on smash factor (if available)
    if 'smash' in df_filtered.columns:
        color_data = df_filtered['smash']
        colorbar_title = "Smash Factor"
    elif 'carry' in df_filtered.columns:
        color_data = df_filtered['carry']
        colorbar_title = "Carry (yds)"
    else:
        color_data = None
        colorbar_title = None

    # Main scatter plot
    fig.add_trace(go.Scatter(
        x=df_filtered[x_col],
        y=df_filtered[y_col],
        mode='markers',
        marker=dict(
            size=12,
            color=color_data if color_data is not None else 'blue',
            colorscale='RdYlGn' if color_data is not None else None,
            showscale=color_data is not None,
            colorbar=dict(title=colorbar_title) if colorbar_title else None,
            line=dict(width=1, color='white'),
            opacity=0.7
        ),
        text=df_filtered['club'] if 'club' in df_filtered.columns else None,
        hovertemplate=(
            "<b>%{text}</b><br>" +
            f"{x_col}: %{{x:.2f}}<br>" +
            f"{y_col}: %{{y:.2f}}<br>" +
            (f"{colorbar_title}: %{{marker.color:.2f}}<extra></extra>" if colorbar_title else "<extra></extra>")
        )
    ))

    # Add center crosshair (sweet spot)
    fig.add_shape(
        type="line",
        x0=0, y0=-0.5, x1=0, y1=0.5,
        line=dict(color="red", width=2, dash="dash"),
        name="Center Line (Vertical)"
    )
    fig.add_shape(
        type="line",
        x0=-0.5, y0=0, x1=0.5, y1=0,
        line=dict(color="red", width=2, dash="dash"),
        name="Center Line (Horizontal)"
    )

    # Add "sweet spot" circle
    fig.add_shape(
        type="circle",
        xref="x", yref="y",
        x0=-0.25, y0=-0.25, x1=0.25, y1=0.25,
        line=dict(color="green", width=2, dash="dot"),
        fillcolor="rgba(0,255,0,0.1)"
    )

    # Calculate center of mass
    center_x = df_filtered[x_col].mean()
    center_y = df_filtered[y_col].mean()

    # Add center of mass marker
    fig.add_trace(go.Scatter(
        x=[center_x],
        y=[center_y],
        mode='markers',
        marker=dict(
            size=15,
            color='yellow',
            symbol='x',
            line=dict(width=3, color='black')
        ),
        name='Average Impact',
        hovertemplate=f"Average Impact<br>X: {center_x:.2f}<br>Y: {center_y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        title=caption,
        xaxis_title="Horizontal (Toe ← → Heel)",
        yaxis_title="Vertical (Low ← → High)",
        xaxis=dict(
            range=[-1, 1],
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='lightgray'
        ),
        yaxis=dict(
            range=[-1, 1],
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='lightgray',
            scaleanchor="x",
            scaleratio=1
        ),
        height=500,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # Statistics
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Horizontal", f"{center_x:.3f}")
    col2.metric("Avg Vertical", f"{center_y:.3f}")

    # Calculate consistency (standard deviation)
    std_x = df_filtered[x_col].std()
    std_y = df_filtered[y_col].std()
    consistency = np.sqrt(std_x**2 + std_y**2)  # Euclidean distance
    col3.metric("Consistency", f"{consistency:.3f}", help="Lower is better (tighter grouping)")

    st.caption(f"📍 Green circle = ideal sweet spot | ❌ Yellow X = your average impact | Total shots: {len(df_filtered)}")
