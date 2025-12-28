"""
Database Manager Page - CRUD operations on golf data
"""
import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import golf_db
from components import render_session_selector

st.set_page_config(layout="wide", page_title="Database Manager - My Golf Lab")

# Initialize DB
golf_db.init_db()

# Sidebar: Session selector
with st.sidebar:
    st.header("🔗 Navigation")
    st.page_link("pages/1_📥_Data_Import.py", label="📥 Import Data", icon="📥")
    st.page_link("pages/2_📊_Dashboard.py", label="📊 Dashboard", icon="📊")

    st.divider()

    selected_session_id, df, selected_clubs = render_session_selector(golf_db)

# Stop if no data
if df.empty:
    st.info("No data to display. Please import a session first.")
    st.page_link("pages/1_📥_Data_Import.py", label="Go to Data Import", icon="📥")
    st.stop()

# Main content
st.title("🗄️ Database Manager")
st.subheader(f"Session: {selected_session_id}")

st.markdown("""
Manage your golf data with precision. Rename clubs, delete shots, or clean up entire sessions.
All operations sync to both local SQLite and cloud Supabase databases.
""")

st.divider()

# Get all clubs for this session
all_clubs = df['club'].unique().tolist()

# Create tabs for different management operations
tab1, tab2, tab3 = st.tabs(["✏️ Edit Data", "🗑️ Delete Operations", "📊 Data Quality"])

# TAB 1: EDIT DATA
with tab1:
    st.header("Edit Session Data")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Rename Club")
        st.caption("Change the name of a club for all shots in this session")

        rename_club = st.selectbox(
            "Select Club to Rename",
            all_clubs,
            key="rename_select"
        )
        new_name = st.text_input(
            "New Club Name",
            placeholder="e.g., Driver → TaylorMade Stealth",
            key="new_name_input"
        )

        if st.button("✏️ Rename Club", key="rename_btn", type="primary"):
            if new_name:
                golf_db.rename_club(selected_session_id, rename_club, new_name)
                st.success(f"✅ Renamed '{rename_club}' to '{new_name}'")
                st.rerun()
            else:
                st.warning("Please enter a new name.")

    with col2:
        st.subheader("Shot Count by Club")
        st.caption("Current distribution of shots in this session")

        # Show shot counts per club
        club_counts = df['club'].value_counts().reset_index()
        club_counts.columns = ['Club', 'Shots']

        st.dataframe(
            club_counts,
            use_container_width=True,
            hide_index=True
        )

# TAB 2: DELETE OPERATIONS
with tab2:
    st.header("Delete Operations")
    st.warning("⚠️ Deletion is permanent and affects both local and cloud databases!")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Delete All Shots for a Club")
        st.caption("Remove all shots for a specific club from this session")

        delete_club = st.selectbox(
            "Select Club to Delete",
            all_clubs,
            key="delete_club_select"
        )

        shot_count = len(df[df['club'] == delete_club])
        st.error(f"This will delete **{shot_count} shots** for '{delete_club}'")

        confirm_club = st.checkbox(
            f"I confirm deletion of all {delete_club} shots",
            key="confirm_club_delete"
        )

        if st.button(
            "🗑️ Delete All Shots for Club",
            key="delete_club_btn",
            type="primary",
            disabled=not confirm_club
        ):
            golf_db.delete_club_session(selected_session_id, delete_club)
            st.success(f"✅ Deleted all shots for '{delete_club}'")
            st.rerun()

    with col2:
        st.subheader("Delete Individual Shot")
        st.caption("Remove a specific shot by its ID")

        if 'shot_id' in df.columns:
            # Create a more descriptive shot list
            shot_options = [
                f"{row['shot_id']} - {row['club']} ({row['carry']:.0f} yds)"
                for _, row in df.iterrows()
            ]

            shot_to_delete_str = st.selectbox(
                "Select Shot to Delete",
                shot_options,
                key="delete_shot_select"
            )

            # Extract shot_id from the selection
            shot_to_delete = shot_to_delete_str.split(" - ")[0]

            confirm_shot = st.checkbox(
                "I confirm deletion of this shot",
                key="confirm_shot_delete"
            )

            if st.button(
                "🗑️ Delete Shot",
                key="delete_shot_btn",
                disabled=not confirm_shot
            ):
                golf_db.delete_shot(shot_to_delete)
                st.success(f"✅ Deleted shot {shot_to_delete}")
                st.rerun()
        else:
            st.info("No shot IDs available for deletion.")

# TAB 3: DATA QUALITY
with tab3:
    st.header("Data Quality Checks")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Missing Data")

        # Check for missing critical fields
        critical_fields = ['ball_speed', 'club_speed', 'carry', 'total']
        missing_data = {}

        for field in critical_fields:
            if field in df.columns:
                missing_count = df[field].isna().sum() + (df[field] == 0).sum()
                missing_data[field] = missing_count

        if any(v > 0 for v in missing_data.values()):
            st.warning("⚠️ Found shots with missing data:")
            for field, count in missing_data.items():
                if count > 0:
                    st.write(f"- **{field}**: {count} shots")
        else:
            st.success("✅ No missing data in critical fields!")

    with col2:
        st.subheader("Outlier Detection")

        # Check for unrealistic values
        outliers = []

        if 'carry' in df.columns:
            extreme_carry = df[df['carry'] > 400]
            if len(extreme_carry) > 0:
                outliers.append(f"Carry > 400 yds: {len(extreme_carry)} shots")

        if 'smash' in df.columns:
            extreme_smash = df[df['smash'] > 1.6]
            if len(extreme_smash) > 0:
                outliers.append(f"Smash > 1.6: {len(extreme_smash)} shots")

        if 'ball_speed' in df.columns:
            extreme_speed = df[df['ball_speed'] > 200]
            if len(extreme_speed) > 0:
                outliers.append(f"Ball speed > 200 mph: {len(extreme_speed)} shots")

        if outliers:
            st.warning("⚠️ Potential outliers detected:")
            for outlier in outliers:
                st.write(f"- {outlier}")
        else:
            st.success("✅ No obvious outliers detected!")

st.divider()

# Database statistics
st.subheader("📊 Database Statistics")

col1, col2, col3, col4 = st.columns(4)

# Get all data for stats
all_shots = golf_db.get_session_data()
all_sessions = golf_db.get_unique_sessions()

col1.metric("Total Sessions", len(all_sessions) if all_sessions else 0)
col2.metric("Total Shots", len(all_shots))
col3.metric("Current Session Shots", len(df))
col4.metric("Clubs in Session", len(all_clubs))

# Sync status
with st.expander("🔄 Sync Status"):
    st.markdown("""
    ### Database Synchronization

    Your data is stored in multiple locations:
    - **Local SQLite**: `golf_stats.db` (primary storage)
    - **Cloud Supabase**: Synced automatically on every write operation
    - **BigQuery**: Synced via `scripts/supabase_to_bigquery.py`

    All edit and delete operations in this interface automatically sync to both
    local and cloud databases.
    """)
