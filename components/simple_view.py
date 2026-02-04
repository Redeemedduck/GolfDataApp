"""
Beginner/Simple view component for casual users.

This component serves the 35% "Casual Fun" persona who want:
- Only 3 key metrics (Carry, Ball Speed, Smash Factor)
- Good/Bad shot indicators
- Progress vs last session
- Session highlights
- No confusing terminology
"""
import streamlit as st
import pandas as pd
from typing import Optional, Dict


def render_simple_dashboard(
    df: pd.DataFrame,
    previous_session_df: Optional[pd.DataFrame] = None
) -> None:
    """
    Render a beginner-friendly dashboard view.

    Args:
        df: Current session DataFrame
        previous_session_df: Previous session DataFrame for comparison
    """
    if df.empty:
        st.info("No shots to display. Hit some balls and import your session!")
        return

    # Simple header
    st.markdown("### Your Session at a Glance")

    # Three key metrics only
    _render_simple_metrics(df, previous_session_df)

    st.divider()

    # Session highlights
    _render_session_highlights(df)

    st.divider()

    # Good/Bad shot breakdown
    _render_shot_quality(df)

    st.divider()

    # Simple tips
    _render_simple_tips(df)


def _render_simple_metrics(
    df: pd.DataFrame,
    previous_df: Optional[pd.DataFrame] = None
) -> None:
    """Render the 3 key metrics with simple explanations."""
    col1, col2, col3 = st.columns(3)

    # Carry Distance
    with col1:
        avg_carry = 0
        prev_carry = None
        delta = None

        if 'carry' in df.columns:
            valid_carry = df[df['carry'] > 0]['carry']
            avg_carry = valid_carry.mean() if len(valid_carry) > 0 else 0

            if previous_df is not None and 'carry' in previous_df.columns:
                prev_valid = previous_df[previous_df['carry'] > 0]['carry']
                if len(prev_valid) > 0:
                    prev_carry = prev_valid.mean()
                    delta = avg_carry - prev_carry

        _render_simple_metric_card(
            emoji="🎯",
            label="How Far",
            value=f"{avg_carry:.0f}",
            unit="yards",
            delta=delta,
            explanation="Average distance your ball flew"
        )

    # Ball Speed
    with col2:
        avg_speed = 0
        prev_speed = None
        delta = None

        if 'ball_speed' in df.columns:
            valid_speed = df[df['ball_speed'] > 0]['ball_speed']
            avg_speed = valid_speed.mean() if len(valid_speed) > 0 else 0

            if previous_df is not None and 'ball_speed' in previous_df.columns:
                prev_valid = previous_df[previous_df['ball_speed'] > 0]['ball_speed']
                if len(prev_valid) > 0:
                    prev_speed = prev_valid.mean()
                    delta = avg_speed - prev_speed

        _render_simple_metric_card(
            emoji="⚡",
            label="Ball Speed",
            value=f"{avg_speed:.0f}",
            unit="mph",
            delta=delta,
            explanation="How fast the ball left your club"
        )

    # Smash Factor (simplified as "Contact Quality")
    with col3:
        avg_smash = 0
        prev_smash = None
        delta = None

        if 'smash' in df.columns:
            valid_smash = df[(df['smash'] > 0) & (df['smash'] < 2)]['smash']
            avg_smash = valid_smash.mean() if len(valid_smash) > 0 else 0

            if previous_df is not None and 'smash' in previous_df.columns:
                prev_valid = previous_df[(previous_df['smash'] > 0) & (previous_df['smash'] < 2)]['smash']
                if len(prev_valid) > 0:
                    prev_smash = prev_valid.mean()
                    delta = (avg_smash - prev_smash) * 100  # Convert to percentage points

        # Convert smash to a simple quality rating
        quality = _smash_to_quality(avg_smash)

        _render_simple_metric_card(
            emoji="✨",
            label="Contact Quality",
            value=quality,
            unit="",
            delta=delta,
            explanation="How solid you hit the ball (1.50 = perfect)",
            raw_value=f"({avg_smash:.2f})" if avg_smash > 0 else ""
        )


def _render_simple_metric_card(
    emoji: str,
    label: str,
    value: str,
    unit: str,
    delta: Optional[float] = None,
    explanation: str = "",
    raw_value: str = ""
) -> None:
    """Render a simple metric card with emoji and explanation."""
    # Delta indicator
    delta_html = ""
    if delta is not None:
        if delta > 0:
            delta_html = f'<div style="color: #4CAF50; font-weight: bold;">↑ Better than last time!</div>'
        elif delta < 0:
            delta_html = f'<div style="color: #F44336;">↓ Keep working at it!</div>'
        else:
            delta_html = f'<div style="color: #9E9E9E;">→ Same as before</div>'

    st.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 20px;
            background: #F5F5F5;
            border-radius: 12px;
        ">
            <div style="font-size: 36px;">{emoji}</div>
            <div style="font-size: 14px; color: #757575; margin-top: 8px;">{label}</div>
            <div style="font-size: 32px; font-weight: bold; margin-top: 8px;">{value} {unit}</div>
            {f'<div style="font-size: 12px; color: #999;">{raw_value}</div>' if raw_value else ''}
            {delta_html}
            <div style="font-size: 12px; color: #999; margin-top: 8px;">{explanation}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def _smash_to_quality(smash: float) -> str:
    """Convert smash factor to a simple quality rating."""
    if smash >= 1.48:
        return "Excellent"
    elif smash >= 1.45:
        return "Great"
    elif smash >= 1.40:
        return "Good"
    elif smash >= 1.35:
        return "OK"
    elif smash > 0:
        return "Needs Work"
    else:
        return "N/A"


