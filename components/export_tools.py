"""
Export tools for CSV and PDF generation.
"""
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime


def export_to_csv(df: pd.DataFrame, filename: str = None) -> bytes:
    """
    Export DataFrame to CSV format.

    Args:
        df: DataFrame to export
        filename: Optional filename (without extension)

    Returns:
        CSV data as bytes
    """
    if filename is None:
        filename = f"golf_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    csv = df.to_csv(index=False)
    return csv.encode('utf-8')


def render_csv_export_button(df: pd.DataFrame, session_id: str = None, label: str = "📥 Download CSV") -> None:
    """
    Render a CSV download button.

    Args:
        df: DataFrame to export
        session_id: Optional session ID for filename
        label: Button label
    """
    if df.empty:
        st.warning("No data to export")
        return

    # Generate filename
    if session_id:
        filename = f"session_{session_id}_{datetime.now().strftime('%Y%m%d')}.csv"
    else:
        filename = f"golf_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # Export data
    csv_data = export_to_csv(df, filename.replace('.csv', ''))

    st.download_button(
        label=label,
        data=csv_data,
        file_name=filename,
        mime='text/csv',
        use_container_width=True
    )


def export_to_excel(df_dict: dict, filename: str = None) -> bytes:
    """
    Export multiple DataFrames to Excel with separate sheets.

    Args:
        df_dict: Dictionary of {sheet_name: DataFrame}
        filename: Optional filename (without extension)

    Returns:
        Excel data as bytes
    """
    if filename is None:
        filename = f"golf_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    output = BytesIO()

    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in df_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        output.seek(0)
        return output.getvalue()
    except ImportError:
        st.error("Excel export requires openpyxl. Install with: pip install openpyxl")
        return None


def render_excel_export_button(df_dict: dict, session_id: str = None, label: str = "📊 Download Excel") -> None:
    """
    Render an Excel download button with multiple sheets.

    Args:
        df_dict: Dictionary of {sheet_name: DataFrame}
        session_id: Optional session ID for filename
        label: Button label
    """
    if not df_dict or all(df.empty for df in df_dict.values()):
        st.warning("No data to export")
        return

    # Generate filename
    if session_id:
        filename = f"session_{session_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    else:
        filename = f"golf_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    # Export data
    excel_data = export_to_excel(df_dict, filename.replace('.xlsx', ''))

    if excel_data:
        st.download_button(
            label=label,
            data=excel_data,
            file_name=filename,
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True
        )


def generate_session_summary(df: pd.DataFrame, session_id: str) -> str:
    """
    Generate a text summary of session data.

    Args:
        df: DataFrame containing session data
        session_id: Session identifier

    Returns:
        Formatted text summary
    """
    if df.empty:
        return "No data available for this session."

    summary = f"""
# Golf Session Report
**Session ID**: {session_id}
**Date**: {df['date_added'].iloc[0] if 'date_added' in df.columns else 'Unknown'}
**Total Shots**: {len(df)}

## Summary by Club

"""

    # Group by club
    if 'club' in df.columns:
        for club in df['club'].unique():
            club_data = df[df['club'] == club]

            summary += f"\n### {club}\n"
            summary += f"- Shots: {len(club_data)}\n"

            if 'carry' in club_data.columns:
                summary += f"- Avg Carry: {club_data['carry'].mean():.1f} yds (σ={club_data['carry'].std():.1f})\n"

            if 'total' in club_data.columns:
                summary += f"- Avg Total: {club_data['total'].mean():.1f} yds\n"

            if 'ball_speed' in club_data.columns:
                summary += f"- Avg Ball Speed: {club_data['ball_speed'].mean():.1f} mph\n"

            if 'smash' in club_data.columns and club_data['smash'].max() > 0:
                summary += f"- Avg Smash: {club_data[club_data['smash'] > 0]['smash'].mean():.2f}\n"

    summary += "\n---\n"
    summary += f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

    return summary


def render_summary_export(df: pd.DataFrame, session_id: str) -> None:
    """
    Render export options for session summary.

    Args:
        df: DataFrame containing session data
        session_id: Session identifier
    """
    st.subheader("📄 Export Session Report")

    col1, col2 = st.columns(2)

    with col1:
        # CSV Export
        render_csv_export_button(df, session_id, "📥 Download Raw Data (CSV)")

    with col2:
        # Text Summary Export
        summary_text = generate_session_summary(df, session_id)
        filename = f"session_{session_id}_summary.txt"

        st.download_button(
            label="📝 Download Summary (TXT)",
            data=summary_text.encode('utf-8'),
            file_name=filename,
            mime='text/plain',
            use_container_width=True
        )

    # Excel export (if multiple clubs)
    if 'club' in df.columns and df['club'].nunique() > 1:
        st.divider()

        # Create dictionary of DataFrames (one per club)
        df_dict = {}
        for club in df['club'].unique():
            df_dict[club] = df[df['club'] == club]

        render_excel_export_button(df_dict, session_id, "📊 Download by Club (Excel)")
