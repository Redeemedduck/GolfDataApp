"""
Journal card component — a single session entry in the practice journal.

Displays date, session type, shot count, clubs used, Big 3 summary,
key metrics, and trend arrows vs rolling averages.
"""
import streamlit as st
import pandas as pd
from typing import Optional

from utils.big3_constants import face_label, path_label, strike_label
from utils.date_helpers import format_session_date


def _trend_arrow(current, baseline):
    """Return trend arrow and delta vs baseline."""
    if current is None or baseline is None or baseline == 0:
        return "", None
    delta = current - baseline
    if abs(delta) < 0.01:
        return "", 0
    return ("+" if delta > 0 else ""), delta



def render_journal_card(
    stats: dict,
    rolling_avg: Optional[dict] = None,
    expanded: bool = False,
) -> None:
    """Render a journal entry card for a single session.

    Args:
        stats: Dict from session_stats table (session_id, shot_count, clubs_used,
               avg_carry, avg_smash, avg_face_angle, std_face_angle, etc.)
        rolling_avg: Optional dict of rolling averages for trend comparison.
        expanded: Whether to show the card expanded by default.
    """
    session_id = stats.get('session_id', 'Unknown')
    date = format_session_date(stats.get('session_date'))
    stype = stats.get('session_type') or 'Practice'
    shots = stats.get('shot_count', 0)
    clubs = stats.get('clubs_used', '')

    # Header line
    title = f"{date} — {stype} ({shots} shots)"

    with st.expander(title, expanded=expanded):
        # Clubs used
        if clubs:
            club_list = clubs.split(',') if isinstance(clubs, str) else clubs
            st.caption(f"Clubs: {', '.join(c.strip() for c in club_list)}")

        # Key metrics row
        col1, col2 = st.columns(2)

        avg_carry = stats.get('avg_carry')
        avg_smash = stats.get('avg_smash')

        with col1:
            if avg_carry is not None:
                prefix, delta = _trend_arrow(avg_carry, (rolling_avg or {}).get('avg_carry'))
                st.metric("Avg Carry", f"{avg_carry:.1f} yds",
                          delta=f"{prefix}{delta:.1f}" if delta is not None else None)
            else:
                st.metric("Avg Carry", "—")

        with col2:
            if avg_smash is not None:
                prefix, delta = _trend_arrow(avg_smash, (rolling_avg or {}).get('avg_smash'))
                st.metric("Smash Factor", f"{avg_smash:.2f}",
                          delta=f"{prefix}{delta:.2f}" if delta is not None else None)
            else:
                st.metric("Smash Factor", "—")

        # Big 3 inline summary
        face_lbl, face_clr = face_label(stats.get('std_face_angle'))
        path_lbl, path_clr = path_label(stats.get('std_club_path'))
        strike_lbl, strike_clr = strike_label(stats.get('avg_strike_distance'))

        st.markdown(
            f"**Big 3:** "
            f"<span style='color:{face_clr}'>Face: {face_lbl}</span> | "
            f"<span style='color:{path_clr}'>Path: {path_lbl}</span> | "
            f"<span style='color:{strike_clr}'>Strike: {strike_lbl}</span>",
            unsafe_allow_html=True,
        )

        notes = stats.get('session_notes')
        if isinstance(notes, str) and notes.strip():
            st.caption(f"📝 {notes[:80]}..." if len(notes) > 80 else notes)