def _render_session_highlights(df: pd.DataFrame) -> None:
    """Render session highlights in simple terms."""
    st.markdown("### Highlights")

    highlights = []

    # Best carry
    if 'carry' in df.columns:
        best_carry = df['carry'].max()
        if best_carry > 0:
            highlights.append(f"🏆 **Best Shot**: {best_carry:.0f} yards")

    # Most consistent club
    if 'club' in df.columns and 'carry' in df.columns:
        club_stats = df.groupby('club')['carry'].agg(['std', 'count'])
        club_stats = club_stats[club_stats['count'] >= 3]  # At least 3 shots
        if len(club_stats) > 0:
            most_consistent = club_stats['std'].idxmin()
            highlights.append(f"🎯 **Most Consistent**: {most_consistent}")

    # Total shots
    shot_count = len(df)
    highlights.append(f"⛳ **Total Shots**: {shot_count}")

    # Clubs used
    if 'club' in df.columns:
        club_count = df['club'].nunique()
        highlights.append(f"🏌️ **Clubs Used**: {club_count}")

    for highlight in highlights:
        st.markdown(highlight)


def _render_shot_quality(df: pd.DataFrame) -> None:
    """Render a simple good/bad shot breakdown."""
    st.markdown("### Shot Quality")

    if 'smash' not in df.columns:
        st.info("No smash factor data available")
        return

    valid_shots = df[(df['smash'] > 0) & (df['smash'] < 2)]

    if len(valid_shots) == 0:
        st.info("No valid shots to analyze")
        return

    # Categorize shots
    excellent = len(valid_shots[valid_shots['smash'] >= 1.48])
    good = len(valid_shots[(valid_shots['smash'] >= 1.40) & (valid_shots['smash'] < 1.48)])
    needs_work = len(valid_shots[valid_shots['smash'] < 1.40])

    total = len(valid_shots)

    col1, col2, col3 = st.columns(3)

    with col1:
        pct = (excellent / total * 100) if total > 0 else 0
        st.markdown(
            f"""
            <div style="text-align: center; padding: 16px; background: #E8F5E9; border-radius: 8px;">
                <div style="font-size: 24px;">✅</div>
                <div style="font-size: 24px; font-weight: bold; color: #4CAF50;">{excellent}</div>
                <div style="color: #666;">Great Shots</div>
                <div style="font-size: 12px; color: #999;">{pct:.0f}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        pct = (good / total * 100) if total > 0 else 0
        st.markdown(
            f"""
            <div style="text-align: center; padding: 16px; background: #FFF3E0; border-radius: 8px;">
                <div style="font-size: 24px;">👍</div>
                <div style="font-size: 24px; font-weight: bold; color: #FF9800;">{good}</div>
                <div style="color: #666;">Good Shots</div>
                <div style="font-size: 12px; color: #999;">{pct:.0f}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        pct = (needs_work / total * 100) if total > 0 else 0
        st.markdown(
            f"""
            <div style="text-align: center; padding: 16px; background: #FFEBEE; border-radius: 8px;">
                <div style="font-size: 24px;">💪</div>
                <div style="font-size: 24px; font-weight: bold; color: #F44336;">{needs_work}</div>
                <div style="color: #666;">Keep Practicing</div>
                <div style="font-size: 12px; color: #999;">{pct:.0f}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )


def _render_simple_tips(df: pd.DataFrame) -> None:
    """Render personalized tips based on the data."""
    st.markdown("### Quick Tips")

    tips = []

    # Check smash factor
    if 'smash' in df.columns:
        valid_smash = df[(df['smash'] > 0) & (df['smash'] < 2)]['smash']
        if len(valid_smash) > 0:
            avg_smash = valid_smash.mean()
            if avg_smash < 1.40:
                tips.append("💡 Focus on hitting the center of the club face to improve contact quality")
            elif avg_smash >= 1.48:
                tips.append("🌟 Great contact! Your ball striking is solid")

    # Check consistency
    if 'carry' in df.columns:
        carry_std = df[df['carry'] > 0]['carry'].std()
        if carry_std > 20:
            tips.append("💡 Work on consistency - try the same swing with each club")

    # Default tip
    if not tips:
        tips.append("💡 Keep practicing! Consistency comes with repetition")

    for tip in tips:
        st.info(tip)


def render_mode_toggle() -> str:
    """
    Render a toggle between Simple and Advanced mode.

    Returns:
        Current mode ("simple" or "advanced")
    """
    from utils.session_state import get_ui_mode, set_ui_mode

    current_mode = get_ui_mode()

    col1, col2 = st.columns(2)

    with col1:
        simple_selected = current_mode == "simple"
        if st.button(
            "🎯 Simple View",
            use_container_width=True,
            type="primary" if simple_selected else "secondary",
            help="Shows only the essential metrics in an easy-to-understand format"
        ):
            set_ui_mode("simple")
            st.rerun()

    with col2:
        advanced_selected = current_mode == "advanced"
        if st.button(
            "📊 Full Dashboard",
            use_container_width=True,
            type="primary" if advanced_selected else "secondary",
            help="Shows all metrics and detailed analytics"
        ):
            set_ui_mode("advanced")
            st.rerun()

    return current_mode
