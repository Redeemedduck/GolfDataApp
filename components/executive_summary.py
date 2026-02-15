"""Executive Summary dashboard component.

Renders quality score, Big 3 status, top/bottom clubs, strengths/weaknesses.
"""
import streamlit as st
from utils.chart_theme import (
    COLOR_GOOD, COLOR_FAIR, COLOR_POOR, COLOR_NEUTRAL,
    BG_CARD, TEXT_COLOR, TEXT_MUTED,
)


def _grade_color(grade: str) -> str:
    if grade in ("A", "B"):
        return COLOR_GOOD
    if grade in ("C",):
        return COLOR_FAIR
    return COLOR_POOR


def _rating_color(rating: str) -> str:
    if rating == "Good":
        return COLOR_GOOD
    if rating == "Fair":
        return COLOR_FAIR
    if rating == "Poor":
        return COLOR_POOR
    return TEXT_MUTED


def render_executive_summary(summary: dict) -> None:
    """Render the executive summary section.

    Args:
        summary: Dict from compute_executive_summary().
    """
    if summary.get("empty"):
        st.info("Not enough data for executive summary")
        return

    # ── Quality Score + Grade ──────────────────────────
    score = summary["quality_score"]
    grade = summary["grade"]
    color = _grade_color(grade)

    col_score, col_overview = st.columns([1, 2])

    with col_score:
        st.markdown(
            f'<div style="text-align:center; padding:20px; background:{BG_CARD}; '
            f'border-radius:12px; border-left:4px solid {color};">'
            f'<div style="font-size:48px; font-weight:bold; color:{color};">{grade}</div>'
            f'<div style="font-size:24px; color:{TEXT_COLOR};">{score:.0f}/100</div>'
            f'<div style="color:{TEXT_MUTED}; font-size:13px;">Overall Quality</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_overview:
        overview = summary["overview"]
        o1, o2, o3 = st.columns(3)
        o1.metric("Total Shots", f"{overview['total_shots']:,}")
        o2.metric("Sessions", str(overview["sessions"]))
        o3.metric("Clubs", str(len(overview["clubs"])))

    st.divider()

    # ── Big 3 Status Cards ──────────────────────────
    st.subheader("Big 3 Impact Laws")
    big3 = summary["big3"]

    b1, b2, b3 = st.columns(3)

    metrics = [
        ("Face Control", "face_to_path", "|face-to-path|", "deg"),
        ("Club Path", "club_path", "avg path", "deg"),
        ("Strike Center", "strike_distance", "|strike dist|", "mm"),
    ]

    for col, (label, key, unit_label, unit) in zip([b1, b2, b3], metrics):
        data = big3.get(key, {})
        value = data.get("value")
        rating = data.get("rating", "N/A")
        rc = _rating_color(rating)

        val_str = f"{value:.2f}" if value is not None else "N/A"

        with col:
            st.markdown(
                f'<div style="padding:16px; background:{BG_CARD}; border-radius:8px; '
                f'border-top:3px solid {rc};">'
                f'<div style="color:{TEXT_MUTED}; font-size:12px;">{label}</div>'
                f'<div style="font-size:24px; font-weight:bold; color:{TEXT_COLOR};">{val_str} {unit}</div>'
                f'<div style="color:{rc}; font-weight:600;">{rating}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Top / Bottom Clubs ──────────────────────────
    col_top, col_bottom = st.columns(2)

    with col_top:
        st.markdown(f"**Top Clubs** <span style='color:{COLOR_GOOD}'>&#9650;</span>", unsafe_allow_html=True)
        for club in summary.get("top_clubs", []):
            carry = club.get("carry_avg", 0)
            comp = club.get("composite", 0)
            st.markdown(
                f"<div style='padding:8px; margin:4px 0; background:{BG_CARD}; border-radius:6px; "
                f"border-left:3px solid {COLOR_GOOD};'>"
                f"<strong>{club['club']}</strong> — {carry:.0f}yd avg, score {comp:.0f}/100"
                f"</div>",
                unsafe_allow_html=True,
            )

    with col_bottom:
        st.markdown(f"**Bottom Clubs** <span style='color:{COLOR_POOR}'>&#9660;</span>", unsafe_allow_html=True)
        for club in summary.get("bottom_clubs", []):
            carry = club.get("carry_avg", 0)
            comp = club.get("composite", 0)
            st.markdown(
                f"<div style='padding:8px; margin:4px 0; background:{BG_CARD}; border-radius:6px; "
                f"border-left:3px solid {COLOR_POOR};'>"
                f"<strong>{club['club']}</strong> — {carry:.0f}yd avg, score {comp:.0f}/100"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Strengths / Weaknesses / Actions ──────────────
    col_str, col_weak = st.columns(2)

    with col_str:
        st.markdown(f"**Strengths**")
        for s in summary.get("strengths", []):
            st.markdown(f"<div style='color:{COLOR_GOOD};'>+ {s}</div>", unsafe_allow_html=True)
        if not summary.get("strengths"):
            st.caption("Not enough data yet")

    with col_weak:
        st.markdown(f"**Weaknesses**")
        for w in summary.get("weaknesses", []):
            st.markdown(f"<div style='color:{COLOR_POOR};'>- {w}</div>", unsafe_allow_html=True)
        if not summary.get("weaknesses"):
            st.caption("No major weaknesses detected")

    if summary.get("actions"):
        st.divider()
        st.subheader("Action Items")
        for i, action in enumerate(summary["actions"], 1):
            st.markdown(f"**{i}.** {action}")
