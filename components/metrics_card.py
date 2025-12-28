"""
Metrics card component for displaying KPIs.
"""
import streamlit as st
import pandas as pd


def render_metrics_row(df: pd.DataFrame) -> None:
    """
    Render a row of key performance metrics.

    Args:
        df: DataFrame containing shot data with columns: carry, total, smash, ball_speed
    """
    col1, col2, col3, col4, col5 = st.columns(5)

    # Total Shots
    col1.metric("Total Shots", len(df))

    # Average Carry
    avg_carry = df['carry'].mean() if len(df) > 0 else 0
    col2.metric("Avg Carry", f"{avg_carry:.1f} yds" if avg_carry > 0 else "N/A")

    # Average Total
    avg_total = df['total'].mean() if len(df) > 0 else 0
    col3.metric("Avg Total", f"{avg_total:.1f} yds" if avg_total > 0 else "N/A")

    # Average Smash Factor
    avg_smash = df[df['smash'] > 0]['smash'].mean() if len(df) > 0 else 0
    col4.metric("Avg Smash", f"{avg_smash:.2f}" if avg_smash > 0 else "N/A")

    # Average Ball Speed
    avg_ball_speed = df['ball_speed'].mean() if len(df) > 0 else 0
    col5.metric("Avg Ball Speed", f"{avg_ball_speed:.1f} mph" if avg_ball_speed > 0 else "N/A")
