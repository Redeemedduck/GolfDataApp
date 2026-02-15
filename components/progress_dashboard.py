"""Progress dashboard component — sparklines and trend cards."""
import streamlit as st
import plotly.graph_objects as go
from utils.chart_theme import (
    themed_figure, COLOR_GOOD, COLOR_FAIR, COLOR_POOR, COLOR_NEUTRAL,
    BG_CARD, BG_PRIMARY, TEXT_COLOR, TEXT_MUTED,
)


def _direction_color(direction: str) -> str:
    if direction == "improving":
        return COLOR_GOOD
    if direction == "declining":
        return COLOR_POOR
    return COLOR_FAIR


def _direction_arrow(direction: str) -> str:
    if direction == "improving":
        return "&#9650;"
    if direction == "declining":
        return "&#9660;"
    return "&#9654;"


def render_progress_dashboard(trends: dict) -> None:
    """Render progress sparklines and highlight cards.

    Args:
        trends: Dict from compute_progress_trends().
    """
    clubs = trends.get("clubs", [])
    if not clubs:
        st.info("Not enough data for progress tracking (need 5+ shots, 2+ sessions per club)")
        return

    # Highlight cards
    most_improved = trends.get("most_improved")
    needs_attention = trends.get("needs_attention")

    if most_improved or needs_attention:
        h1, h2 = st.columns(2)
        if most_improved:
            improved_data = next((c for c in clubs if c["club"] == most_improved), None)
            delta = improved_data["delta"] if improved_data else 0
            with h1:
                st.markdown(
                    f'<div style="padding:16px; background:{BG_CARD}; border-radius:8px; '
                    f'border-left:4px solid {COLOR_GOOD};">'
                    f'<div style="color:{TEXT_MUTED}; font-size:12px;">Most Improved</div>'
                    f'<div style="font-size:20px; font-weight:bold; color:{COLOR_GOOD};">'
                    f'{most_improved}</div>'
                    f'<div style="color:{COLOR_GOOD};">+{delta:.1f} yd avg carry</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        if needs_attention:
            attention_data = next((c for c in clubs if c["club"] == needs_attention), None)
            delta = attention_data["delta"] if attention_data else 0
            with h2:
                st.markdown(
                    f'<div style="padding:16px; background:{BG_CARD}; border-radius:8px; '
                    f'border-left:4px solid {COLOR_POOR};">'
                    f'<div style="color:{TEXT_MUTED}; font-size:12px;">Needs Attention</div>'
                    f'<div style="font-size:20px; font-weight:bold; color:{COLOR_POOR};">'
                    f'{needs_attention}</div>'
                    f'<div style="color:{COLOR_POOR};">{delta:+.1f} yd avg carry</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.divider()

    # Per-club sparklines
    st.subheader("Per-Club Trends")

    # Render in 2-column grid
    for i in range(0, len(clubs), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(clubs):
                break

            club_data = clubs[idx]
            club = club_data["club"]
            sparkline = club_data["sparkline_data"]
            direction = club_data["direction"]
            delta = club_data["delta"]
            recent = club_data["most_recent_avg"]
            dc = _direction_color(direction)
            arrow = _direction_arrow(direction)

            with col:
                # Mini sparkline chart
                fig = themed_figure(height=80, margin=dict(l=0, r=0, t=0, b=0))
                fig.add_trace(go.Scatter(
                    y=sparkline,
                    mode="lines",
                    line=dict(color=dc, width=2),
                    fill="tozeroy",
                    fillcolor=dc.replace(")", ", 0.1)").replace("rgb", "rgba") if "rgb" in dc else f"rgba{tuple(int(dc.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.1,)}",
                    hoverinfo="skip",
                ))
                fig.update_xaxes(visible=False)
                fig.update_yaxes(visible=False)

                st.markdown(
                    f'<div style="padding:8px 12px; background:{BG_CARD}; border-radius:8px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<span style="font-weight:600; color:{TEXT_COLOR};">{club}</span>'
                    f'<span style="color:{dc};">{arrow} {delta:+.1f}yd</span>'
                    f'</div>'
                    f'<div style="color:{TEXT_MUTED}; font-size:12px;">'
                    f'{club_data["sessions"]} sessions • {recent:.0f}yd latest'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(fig, use_container_width=True, key=f"sparkline_{club}_{idx}")
