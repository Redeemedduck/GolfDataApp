"""Practice plan component — weakness badges, drill blocks, time budget."""
import streamlit as st
from utils.chart_theme import (
    COLOR_GOOD, COLOR_FAIR, COLOR_POOR, COLOR_NEUTRAL,
    BG_CARD, TEXT_COLOR, TEXT_MUTED, COLOR_ACCENT,
)


def _severity_color(severity: float) -> str:
    if severity >= 0.7:
        return COLOR_POOR
    if severity >= 0.4:
        return COLOR_FAIR
    return COLOR_NEUTRAL


def render_practice_plan(plan: dict) -> None:
    """Render a practice plan with drill blocks.

    Args:
        plan: Dict from generate_practice_plan().
    """
    if plan.get("empty"):
        st.info("Not enough data to generate a practice plan")
        return

    # Header
    total = plan["total_shots"]
    duration = plan["duration"]

    st.markdown(
        f'<div style="padding:16px; background:{BG_CARD}; border-radius:8px; '
        f'margin-bottom:16px; border-left:4px solid {COLOR_ACCENT};">'
        f'<div style="font-size:18px; font-weight:bold; color:{TEXT_COLOR};">'
        f'Practice Plan — {duration} min</div>'
        f'<div style="color:{TEXT_MUTED};">{total} shots planned</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Weakness badges
    weaknesses = plan.get("weaknesses", [])
    if weaknesses:
        badges_html = ""
        for w in weaknesses:
            badges_html += (
                f'<span style="display:inline-block; padding:4px 10px; margin:2px; '
                f'background:{COLOR_POOR}22; color:{COLOR_POOR}; border-radius:12px; '
                f'font-size:12px; font-weight:600;">'
                f'{w["club"]}: {w["type"].replace("_", " ").title()}</span>'
            )
        st.markdown(
            f'<div style="margin-bottom:16px;"><span style="color:{TEXT_MUTED}; '
            f'font-size:12px;">Targeting: </span>{badges_html}</div>',
            unsafe_allow_html=True,
        )

    # Warmup block
    warmup = plan.get("warmup", {})
    if warmup:
        st.markdown(
            f'<div style="padding:12px 16px; background:{BG_CARD}; border-radius:8px; '
            f'border-left:4px solid {COLOR_GOOD}; margin-bottom:8px;">'
            f'<div style="display:flex; justify-content:space-between;">'
            f'<div>'
            f'<span style="font-weight:600; color:{COLOR_GOOD};">Warmup</span>'
            f'<span style="color:{TEXT_MUTED}; margin-left:8px;">{warmup["club"]}</span>'
            f'</div>'
            f'<span style="color:{TEXT_MUTED};">{warmup["shots"]} shots</span>'
            f'</div>'
            f'<div style="color:{TEXT_MUTED}; font-size:13px; margin-top:4px;">'
            f'{warmup["goal"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Drill blocks
    for i, drill in enumerate(plan.get("drill_blocks", []), 1):
        sev_color = _severity_color(drill.get("severity", 0.5))
        st.markdown(
            f'<div style="padding:12px 16px; background:{BG_CARD}; border-radius:8px; '
            f'border-left:4px solid {sev_color}; margin-bottom:8px;">'
            f'<div style="display:flex; justify-content:space-between;">'
            f'<div>'
            f'<span style="font-weight:600; color:{TEXT_COLOR};">Block {i}: {drill["drill_name"]}</span>'
            f'</div>'
            f'<span style="color:{TEXT_MUTED};">{drill["shots"]} shots</span>'
            f'</div>'
            f'<div style="color:{COLOR_NEUTRAL}; font-size:13px; margin-top:4px;">'
            f'{drill["club"]} — {drill["description"]}</div>'
            f'<div style="color:{TEXT_MUTED}; font-size:12px; margin-top:2px;">'
            f'Why: {drill["metric"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Cooldown / Game simulation
    cooldown = plan.get("cooldown", {})
    if cooldown:
        st.markdown(
            f'<div style="padding:12px 16px; background:{BG_CARD}; border-radius:8px; '
            f'border-left:4px solid {COLOR_ACCENT}; margin-bottom:8px;">'
            f'<div style="display:flex; justify-content:space-between;">'
            f'<div>'
            f'<span style="font-weight:600; color:{COLOR_ACCENT};">Game Simulation</span>'
            f'</div>'
            f'<span style="color:{TEXT_MUTED};">{cooldown["shots"]} shots</span>'
            f'</div>'
            f'<div style="color:{TEXT_MUTED}; font-size:13px; margin-top:4px;">'
            f'{cooldown["goal"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
