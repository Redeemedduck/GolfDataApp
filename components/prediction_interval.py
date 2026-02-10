"""
Prediction interval visualization component.
"""
import streamlit as st
import plotly.graph_objects as go


def render_prediction_interval(prediction: dict, club: str = None) -> None:
    """
    Render a prediction with confidence interval visualization.

    Args:
        prediction: Dict with keys:
            - predicted_value: Point estimate (float)
            - lower_bound: Lower CI bound (float, if has_intervals=True)
            - upper_bound: Upper CI bound (float, if has_intervals=True)
            - confidence_level: Confidence level (float, if has_intervals=True)
            - interval_width: Width of interval (float, if has_intervals=True)
            - has_intervals: Whether intervals are available (bool)
            - message: Explanation if intervals not available (str, optional)
        club: Optional club name for context
    """
    if not prediction:
        st.warning("No prediction data available")
        return

    predicted_value = prediction.get('predicted_value', 0)
    has_intervals = prediction.get('has_intervals', False)

    if not has_intervals:
        # Show point estimate only
        st.metric(
            "Predicted Carry" + (f" ({club})" if club else ""),
            f"{predicted_value:.0f} yards"
        )

        # Show explanation if available
        message = prediction.get('message', 'Confidence intervals not available')
        st.caption(f"ℹ️ {message}")
        return

    # Extract interval data
    lower_bound = prediction.get('lower_bound', predicted_value)
    upper_bound = prediction.get('upper_bound', predicted_value)
    confidence_level = prediction.get('confidence_level', 0.95)
    interval_width = prediction.get('interval_width', upper_bound - lower_bound)

    # Show metric with delta
    delta_text = f"+/- {interval_width / 2:.0f} yards"
    st.metric(
        "Predicted Carry" + (f" ({club})" if club else ""),
        f"{predicted_value:.0f} yards",
        delta=delta_text,
        delta_color="off"  # Don't color the delta
    )

    # Show confidence interval caption
    st.caption(
        f"📊 {confidence_level * 100:.0f}% confidence interval: "
        f"{lower_bound:.0f}-{upper_bound:.0f} yards"
    )

    # Create Plotly visualization
    fig = go.Figure()

    # Add horizontal line for interval range (light blue, thicker)
    fig.add_trace(go.Scatter(
        x=[lower_bound, upper_bound],
        y=[1, 1],
        mode='lines',
        line=dict(color='lightblue', width=8),
        showlegend=False,
        hoverinfo='skip'
    ))

    # Add point estimate marker (blue dot, larger)
    fig.add_trace(go.Scatter(
        x=[predicted_value],
        y=[1],
        mode='markers',
        marker=dict(
            color='blue',
            size=12,
            line=dict(color='white', width=2)
        ),
        showlegend=False,
        hovertemplate=f"Predicted: {predicted_value:.0f} yards<extra></extra>"
    ))

    # Layout configuration
    fig.update_layout(
        xaxis=dict(
            title="Carry Distance (yards)",
            showgrid=True,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            visible=False,
            range=[0.5, 1.5]
        ),
        height=150,
        margin=dict(l=10, r=10, t=10, b=40),
        showlegend=False,
        hovermode='closest'
    )

    st.plotly_chart(fig, use_container_width=True)
