"""
Distance table component showing true club distances.
"""
import streamlit as st
import pandas as pd
from analytics.utils import calculate_distance_stats


def render_distance_table(df: pd.DataFrame) -> None:
    """
    Render a table showing median and IQR distances per club.

    Args:
        df: DataFrame containing shot data with club, carry, total columns

    Notes:
        - Shows median (typical) distances instead of maximum
        - Displays IQR range (Q25-Q75) for each club
        - Sorts clubs by median carry distance (longest first)
        - Indicates confidence level based on sample size
        - Requires 3+ shots per club for analysis
    """
    st.subheader("True Club Distances")

    if df.empty:
        st.info("No data available for distance table")
        return

    # Check required columns
    if 'club' not in df.columns or 'carry' not in df.columns:
        st.warning("Missing required columns: club and/or carry")
        return

    # Get unique clubs
    clubs = df['club'].dropna().unique()

    if len(clubs) == 0:
        st.info("No club data available")
        return

    # Calculate stats for each club
    club_stats = []
    insufficient_clubs = []

    for club in clubs:
        stats = calculate_distance_stats(df, club)

        if stats is None:
            # Track clubs with insufficient data
            club_count = len(df[df['club'] == club].dropna(subset=['carry']))
            insufficient_clubs.append(f"{club} ({club_count} shots)")
            continue

        # Build row for table
        row = {
            'Club': club,
            'Typical Carry': f"{stats['median']:.1f} yds",
            'Carry Range': f"{stats['q25']:.1f}-{stats['q75']:.1f}",
            'Best Carry': f"{stats['max']:.1f} yds",
            'Shots': stats['sample_size'],
            'Confidence': stats['confidence']
        }

        # Add total distance if available
        if 'total_median' in stats:
            row['Typical Total'] = f"{stats['total_median']:.1f} yds"
        else:
            row['Typical Total'] = "N/A"

        # Store raw median for sorting
        row['_median_raw'] = stats['median']

        club_stats.append(row)

    if not club_stats:
        st.warning("No clubs have sufficient data (need 3+ shots per club)")
        if insufficient_clubs:
            st.caption(f"Clubs found: {', '.join(insufficient_clubs)}")
        return

    # Convert to DataFrame
    table_df = pd.DataFrame(club_stats)

    # Sort by median carry (descending - longest first)
    table_df = table_df.sort_values('_median_raw', ascending=False)

    # Drop the raw column (used only for sorting)
    display_df = table_df.drop(columns=['_median_raw'])

    # Display table with column configuration
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "Club": st.column_config.TextColumn(
                "Club",
                width="medium"
            ),
            "Typical Carry": st.column_config.TextColumn(
                "Typical Carry",
                help="Median carry distance (50th percentile)",
                width="medium"
            ),
            "Carry Range": st.column_config.TextColumn(
                "Carry Range (IQR)",
                help="Middle 50% range (25th to 75th percentile)",
                width="medium"
            ),
            "Best Carry": st.column_config.TextColumn(
                "Best Carry",
                help="Maximum carry distance (may include outliers)",
                width="medium"
            ),
            "Typical Total": st.column_config.TextColumn(
                "Typical Total",
                help="Median total distance (carry + roll)",
                width="medium"
            ),
            "Shots": st.column_config.NumberColumn(
                "Shots",
                help="Number of shots after outlier filtering",
                width="small"
            ),
            "Confidence": st.column_config.TextColumn(
                "Confidence",
                help="Low (<5 shots), Medium (<10 shots), High (10+ shots)",
                width="small"
            )
        },
        hide_index=True
    )

    # Show interpretation guide
    st.info(
        "📊 **Interpretation Guide**\n\n"
        "• **Typical** = Median (50th percentile) — your most common distance\n"
        "• **Range** = Middle 50% of shots (IQR) — where most shots land\n"
        "• **Best** = Maximum recorded (may include hot shots)\n\n"
        "💡 Use *Typical* distances for club selection, not maximum. More reliable for course management."
    )

    # Show insufficient data clubs if any
    if insufficient_clubs:
        st.caption(
            f"⚠️ **Clubs with insufficient data (< 3 shots):** {', '.join(insufficient_clubs)}"
        )
