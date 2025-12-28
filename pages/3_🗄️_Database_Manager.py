"""
Database Manager Page - Comprehensive CRUD operations and data management
Phase 2: Enhanced with session operations, bulk editing, and audit trail
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
st.title("🗄️ Database Manager Pro")
st.subheader(f"Session: {selected_session_id}")

st.markdown("""
**Phase 2 Enhanced**: Comprehensive data management with session operations, bulk editing,
data quality tools, and full audit trail. All operations sync to SQLite + Supabase.
""")

st.divider()

# Get all clubs and sessions for operations
all_clubs = df['club'].unique().tolist()
all_sessions = golf_db.get_unique_sessions()

# Create tabs for different management operations
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "✏️ Edit Data",
    "🗑️ Delete Operations",
    "🔄 Session Operations",
    "⚡ Bulk Operations",
    "📊 Data Quality",
    "📜 Audit Trail"
])

# ============================================================================
# TAB 1: EDIT DATA
# ============================================================================
with tab1:
    st.header("Edit Session Data")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Rename Club (This Session)")
        st.caption("Change the name of a club for all shots in this session only")

        rename_club = st.selectbox(
            "Select Club to Rename",
            all_clubs,
            key="rename_select"
        )
        new_club_name = st.text_input(
            "New Club Name",
            placeholder="e.g., Driver → TaylorMade Stealth",
            key="new_name_input"
        )

        if st.button("✏️ Rename Club", key="rename_btn", type="primary"):
            if new_club_name:
                golf_db.rename_club(selected_session_id, rename_club, new_club_name)
                st.success(f"✅ Renamed '{rename_club}' to '{new_club_name}' in session {selected_session_id}")
                st.rerun()
            else:
                st.warning("Please enter a new name.")

    with col2:
        st.subheader("Rename Session")
        st.caption("Change the session ID for all shots in this session")

        new_session_id = st.text_input(
            "New Session ID",
            placeholder=f"e.g., {selected_session_id} → Session_2025-12-28",
            key="new_session_id_input"
        )

        if st.button("✏️ Rename Session", key="rename_session_btn", type="primary"):
            if new_session_id:
                shots_updated = golf_db.rename_session(selected_session_id, new_session_id)
                st.success(f"✅ Renamed session to '{new_session_id}' ({shots_updated} shots updated)")
                st.rerun()
            else:
                st.warning("Please enter a new session ID.")

    st.divider()

    # Shot count by club
    st.subheader("Shot Count by Club")
    club_counts = df['club'].value_counts().reset_index()
    club_counts.columns = ['Club', 'Shots']
    st.dataframe(club_counts, use_container_width=True, hide_index=True)


# ============================================================================
# TAB 2: DELETE OPERATIONS
# ============================================================================
with tab2:
    st.header("Delete Operations")
    st.warning("⚠️ Deletions are archived for safety and can be restored from the Audit Trail tab.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Delete Entire Session")
        st.caption(f"Remove all {len(df)} shots in this session")

        st.error(f"This will delete **{len(df)} shots** across **{len(all_clubs)} clubs**")

        confirm_session_delete = st.checkbox(
            "I confirm deletion of entire session",
            key="confirm_session_delete"
        )

        if st.button(
            "🗑️ Delete Session",
            key="delete_session_btn",
            type="primary",
            disabled=not confirm_session_delete
        ):
            shots_deleted = golf_db.delete_session(selected_session_id, archive=True)
            st.success(f"✅ Deleted session {selected_session_id} ({shots_deleted} shots archived)")
            st.info("💡 Shots have been archived and can be restored from the Audit Trail tab")
            st.rerun()

    with col2:
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
            "🗑️ Delete Club Shots",
            key="delete_club_btn",
            type="primary",
            disabled=not confirm_club
        ):
            golf_db.delete_club_session(selected_session_id, delete_club)
            st.success(f"✅ Deleted all shots for '{delete_club}'")
            st.rerun()

    with col3:
        st.subheader("Delete Individual Shot")
        st.caption("Remove a specific shot by its ID")

        if 'shot_id' in df.columns:
            shot_options = [
                f"{row['shot_id']} - {row['club']} ({row['carry']:.0f} yds)"
                for _, row in df.iterrows()
            ]

            shot_to_delete_str = st.selectbox(
                "Select Shot to Delete",
                shot_options,
                key="delete_shot_select"
            )

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


# ============================================================================
# TAB 3: SESSION OPERATIONS
# ============================================================================
with tab3:
    st.header("Session Operations")
    st.caption("Merge multiple sessions or split a session into separate parts")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Merge Sessions")
        st.caption("Combine multiple sessions into one unified session")

        # Multi-select for sessions to merge
        session_options = [s['session_id'] for s in all_sessions]
        sessions_to_merge = st.multiselect(
            "Select Sessions to Merge",
            session_options,
            key="merge_sessions_select"
        )

        merged_session_id = st.text_input(
            "New Merged Session ID",
            placeholder="e.g., Combined_Session_2025-12-28",
            key="merged_session_id"
        )

        if st.button("🔄 Merge Sessions", key="merge_btn", type="primary"):
            if len(sessions_to_merge) < 2:
                st.warning("Please select at least 2 sessions to merge.")
            elif not merged_session_id:
                st.warning("Please enter a new session ID for merged data.")
            else:
                shots_merged = golf_db.merge_sessions(sessions_to_merge, merged_session_id)
                st.success(f"✅ Merged {len(sessions_to_merge)} sessions into '{merged_session_id}' ({shots_merged} shots)")
                st.rerun()

    with col2:
        st.subheader("Split Session")
        st.caption("Move specific shots to a new session")

        if 'shot_id' in df.columns:
            shot_options_split = st.multiselect(
                "Select Shots to Move",
                df['shot_id'].tolist(),
                key="split_shots_select",
                format_func=lambda x: f"{x} - {df[df['shot_id']==x]['club'].iloc[0] if len(df[df['shot_id']==x]) > 0 else ''}"
            )

            new_split_session_id = st.text_input(
                "New Session ID for Selected Shots",
                placeholder="e.g., Session_Part_2",
                key="split_session_id"
            )

            if st.button("🔄 Split Session", key="split_btn", type="primary"):
                if len(shot_options_split) == 0:
                    st.warning("Please select at least 1 shot to move.")
                elif not new_split_session_id:
                    st.warning("Please enter a new session ID.")
                else:
                    shots_moved = golf_db.split_session(selected_session_id, shot_options_split, new_split_session_id)
                    st.success(f"✅ Moved {shots_moved} shots to session '{new_split_session_id}'")
                    st.rerun()
        else:
            st.info("No shot IDs available for splitting.")


# ============================================================================
# TAB 4: BULK OPERATIONS
# ============================================================================
with tab4:
    st.header("Bulk Operations")
    st.caption("Perform operations across multiple sessions or shots at once")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Bulk Rename Club (All Sessions)")
        st.caption("Rename a club across ALL sessions in the database")

        all_shots_df = golf_db.get_session_data()
        all_unique_clubs = all_shots_df['club'].unique().tolist() if not all_shots_df.empty else []

        old_club_name = st.selectbox(
            "Select Club to Rename Globally",
            all_unique_clubs,
            key="bulk_rename_old"
        )

        new_club_name_bulk = st.text_input(
            "New Club Name (Global)",
            placeholder="e.g., 7-Iron → Titleist T200 7i",
            key="bulk_rename_new"
        )

        if st.button("⚡ Rename Globally", key="bulk_rename_btn", type="primary"):
            if new_club_name_bulk:
                shots_updated = golf_db.bulk_rename_clubs(old_club_name, new_club_name_bulk)
                st.success(f"✅ Renamed '{old_club_name}' to '{new_club_name_bulk}' across all sessions ({shots_updated} shots)")
                st.rerun()
            else:
                st.warning("Please enter a new club name.")

    with col2:
        st.subheader("Recalculate Metrics")
        st.caption("Recompute smash factor and clean invalid data (99999 → 0)")

        recalc_scope = st.radio(
            "Recalculation Scope",
            ["Current Session Only", "All Sessions"],
            key="recalc_scope"
        )

        if st.button("⚡ Recalculate", key="recalc_btn", type="primary"):
            if recalc_scope == "Current Session Only":
                shots_updated = golf_db.recalculate_metrics(selected_session_id)
                st.success(f"✅ Recalculated metrics for session {selected_session_id} ({shots_updated} shots)")
            else:
                shots_updated = golf_db.recalculate_metrics()
                st.success(f"✅ Recalculated metrics for all sessions ({shots_updated} shots)")
            st.rerun()


# ============================================================================
# TAB 5: DATA QUALITY
# ============================================================================
with tab5:
    st.header("Data Quality Tools")
    st.caption("Detect and fix data issues automatically")

    # Outlier Detection (using new function)
    st.subheader("🔍 Outlier Detection")
    outliers_df = golf_db.find_outliers(selected_session_id)

    if not outliers_df.empty:
        st.warning(f"⚠️ Found {len(outliers_df)} outlier shots in this session:")
        st.dataframe(outliers_df, use_container_width=True)
    else:
        st.success("✅ No outliers detected in this session!")

    st.divider()

    # Validation (using new function)
    st.subheader("✅ Data Validation")
    invalid_shots_df = golf_db.validate_shot_data()

    if not invalid_shots_df.empty:
        st.warning(f"⚠️ Found {len(invalid_shots_df)} shots with missing critical data:")
        st.dataframe(invalid_shots_df, use_container_width=True)
    else:
        st.success("✅ All shots have complete critical data!")

    st.divider()

    # Deduplication
    st.subheader("🔁 Duplicate Detection")
    if st.button("🔍 Check for Duplicates", key="dedup_btn"):
        duplicates_removed = golf_db.deduplicate_shots()
        if duplicates_removed > 0:
            st.success(f"✅ Removed {duplicates_removed} duplicate shots")
            st.rerun()
        else:
            st.info("✅ No duplicates found!")


# ============================================================================
# TAB 6: AUDIT TRAIL
# ============================================================================
with tab6:
    st.header("Audit Trail & Recovery")
    st.caption("View change history and restore deleted shots")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📜 Change Log")
        change_log_df = golf_db.get_change_log(session_id=None, limit=20)

        if not change_log_df.empty:
            st.dataframe(
                change_log_df[['timestamp', 'operation', 'entity_type', 'entity_id', 'details']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No changes logged yet.")

    with col2:
        st.subheader("♻️ Restore Deleted Shots")
        archived_shots_df = golf_db.get_archived_shots(selected_session_id)

        if not archived_shots_df.empty:
            st.warning(f"Found {len(archived_shots_df)} archived shots from this session:")

            # Show archived shots
            st.dataframe(
                archived_shots_df[['shot_id', 'deleted_at', 'deleted_reason']],
                use_container_width=True,
                hide_index=True
            )

            # Restore interface
            shots_to_restore = st.multiselect(
                "Select Shots to Restore",
                archived_shots_df['shot_id'].tolist(),
                key="restore_shots_select"
            )

            if st.button("♻️ Restore Selected Shots", key="restore_btn", type="primary"):
                if len(shots_to_restore) > 0:
                    restored = golf_db.restore_deleted_shots(shots_to_restore)
                    st.success(f"✅ Restored {restored} shots from archive")
                    st.rerun()
                else:
                    st.warning("Please select at least one shot to restore.")
        else:
            st.info("No archived shots for this session.")


# ============================================================================
# FOOTER: DATABASE STATISTICS
# ============================================================================
st.divider()

st.subheader("📊 Database Statistics")

col1, col2, col3, col4, col5 = st.columns(5)

# Get all data for stats
all_shots = golf_db.get_session_data()
archived_count = len(golf_db.get_archived_shots())

col1.metric("Total Sessions", len(all_sessions) if all_sessions else 0)
col2.metric("Total Shots", len(all_shots))
col3.metric("Current Session", len(df))
col4.metric("Archived Shots", archived_count)
col5.metric("Unique Clubs", len(all_clubs))

# Sync status
with st.expander("🔄 Sync Status & Technical Details"):
    st.markdown("""
    ### Database Synchronization

    Your data is stored in multiple locations with automatic syncing:
    - **Local SQLite**: `golf_stats.db` (primary storage, offline-first)
    - **Cloud Supabase**: Synced automatically on every write operation
    - **BigQuery**: Synced via `scripts/supabase_to_bigquery.py`

    ### Phase 2 Enhancements

    **New Tables:**
    - `shots_archive`: Stores deleted shots for recovery
    - `change_log`: Tracks all database modifications

    **New Functions:**
    - Session operations: delete, merge, split, rename
    - Bulk operations: global rename, recalculate metrics, bulk update
    - Data quality: outlier detection, validation, deduplication
    - Audit trail: change log, restore deleted shots

    All operations maintain data integrity across local and cloud databases.
    """)
