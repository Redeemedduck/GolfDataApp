"""
Auto-generated insights component.

Provides automatic analysis of session data to surface key insights
without the user needing to ask questions.

This is a pure function (no Streamlit calls in the core logic)
to enable easy testing and reuse.
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional


def generate_session_insights(
    df: pd.DataFrame,
    previous_session_df: Optional[pd.DataFrame] = None,
    max_insights: int = 5
) -> List[str]:
    """
    Auto-analyze session and return 3-5 insights.

    This is a pure function with no Streamlit calls for testability.

    Args:
        df: Current session DataFrame
        previous_session_df: Optional previous session for comparison
        max_insights: Maximum number of insights to return

    Returns:
        List of insight strings

    Examples:
        - "Your driver carry improved 8 yards vs last session"
        - "7 Iron consistency dropped - check face angle"
        - "Best smash factor: 1.48 on shot #23"
    """
    insights = []

    if df.empty:
        return ["No data available for analysis"]

    # 1. Session overview insight
    shot_count = len(df)
    club_count = df['club'].nunique() if 'club' in df.columns else 0
    insights.append(f"You hit {shot_count} shots with {club_count} different clubs")

    # 2. Comparison to previous session
    if previous_session_df is not None and not previous_session_df.empty:
        comparison_insight = _compare_sessions(df, previous_session_df)
        if comparison_insight:
            insights.append(comparison_insight)

    # 3. Best shot insight
    best_shot_insight = _find_best_shot(df)
    if best_shot_insight:
        insights.append(best_shot_insight)

    # 4. Consistency insight
    consistency_insight = _analyze_consistency(df)
    if consistency_insight:
        insights.append(consistency_insight)

    # 5. Problem area insight
    problem_insight = _identify_problem_areas(df)
    if problem_insight:
        insights.append(problem_insight)

    # 6. Smash factor insight
    smash_insight = _analyze_smash_factor(df)
    if smash_insight:
        insights.append(smash_insight)

    # 7. Club-specific insight
    club_insight = _analyze_club_performance(df)
    if club_insight:
        insights.append(club_insight)

    return insights[:max_insights]


def _compare_sessions(
    current_df: pd.DataFrame,
    previous_df: pd.DataFrame
) -> Optional[str]:
    """Compare current session to previous session."""
    if 'carry' not in current_df.columns or 'carry' not in previous_df.columns:
        return None

    current_carry = current_df[current_df['carry'] > 0]['carry'].mean()
    previous_carry = previous_df[previous_df['carry'] > 0]['carry'].mean()

    if current_carry > 0 and previous_carry > 0:
        delta = current_carry - previous_carry
        if delta > 2:
            return f"Your average carry improved {delta:.0f} yards vs last session"
        elif delta < -2:
            return f"Your average carry dropped {abs(delta):.0f} yards vs last session"

    return None


def _find_best_shot(df: pd.DataFrame) -> Optional[str]:
    """Find the best shot in the session."""
    if 'carry' not in df.columns:
        return None

    valid_carry = df[df['carry'] > 0]
    if valid_carry.empty:
        return None

    best_idx = valid_carry['carry'].idxmax()
    best_shot = valid_carry.loc[best_idx]
    best_carry = best_shot['carry']
    best_club = best_shot.get('club', 'Unknown')

    return f"Best shot: {best_carry:.0f} yards with {best_club}"


def _analyze_consistency(df: pd.DataFrame) -> Optional[str]:
    """Analyze shot consistency."""
    if 'carry' not in df.columns or 'club' not in df.columns:
        return None

    # Find most and least consistent clubs
    club_stats = df.groupby('club').agg({
        'carry': ['std', 'count', 'mean']
    })
    club_stats.columns = ['std', 'count', 'mean']
    club_stats = club_stats[club_stats['count'] >= 3]  # At least 3 shots

    if club_stats.empty:
        return None

    most_consistent = club_stats['std'].idxmin()
    most_consistent_std = club_stats.loc[most_consistent, 'std']

    # Excellent consistency is std < 5 yards
    if most_consistent_std < 5:
        return f"Excellent consistency with {most_consistent} (±{most_consistent_std:.1f} yds)"
    elif most_consistent_std < 10:
        return f"Good consistency with {most_consistent} (±{most_consistent_std:.1f} yds)"

    return None


def _identify_problem_areas(df: pd.DataFrame) -> Optional[str]:
    """Identify potential problem areas."""
    problems = []

    # Check for low smash factor
    if 'smash' in df.columns:
        valid_smash = df[(df['smash'] > 0) & (df['smash'] < 2)]['smash']
        if len(valid_smash) > 0:
            avg_smash = valid_smash.mean()
            if avg_smash < 1.40:
                problems.append("contact quality")

    # Check for extreme face angles
    if 'face_angle' in df.columns:
        valid_face = df[df['face_angle'] != 0]['face_angle']
        if len(valid_face) > 0:
            avg_face = valid_face.mean()
            if abs(avg_face) > 3:
                direction = "open" if avg_face > 0 else "closed"
                problems.append(f"face angle ({direction})")

    if problems:
        return f"Areas to work on: {', '.join(problems)}"

    return None


def _analyze_smash_factor(df: pd.DataFrame) -> Optional[str]:
    """Analyze smash factor performance."""
    if 'smash' not in df.columns:
        return None

    valid_smash = df[(df['smash'] > 0) & (df['smash'] < 2)]['smash']
    if len(valid_smash) == 0:
        return None

    avg_smash = valid_smash.mean()
    max_smash = valid_smash.max()

    if max_smash >= 1.50:
        return f"Great contact! Best smash factor: {max_smash:.2f}"
    elif avg_smash >= 1.45:
        return f"Solid contact with avg smash factor of {avg_smash:.2f}"

    return None


def _analyze_club_performance(df: pd.DataFrame) -> Optional[str]:
    """Analyze performance by club."""
    if 'club' not in df.columns or 'carry' not in df.columns:
        return None

    # Find the club with the most shots
    club_counts = df['club'].value_counts()
    if club_counts.empty:
        return None

    most_used = club_counts.index[0]
    most_used_count = club_counts.iloc[0]

    if most_used_count >= 10:
        club_data = df[df['club'] == most_used]
        avg_carry = club_data['carry'].mean()
        return f"Focused on {most_used}: {most_used_count} shots, {avg_carry:.0f} yds avg"

    return None


def render_insights_card(
    df: pd.DataFrame,
    previous_session_df: Optional[pd.DataFrame] = None,
    title: str = "Today's Insights"
) -> None:
    """
    Display insights in a card UI.

    Args:
        df: Current session DataFrame
        previous_session_df: Optional previous session for comparison
        title: Card title
    """
    insights = generate_session_insights(df, previous_session_df)

    st.markdown(f"### {title}")

    if not insights:
        st.info("Hit some shots to see insights about your game!")
        return

    for insight in insights:
        # Determine icon based on content
        icon = _get_insight_icon(insight)

        st.markdown(
            f"""
            <div style="
                display: flex;
                align-items: flex-start;
                padding: 12px 16px;
                background: #F8F9FA;
                border-radius: 8px;
                margin-bottom: 8px;
                border-left: 3px solid #2D7F3E;
            ">
                <span style="font-size: 20px; margin-right: 12px;">{icon}</span>
                <span style="flex: 1;">{insight}</span>
            </div>
            """,
            unsafe_allow_html=True
        )


def _get_insight_icon(insight: str) -> str:
    """Get an appropriate icon for an insight."""
    insight_lower = insight.lower()

    if "improved" in insight_lower or "better" in insight_lower or "great" in insight_lower:
        return "📈"
    elif "dropped" in insight_lower or "work on" in insight_lower:
        return "📉"
    elif "best shot" in insight_lower:
        return "🏆"
    elif "consistent" in insight_lower:
        return "🎯"
    elif "smash" in insight_lower or "contact" in insight_lower:
        return "✨"
    elif "focused" in insight_lower:
        return "🏌️"
    else:
        return "💡"


def render_quick_insights_banner(df: pd.DataFrame) -> None:
    """
    Render a compact insights banner for dashboard headers.

    Args:
        df: Session DataFrame
    """
    insights = generate_session_insights(df, max_insights=2)

    if not insights:
        return

    # Join insights into a single line
    insights_text = " • ".join(insights[:2])

    st.markdown(
        f"""
        <div style="
            padding: 12px 16px;
            background: linear-gradient(90deg, #E8F5E9 0%, #F1F8E9 100%);
            border-radius: 8px;
            margin-bottom: 16px;
            border-left: 4px solid #2D7F3E;
        ">
            <span style="font-weight: 500;">💡 Quick Insights:</span>
            <span style="margin-left: 8px;">{insights_text}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
