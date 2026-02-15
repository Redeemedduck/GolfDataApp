"""Session grades component — A-F grade cards with trajectory indicator."""
import streamlit as st
from utils.chart_theme import (
    COLOR_GOOD, COLOR_FAIR, COLOR_POOR, COLOR_NEUTRAL,
    BG_CARD, TEXT_COLOR, TEXT_MUTED,
)


def _grade_color(grade: str) -> str:
    if grade in ("A", "B"):
        return COLOR_GOOD
    if grade == "C":
        return COLOR_FAIR
    return COLOR_POOR


def _trajectory_display(trajectory: str) -> tuple:
    """Return (label, color, arrow) for trajectory."""
    if trajectory == "IMPROVING":
        return "Improving", COLOR_GOOD, "&#9650;"
    if trajectory == "DECLINING":
        return "Declining", COLOR_POOR, "&#9660;"
    if trajectory == "FLAT":
        return "Stable", COLOR_FAIR, "&#9654;"
    return "Insufficient Data", TEXT_MUTED, "&#8212;"


def render_session_grades(grades: list) -> None:
    """Render session grade cards.

    Args:
        grades: List from compute_session_grades().
    """
    if not grades:
        st.info("Not enough sessions for grading (need 3+ shots per session)")
        return

    # Trajectory indicator
    trajectory = grades[0].get("trajectory", "INSUFFICIENT DATA")
    traj_label, traj_color, traj_arrow = _trajectory_display(trajectory)

    st.markdown(
        f'<div style="padding:12px; background:{BG_CARD}; border-radius:8px; '
        f'display:flex; align-items:center; gap:12px; margin-bottom:16px;">'
        f'<span style="font-size:20px; color:{traj_color};">{traj_arrow}</span>'
        f'<span style="font-size:16px; font-weight:600; color:{traj_color};">{traj_label}</span>'
        f'<span style="color:{TEXT_MUTED}; font-size:13px;">— based on last {min(5, len(grades))} sessions</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Session cards (show last 10)
    for session in grades[:10]:
        grade = session["grade"]
        score = session["total_score"]
        color = _grade_color(grade)
        date_str = session.get("session_date", "Unknown")
        shots = session["shot_count"]
        scores = session.get("scores", {})

        # Component bars
        bars_html = ""
        for comp_name, comp_score in scores.items():
            bar_width = max(5, min(100, comp_score))
            bar_color = COLOR_GOOD if comp_score >= 70 else (COLOR_FAIR if comp_score >= 50 else COLOR_POOR)
            bars_html += (
                f'<div style="display:flex; align-items:center; gap:8px; margin:2px 0;">'
                f'<span style="width:50px; font-size:11px; color:{TEXT_MUTED}; text-align:right;">'
                f'{comp_name.title()}</span>'
                f'<div style="flex:1; height:6px; background:#2a2a4a; border-radius:3px;">'
                f'<div style="width:{bar_width}%; height:100%; background:{bar_color}; '
                f'border-radius:3px;"></div></div>'
                f'<span style="width:30px; font-size:11px; color:{TEXT_MUTED};">{comp_score:.0f}</span>'
                f'</div>'
            )

        st.markdown(
            f'<div style="padding:12px 16px; background:{BG_CARD}; border-radius:8px; '
            f'border-left:4px solid {color}; margin-bottom:8px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<div>'
            f'<span style="font-weight:600; color:{TEXT_COLOR};">{date_str}</span>'
            f'<span style="color:{TEXT_MUTED}; font-size:13px; margin-left:12px;">{shots} shots</span>'
            f'</div>'
            f'<div style="display:flex; align-items:center; gap:8px;">'
            f'<span style="font-size:13px; color:{TEXT_MUTED};">{score:.0f}/100</span>'
            f'<span style="font-size:24px; font-weight:bold; color:{color};">{grade}</span>'
            f'</div>'
            f'</div>'
            f'<div style="margin-top:8px;">{bars_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
