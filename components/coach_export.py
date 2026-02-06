"""
Coach Export component for generating PDF and CSV reports.

This component serves the 15% "Coach" persona who need:
- PDF summary with key charts
- CSV with all metrics
- Session summary text
- Problem shots highlighted
- Comparison to baseline
"""
import streamlit as st
import pandas as pd
from io import BytesIO
from typing import Optional, Dict, List
import json


def render_coach_export(
    df: pd.DataFrame,
    session_id: str,
    baseline_df: Optional[pd.DataFrame] = None
) -> None:
    """
    Render coach-ready export options.

    Args:
        df: Session DataFrame
        session_id: Session identifier
        baseline_df: Optional baseline session for comparison
    """
    st.subheader("Coach Report Export")
    st.markdown("""
    Generate reports suitable for sharing with your golf coach or instructor.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Quick Exports**")

        # CSV Export
        csv_data = export_session_csv(df, session_id)
        st.download_button(
            label="Download Full CSV",
            data=csv_data,
            file_name=f"coach_report_{session_id}.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Summary Text Export
        summary_text = generate_session_summary(df, session_id, baseline_df)
        st.download_button(
            label="Download Summary (Text)",
            data=summary_text,
            file_name=f"session_summary_{session_id}.txt",
            mime="text/plain",
            use_container_width=True
        )

        # JSON Export (for advanced users)
        json_data = export_session_json(df, session_id)
        st.download_button(
            label="Download JSON Data",
            data=json_data,
            file_name=f"session_data_{session_id}.json",
            mime="application/json",
            use_container_width=True
        )

    with col2:
        st.markdown("**Report Preview**")

        with st.expander("Session Summary", expanded=True):
            st.text(summary_text[:500] + "..." if len(summary_text) > 500 else summary_text)

        # Problem shots
        problem_shots = identify_problem_shots(df)
        if problem_shots:
            with st.expander(f"Problem Shots ({len(problem_shots)})"):
                st.dataframe(problem_shots, use_container_width=True, hide_index=True)

    st.divider()

    # Club-by-club breakdown
    st.markdown("**Club-by-Club Summary**")
    club_summary = generate_club_summary(df)
    if not club_summary.empty:
        st.dataframe(club_summary, use_container_width=True, hide_index=True)

        # Download club summary
        club_csv = club_summary.to_csv(index=False)
        st.download_button(
            label="Download Club Summary CSV",
            data=club_csv,
            file_name=f"club_summary_{session_id}.csv",
            mime="text/csv"
        )


def export_session_csv(df: pd.DataFrame, session_id: str) -> str:
    """
    Export session data to CSV with coach-relevant columns.

    Args:
        df: Session DataFrame
        session_id: Session identifier

    Returns:
        CSV string
    """
    # Select coach-relevant columns
    coach_columns = [
        'shot_id', 'club', 'carry', 'total', 'ball_speed', 'club_speed',
        'smash', 'launch_angle', 'back_spin', 'side_spin',
        'face_angle', 'club_path', 'attack_angle', 'dynamic_loft',
        'side_distance', 'shot_type', 'shot_tag'
    ]

    # Filter to available columns
    available_cols = [c for c in coach_columns if c in df.columns]

    export_df = df[available_cols].copy()

    # Round numeric columns
    numeric_cols = export_df.select_dtypes(include=['float64', 'float32']).columns
    export_df[numeric_cols] = export_df[numeric_cols].round(2)

    return export_df.to_csv(index=False)


def export_session_json(df: pd.DataFrame, session_id: str) -> str:
    """
    Export session data to JSON format.

    Args:
        df: Session DataFrame
        session_id: Session identifier

    Returns:
        JSON string
    """
    # Create structured export
    export_data = {
        "session_id": session_id,
        "shot_count": len(df),
        "summary": {
            "clubs_used": df['club'].unique().tolist() if 'club' in df.columns else [],
            "avg_carry": df['carry'].mean() if 'carry' in df.columns else 0,
            "avg_ball_speed": df['ball_speed'].mean() if 'ball_speed' in df.columns else 0,
            "avg_smash": df[df['smash'] > 0]['smash'].mean() if 'smash' in df.columns else 0,
        },
        "shots": df.to_dict(orient='records')
    }

    return json.dumps(export_data, indent=2, default=str)


def generate_session_summary(
    df: pd.DataFrame,
    session_id: str,
    baseline_df: Optional[pd.DataFrame] = None
) -> str:
    """
    Generate a text summary of the session for coach review.

    Args:
        df: Session DataFrame
        session_id: Session identifier
        baseline_df: Optional baseline for comparison

    Returns:
        Formatted text summary
    """
    lines = []
    lines.append(f"SESSION SUMMARY: {session_id}")
    lines.append("=" * 50)
    lines.append("")

    # Basic stats
    lines.append("OVERVIEW")
    lines.append("-" * 30)
    lines.append(f"Total Shots: {len(df)}")

    if 'club' in df.columns:
        clubs = df['club'].unique()
        lines.append(f"Clubs Used: {', '.join(clubs)}")

    lines.append("")

    # Key metrics
    lines.append("KEY METRICS")
    lines.append("-" * 30)

    if 'carry' in df.columns:
        valid_carry = df[df['carry'] > 0]['carry']
        if len(valid_carry) > 0:
            lines.append(f"Avg Carry: {valid_carry.mean():.1f} yards")
            lines.append(f"Best Carry: {valid_carry.max():.1f} yards")
            lines.append(f"Carry Std Dev: {valid_carry.std():.1f} yards")

    if 'ball_speed' in df.columns:
        valid_speed = df[df['ball_speed'] > 0]['ball_speed']
        if len(valid_speed) > 0:
            lines.append(f"Avg Ball Speed: {valid_speed.mean():.1f} mph")

    if 'smash' in df.columns:
        valid_smash = df[(df['smash'] > 0) & (df['smash'] < 2)]['smash']
        if len(valid_smash) > 0:
            lines.append(f"Avg Smash Factor: {valid_smash.mean():.3f}")

    lines.append("")

    # Comparison to baseline
    if baseline_df is not None and 'carry' in df.columns and 'carry' in baseline_df.columns:
        lines.append("COMPARISON TO BASELINE")
        lines.append("-" * 30)

        current_carry = df[df['carry'] > 0]['carry'].mean()
        baseline_carry = baseline_df[baseline_df['carry'] > 0]['carry'].mean()
        delta = current_carry - baseline_carry

        lines.append(f"Carry Change: {delta:+.1f} yards")

        if 'smash' in df.columns and 'smash' in baseline_df.columns:
            current_smash = df[(df['smash'] > 0) & (df['smash'] < 2)]['smash'].mean()
            baseline_smash = baseline_df[(baseline_df['smash'] > 0) & (baseline_df['smash'] < 2)]['smash'].mean()
            smash_delta = current_smash - baseline_smash
            lines.append(f"Smash Change: {smash_delta:+.3f}")

        lines.append("")

    # Club breakdown
    if 'club' in df.columns:
        lines.append("CLUB-BY-CLUB")
        lines.append("-" * 30)

        for club in sorted(df['club'].unique()):
            club_data = df[df['club'] == club]
            shot_count = len(club_data)

            avg_carry = 0
            if 'carry' in club_data.columns:
                valid_carry = club_data[club_data['carry'] > 0]['carry']
                avg_carry = valid_carry.mean() if len(valid_carry) > 0 else 0

            lines.append(f"{club}: {shot_count} shots, {avg_carry:.1f} yds avg carry")

    lines.append("")

    # Problem areas
    problem_shots = identify_problem_shots(df)
    if len(problem_shots) > 0:
        lines.append("AREAS TO ADDRESS")
        lines.append("-" * 30)
        lines.append(f"Found {len(problem_shots)} shots with potential issues")

        # Categorize issues
        if 'smash' in df.columns:
            low_smash = len(df[(df['smash'] > 0) & (df['smash'] < 1.35)])
            if low_smash > 0:
                lines.append(f"- {low_smash} shots with low contact quality (smash < 1.35)")

    lines.append("")
    lines.append("-" * 50)
    lines.append("Generated by Golf Data Lab")

    return "\n".join(lines)


def generate_club_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate a club-by-club summary table.

    Args:
        df: Session DataFrame

    Returns:
        Summary DataFrame
    """
    if 'club' not in df.columns:
        return pd.DataFrame()

    summary_rows = []

    for club in sorted(df['club'].unique()):
        club_data = df[df['club'] == club]
        row = {'Club': club, 'Shots': len(club_data)}

        if 'carry' in club_data.columns:
            valid_carry = club_data[club_data['carry'] > 0]['carry']
            row['Avg Carry'] = f"{valid_carry.mean():.1f}" if len(valid_carry) > 0 else "N/A"
            row['Max Carry'] = f"{valid_carry.max():.1f}" if len(valid_carry) > 0 else "N/A"
            row['Std Dev'] = f"{valid_carry.std():.1f}" if len(valid_carry) > 1 else "N/A"

        if 'ball_speed' in club_data.columns:
            valid_speed = club_data[club_data['ball_speed'] > 0]['ball_speed']
            row['Avg Speed'] = f"{valid_speed.mean():.1f}" if len(valid_speed) > 0 else "N/A"

        if 'smash' in club_data.columns:
            valid_smash = club_data[(club_data['smash'] > 0) & (club_data['smash'] < 2)]['smash']
            row['Avg Smash'] = f"{valid_smash.mean():.3f}" if len(valid_smash) > 0 else "N/A"

        summary_rows.append(row)

    return pd.DataFrame(summary_rows)


def identify_problem_shots(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify shots that may need attention from a coach.

    Args:
        df: Session DataFrame

    Returns:
        DataFrame of problem shots
    """
    problems = []

    for idx, row in df.iterrows():
        issues = []

        # Low smash factor
        if 'smash' in row and row['smash'] > 0 and row['smash'] < 1.35:
            issues.append("Low contact quality")

        # Extreme face angle
        if 'face_angle' in row and abs(row['face_angle']) > 5:
            direction = "open" if row['face_angle'] > 0 else "closed"
            issues.append(f"Face {direction} ({row['face_angle']:.1f}°)")

        # Extreme club path
        if 'club_path' in row and abs(row['club_path']) > 6:
            direction = "out-to-in" if row['club_path'] < 0 else "in-to-out"
            issues.append(f"Path {direction} ({row['club_path']:.1f}°)")

        if issues:
            problems.append({
                'Shot': row.get('shot_id', idx),
                'Club': row.get('club', 'Unknown'),
                'Carry': f"{row.get('carry', 0):.1f}",
                'Issues': ', '.join(issues)
            })

    return pd.DataFrame(problems)
