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
        col1, col2, col3 = st.columns(3)

        avg_carry = stats.get('avg_carry')
        avg_smash = stats.get('avg_smash')
        best_carry = stats.get('best_carry')

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

        with col3:
            if best_carry is not None:
                st.metric("Best Carry", f"{best_carry:.1f} yds")
            else:
                st.metric("Best Carry", "—")

        # Big 3 summary
        st.markdown("**Big 3 Impact Laws**")
        b1, b2, b3 = st.columns(3)

        face_lbl, face_clr = face_label(stats.get('std_face_angle'))
        path_lbl, path_clr = path_label(stats.get('std_club_path'))
        strike_lbl, strike_clr = strike_label(stats.get('avg_strike_distance'))

        with b1:
            avg_face = stats.get('avg_face_angle')
            face_val = f"{avg_face:+.1f}" if avg_face is not None else "—"
            st.markdown(
                f"<div style='text-align:center'>"
                f"<span style='font-size:0.8em;color:#888'>Face Angle</span><br>"
                f"<span style='font-size:1.3em;font-weight:bold'>{face_val}</span><br>"
                f"<span style='color:{face_clr};font-size:0.9em'>{face_lbl}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        with b2:
            avg_path = stats.get('avg_club_path')
            path_val = f"{avg_path:+.1f}" if avg_path is not None else "—"
            st.markdown(
                f"<div style='text-align:center'>"
                f"<span style='font-size:0.8em;color:#888'>Club Path</span><br>"
                f"<span style='font-size:1.3em;font-weight:bold'>{path_val}</span><br>"
                f"<span style='color:{path_clr};font-size:0.9em'>{path_lbl}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        with b3:
            avg_strike = stats.get('avg_strike_distance')
            strike_val = f"{avg_strike:.2f}\"" if avg_strike is not None else "—"
            st.markdown(
                f"<div style='text-align:center'>"
                f"<span style='font-size:0.8em;color:#888'>Strike Quality</span><br>"
                f"<span style='font-size:1.3em;font-weight:bold'>{strike_val}</span><br>"
                f"<span style='color:{strike_clr};font-size:0.9em'>{strike_lbl}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
