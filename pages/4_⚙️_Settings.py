"""
Settings Page — Import data, manage sessions, data quality, sync, and tags.

Combines the former Data Import and Database Manager pages into one
tucked-away Settings page so the main flow stays journal → dashboard → clubs → coach.
"""
import streamlit as st
import pandas as pd
import re

from automation.naming_conventions import ClubNameNormalizer
import golf_db
import golf_scraper
import observability
from services.data_access import (
    get_unique_sessions,
    get_session_data,
    clear_all_caches,
)
from utils.session_state import get_read_mode
from utils.responsive import add_responsive_css, render_compact_toggle
from components import (
    render_session_selector,
    render_shared_sidebar,
    render_no_data_state,
)
from components.shared_sidebar import (
    render_data_source,
    render_sync_status,
    render_mode_toggle,
    render_appearance_toggle,
)

_normalizer = ClubNameNormalizer()

st.set_page_config(layout="wide", page_title="Settings - My Golf Lab", page_icon="⚙️")
add_responsive_css()

golf_db.init_db()
read_mode = get_read_mode()

# Sidebar
render_shared_sidebar(current_page="settings")

with st.sidebar:
    st.divider()
    selected_session_id, df, selected_clubs = render_session_selector(
        lambda: get_unique_sessions(read_mode=read_mode),
        lambda session_id: get_session_data(session_id, read_mode=read_mode),
    )

st.title("Settings")
st.caption("Data management, maintenance, and tagging")

st.divider()

all_sessions = get_unique_sessions(read_mode=read_mode)
all_clubs = df["club"].unique().tolist() if not df.empty and "club" in df.columns else []

# ─── Tabs ──────────────────────────────────────────────────────
tab_data, tab_maintenance, tab_tags, tab_automation, tab_display = st.tabs([
    "Data",
    "Maintenance",
    "Tags",
    "Automation",
    "Display",
])


# ================================================================
# TAB 1: DATA (Import + Sessions)
# ================================================================
with tab_data:
    st.header("Import Golf Data")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Import from Uneekor URL")

        uneekor_url = st.text_input(
            "Paste Uneekor Report URL",
            placeholder="https://myuneekor.com/report?id=12345&key=abc123...",
            help="Copy the full URL from your Uneekor report page",
        )

        if st.button("Run Import", type="primary", use_container_width=True):
            if uneekor_url:
                st.info("Starting import...")
                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_progress(msg):
                    status_text.text(msg)

                result = golf_scraper.run_scraper(uneekor_url, update_progress)
                clear_all_caches()

                progress_bar.empty()
                status_text.empty()

                if result.get("status") == "success":
                    st.success(f"Import complete! {result.get('message', '')}")
                    st.balloons()
                else:
                    st.error(f"Import failed: {result.get('message', 'Unknown error')}")

                report_id, _ = golf_scraper.extract_url_params(uneekor_url)
                invalid_shots_df = golf_db.validate_shot_data(session_id=report_id)
                if not invalid_shots_df.empty:
                    st.warning(
                        f"Found {len(invalid_shots_df)} shots missing critical fields."
                    )
            else:
                st.error("Please enter a valid Uneekor URL")

        with st.expander("How to Import Data"):
            st.markdown("""
            1. Log in to your Uneekor account
            2. Find your practice session in reports
            3. Copy the full URL from your browser
            4. Paste the URL above and click **Run Import**
            """)

    with col2:
        st.subheader("Import History")

        unique_sessions = get_unique_sessions(read_mode=read_mode)
        if unique_sessions:
            st.write(f"**{len(unique_sessions)} sessions** in database")
            for session in unique_sessions[:5]:
                display_date = session.get("session_date") or session.get("date_added", "Unknown")
                if display_date and display_date != "Unknown" and hasattr(display_date, "strftime"):
                    display_date = display_date.strftime("%Y-%m-%d")
                st.caption(f"{session['session_id']} — {display_date}")
        else:
            st.info("No sessions imported yet")

        st.divider()
        st.subheader("Recent Imports")
        recent_imports = observability.read_recent_events("import_runs.jsonl", limit=5)
        if recent_imports:
            rows = [
                {
                    "status": item.get("status", "unknown"),
                    "report_id": item.get("report_id", ""),
                    "shots": item.get("shots_imported", 0),
                    "errors": item.get("errors", 0),
                    "duration_sec": item.get("duration_sec", 0),
                }
                for item in recent_imports
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.caption("No import runs logged yet")

    st.divider()

    # ── Sessions Section ──
    if df.empty:
        st.info("Select a session in the sidebar to manage it.")
    else:
        st.header(f"Session: {selected_session_id}")

        # ── Edit ──
        st.subheader("Edit")
        edit_c1, edit_c2, edit_c3 = st.columns(3)

        with edit_c1:
            st.markdown("**Rename Club (this session)**")
            rename_club = st.selectbox("Club to Rename", all_clubs, key="rename_select")
            new_club_name = st.text_input("New Name", key="new_name_input")
            if st.button("Rename Club", key="rename_btn", type="primary"):
                if new_club_name:
                    golf_db.rename_club(selected_session_id, rename_club, new_club_name)
                    clear_all_caches()
                    st.success(f"Renamed '{rename_club}' to '{new_club_name}'")
                    st.rerun()

        with edit_c2:
            st.markdown("**Rename Session**")
            new_session_id = st.text_input("New Session ID", key="new_session_id_input")
            if st.button("Rename Session", key="rename_session_btn", type="primary"):
                if new_session_id:
                    shots_updated = golf_db.rename_session(selected_session_id, new_session_id)
                    clear_all_caches()
                    st.success(f"Renamed to '{new_session_id}' ({shots_updated} shots)")
                    st.rerun()

        with edit_c3:
            st.markdown("**Session Type**")
            session_type_values = df.get("session_type", pd.Series()).dropna().unique().tolist()
            current_type = session_type_values[0] if len(session_type_values) == 1 else "Mixed/Unset"
            st.caption(f"Current: {current_type}")
            session_type_options = ["Unset", "Practice", "Round", "Gapping", "Fitting", "Combine"]
            selected_type = st.selectbox("Set Type", session_type_options, key="session_type_select")
            if st.button("Apply", key="apply_session_type_btn", type="primary"):
                value = None if selected_type == "Unset" else selected_type
                updated = golf_db.update_session_type(selected_session_id, value)
                clear_all_caches()
                st.success(f"Updated type for {updated} shots")
                st.rerun()

        st.divider()

        # ── Delete ──
        st.subheader("Delete Operations")
        st.warning("Deletions are archived for safety and can be restored below.")

        del_c1, del_c2, del_c3 = st.columns(3)

        with del_c1:
            st.markdown("**Delete Session**")
            st.error(f"This deletes **{len(df)} shots** across **{len(all_clubs)} clubs**")
            confirm_session = st.checkbox("Confirm", key="confirm_session_delete")
            if st.button("Delete Session", key="delete_session_btn", type="primary", disabled=not confirm_session):
                shots_deleted = golf_db.delete_session(selected_session_id, archive=True)
                clear_all_caches()
                st.success(f"Deleted session ({shots_deleted} shots archived)")
                st.rerun()

        with del_c2:
            st.markdown("**Delete Club Shots**")
            delete_club = st.selectbox("Club", all_clubs, key="delete_club_select")
            shot_count = len(df[df["club"] == delete_club]) if delete_club else 0
            st.error(f"Deletes **{shot_count} shots** for '{delete_club}'")
            confirm_club = st.checkbox("Confirm", key="confirm_club_delete")
            if st.button("Delete Club", key="delete_club_btn", type="primary", disabled=not confirm_club):
                golf_db.delete_club_session(selected_session_id, delete_club)
                clear_all_caches()
                st.success(f"Deleted all '{delete_club}' shots")
                st.rerun()

        with del_c3:
            st.markdown("**Delete Individual Shot**")
            if "shot_id" in df.columns:
                shot_opts = [
                    f"{row['shot_id']} - {row['club']} ({row['carry']:.0f} yds)"
                    for _, row in df.iterrows()
                ]
                shot_str = st.selectbox("Shot", shot_opts, key="delete_shot_select")
                shot_id = shot_str.split(" - ")[0]
                confirm_shot = st.checkbox("Confirm", key="confirm_shot_delete")
                if st.button("Delete Shot", key="delete_shot_btn", disabled=not confirm_shot):
                    golf_db.delete_shot(shot_id)
                    clear_all_caches()
                    st.success(f"Deleted shot {shot_id}")
                    st.rerun()

        st.divider()

        # ── Merge / Split ──
        st.subheader("Merge & Split")
        ms_c1, ms_c2 = st.columns(2)

        with ms_c1:
            st.markdown("**Merge Sessions**")
            session_options = [s["session_id"] for s in all_sessions]
            sessions_to_merge = st.multiselect("Sessions to Merge", session_options, key="merge_select")
            merged_id = st.text_input("Merged Session ID", key="merged_session_id")
            if st.button("Merge", key="merge_btn", type="primary"):
                if len(sessions_to_merge) < 2:
                    st.warning("Select at least 2 sessions.")
                elif not merged_id:
                    st.warning("Enter a new session ID.")
                else:
                    shots_merged = golf_db.merge_sessions(sessions_to_merge, merged_id)
                    clear_all_caches()
                    st.success(f"Merged {len(sessions_to_merge)} sessions ({shots_merged} shots)")
                    st.rerun()

        with ms_c2:
            st.markdown("**Split Session**")
            if "shot_id" in df.columns:
                split_shots = st.multiselect(
                    "Shots to Move",
                    df["shot_id"].tolist(),
                    key="split_shots_select",
                    format_func=lambda x: f"{x} - {df[df['shot_id']==x]['club'].iloc[0] if len(df[df['shot_id']==x]) > 0 else ''}",
                )
                new_split_id = st.text_input("New Session ID", key="split_session_id")
                if st.button("Split", key="split_btn", type="primary"):
                    if not split_shots:
                        st.warning("Select at least 1 shot.")
                    elif not new_split_id:
                        st.warning("Enter a new session ID.")
                    else:
                        moved = golf_db.split_session(selected_session_id, split_shots, new_split_id)
                        clear_all_caches()
                        st.success(f"Moved {moved} shots to '{new_split_id}'")
                        st.rerun()

        st.divider()

        # ── Bulk Operations ──
        st.subheader("Bulk Operations")
        bulk_c1, bulk_c2 = st.columns(2)

        with bulk_c1:
            st.markdown("**Bulk Rename Club (All Sessions)**")
            all_shots_df = get_session_data()
            all_unique_clubs = all_shots_df["club"].unique().tolist() if not all_shots_df.empty else []
            old_club = st.selectbox("Club to Rename Globally", all_unique_clubs, key="bulk_rename_old")
            new_club_bulk = st.text_input("New Name (Global)", key="bulk_rename_new")
            if st.button("Rename Globally", key="bulk_rename_btn", type="primary"):
                if new_club_bulk:
                    count = golf_db.bulk_rename_clubs(old_club, new_club_bulk)
                    clear_all_caches()
                    st.success(f"Renamed '{old_club}' globally ({count} shots)")
                    st.rerun()

        with bulk_c2:
            st.markdown("**Recalculate Metrics**")
            recalc_scope = st.radio("Scope", ["Current Session", "All Sessions"], key="recalc_scope")
            if st.button("Recalculate", key="recalc_btn", type="primary"):
                sid = selected_session_id if recalc_scope == "Current Session" else None
                count = golf_db.recalculate_metrics(sid)
                clear_all_caches()
                st.success(f"Recalculated ({count} shots)")
                st.rerun()

        st.divider()

        # ── Audit Trail / Restore ──
        st.subheader("Audit Trail & Recovery")
        audit_c1, audit_c2 = st.columns(2)

        with audit_c1:
            st.markdown("**Change Log**")
            change_log_df = golf_db.get_change_log(session_id=None, limit=20)
            if not change_log_df.empty:
                st.dataframe(
                    change_log_df[["timestamp", "operation", "entity_type", "entity_id", "details"]],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No changes logged yet.")

        with audit_c2:
            st.markdown("**Restore Deleted Shots**")
            archived = golf_db.get_archived_shots(selected_session_id)
            if not archived.empty:
                st.warning(f"{len(archived)} archived shots from this session")
                st.dataframe(
                    archived[["shot_id", "deleted_at", "deleted_reason"]],
                    use_container_width=True,
                    hide_index=True,
                )
                restore_shots = st.multiselect("Restore", archived["shot_id"].tolist(), key="restore_select")
                if st.button("Restore Selected", key="restore_btn", type="primary"):
                    if restore_shots:
                        restored = golf_db.restore_deleted_shots(restore_shots)
                        st.success(f"Restored {restored} shots")
                        st.rerun()
            else:
                st.info("No archived shots for this session.")


# ================================================================
# TAB 2: MAINTENANCE (Data Quality + Sync)
# ================================================================
with tab_maintenance:
    if df.empty:
        render_no_data_state()
    else:
        st.header("Data Quality Tools")

        st.subheader("Outlier Detection")
        outliers_df = golf_db.find_outliers(selected_session_id)
        if not outliers_df.empty:
            st.warning(f"Found {len(outliers_df)} outlier shots")
            st.dataframe(outliers_df, use_container_width=True)
        else:
            st.success("No outliers detected!")

        st.divider()

        st.subheader("Data Validation")
        invalid_shots_df = golf_db.validate_shot_data(selected_session_id)
        if not invalid_shots_df.empty:
            st.warning(f"Found {len(invalid_shots_df)} shots with missing critical data")
            st.dataframe(invalid_shots_df, use_container_width=True)
        else:
            st.success("All shots have complete critical data!")

        st.divider()

        st.subheader("Club Naming Anomalies")

        def normalize_club_name(name):
            """Normalize club name for anomaly detection using canonical normalizer."""
            if not name:
                return ""
            return _normalizer.normalize(name).normalized.lower()

        club_variants = {}
        for cn in all_clubs:
            base = normalize_club_name(cn)
            club_variants.setdefault(base, set()).add(cn)

        anomaly_rows = [
            {"Base Club": b, "Variants": ", ".join(sorted(v)), "Count": len(v)}
            for b, v in club_variants.items()
            if len(v) > 1
        ]
        if anomaly_rows:
            st.warning(f"Found {len(anomaly_rows)} naming anomalies")
            st.dataframe(pd.DataFrame(anomaly_rows), use_container_width=True, hide_index=True)
        else:
            st.success("No club naming anomalies detected.")

        st.divider()

        st.subheader("Duplicate Detection")
        if st.button("Check for Duplicates", key="dedup_btn"):
            removed = golf_db.deduplicate_shots()
            if removed > 0:
                clear_all_caches()
                st.success(f"Removed {removed} duplicate shots")
                st.rerun()
            else:
                st.info("No duplicates found!")

    st.divider()

    # ── Sync Section ──
    st.header("Database Sync")

    sync_status = golf_db.get_sync_status()
    counts = sync_status["counts"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("SQLite Shots", counts["sqlite"])
    with col2:
        st.metric("Supabase Shots", counts.get("supabase", "N/A"))

    if sync_status.get("drift_exceeds"):
        st.warning(f"Drift: {sync_status['drift']} shots between SQLite and Supabase")
    else:
        st.success("Databases in sync")

    st.divider()

    st.subheader("Health")
    latest_import = observability.read_latest_event("import_runs.jsonl")
    if latest_import:
        st.caption(f"Last Import: {latest_import.get('status', 'unknown')}")
        st.caption(f"Shots: {latest_import.get('shots_imported', 0)}")
        st.caption(f"Duration: {latest_import.get('duration_sec', 0)}s")
    else:
        st.caption("Last Import: none")

    latest_sync = observability.read_latest_event("sync_runs.jsonl")
    if latest_sync:
        st.caption(f"Last Sync: {latest_sync.get('status', 'unknown')} ({latest_sync.get('mode', 'n/a')})")
        st.caption(f"Shots: {latest_sync.get('shots', 0)}")
        st.caption(f"Duration: {latest_sync.get('duration_sec', 0)}s")
    else:
        st.caption("Last Sync: none")

    st.divider()

    # Database stats
    st.subheader("Database Statistics")
    all_shots = golf_db.get_session_data(read_mode=read_mode)
    archived_count = len(golf_db.get_archived_shots())

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Total Sessions", len(all_sessions) if all_sessions else 0)
    s2.metric("Total Shots", len(all_shots))
    s3.metric("Current Session", len(df) if not df.empty else 0)
    s4.metric("Archived Shots", archived_count)
    s5.metric("Unique Clubs", len(all_clubs))


# ================================================================
# TAB 3: TAGS
# ================================================================
with tab_tags:
    if df.empty:
        render_no_data_state()
    else:
        st.header("Tags & Session Split")

        default_tags = ["Warmup", "Practice", "Round", "Fitting"]
        catalog_tags = golf_db.get_tag_catalog(read_mode=read_mode)
        catalog_tags = sorted({tag for tag in catalog_tags if tag})

        # ── Tag Catalog ──
        st.subheader("Tag Catalog")
        cat_c1, cat_c2 = st.columns(2)
        with cat_c1:
            st.markdown("**Available Tags**")
            st.write(", ".join(catalog_tags) if catalog_tags else "No tags yet.")
        with cat_c2:
            new_tag = st.text_input("New Tag", placeholder="e.g., Range Balls", key="new_catalog_tag")
            new_desc = st.text_input("Description (optional)", key="new_catalog_desc")
            if st.button("Add Tag", key="add_catalog_tag_btn"):
                if new_tag:
                    if golf_db.add_tag_to_catalog(new_tag, new_desc or None):
                        clear_all_caches()
                        st.success(f"Added '{new_tag}'")
                        st.rerun()

            deletable = [t for t in catalog_tags if t not in default_tags]
            del_tag = st.selectbox(
                "Delete Tag",
                deletable if deletable else ["No custom tags"],
                disabled=not deletable,
                key="delete_catalog_tag",
            )
            if st.button("Remove Tag", key="remove_catalog_tag_btn", disabled=not deletable):
                if golf_db.delete_tag_from_catalog(del_tag):
                    clear_all_caches()
                    st.success(f"Removed '{del_tag}'")
                    st.rerun()

        st.divider()

        # ── Quick Tagging ──
        st.subheader("Quick Tagging")

        qt_c1, qt_c2, qt_c3 = st.columns(3)
        with qt_c1:
            warmup_count = st.number_input(
                "Warmup shots (first N)",
                min_value=0, max_value=len(df),
                value=min(10, len(df)), step=1,
                key="warmup_count",
            )
        with qt_c2:
            tag_remaining = st.checkbox("Tag remaining as Practice", value=True, key="tag_remaining_practice")
        with qt_c3:
            overwrite_tags = st.checkbox("Overwrite existing tags", value=False, key="overwrite_tags")

        if st.button("Apply Quick Tags", key="apply_quick_tags_btn", type="primary"):
            tag_df = df.copy()
            if not overwrite_tags and "shot_tag" in tag_df.columns:
                tag_df = tag_df[(tag_df["shot_tag"].isna()) | (tag_df["shot_tag"] == "")]

            if tag_df.empty:
                st.warning("No untagged shots available.")
            else:
                if "date_added" in tag_df.columns:
                    tag_df = tag_df.sort_values("date_added")
                warmup_ids = tag_df.head(int(warmup_count))["shot_id"].tolist()
                remaining_ids = tag_df.iloc[int(warmup_count):]["shot_id"].tolist()
                updated = 0
                if warmup_ids:
                    updated += golf_db.update_shot_tags(warmup_ids, "Warmup")
                if tag_remaining and remaining_ids:
                    updated += golf_db.update_shot_tags(remaining_ids, "Practice")
                if updated > 0:
                    clear_all_caches()
                    st.success(f"Tagged {updated} shots")
                    st.rerun()

        st.divider()

        # ── Manual Tagging ──
        tag_c1, tag_c2 = st.columns(2)

        with tag_c1:
            st.subheader("Apply Tags")
            tag_club_filter = st.selectbox("Filter by Club", ["All"] + all_clubs, key="tag_club_filter")
            tag_df = df if tag_club_filter == "All" else df[df["club"] == tag_club_filter]
            shot_options = [
                f"{row['shot_id']} | {row['club']} | {row['carry']:.0f} yds"
                for _, row in tag_df.iterrows()
            ]
            selected_shots = st.multiselect("Select Shots", shot_options, key="tag_shots_select")
            tag_options = (catalog_tags or default_tags) + ["Custom"]
            tag_choice = st.selectbox("Tag", tag_options, key="tag_choice")
            custom_tag = st.text_input(
                "Custom Tag",
                disabled=tag_choice != "Custom",
                key="custom_tag_input",
            )
            if st.button("Apply Tag", key="apply_tag_btn", type="primary"):
                if selected_shots:
                    shot_ids = [item.split(" | ")[0] for item in selected_shots]
                    tag_value = custom_tag if tag_choice == "Custom" and custom_tag else tag_choice
                    updated = golf_db.update_shot_tags(shot_ids, tag_value)
                    clear_all_caches()
                    st.success(f"Tagged {updated} shots as '{tag_value}'")
                    st.rerun()

        with tag_c2:
            st.subheader("Split by Tag")
            available_tags = sorted([t for t in df.get("shot_tag", pd.Series()).dropna().unique()])
            sel_tag = st.selectbox(
                "Tag to Split",
                available_tags if available_tags else ["No tags yet"],
                disabled=not available_tags,
                key="split_tag_select",
            )
            split_new_id = st.text_input("New Session ID", key="split_tag_new_session")
            if st.button("Split", key="split_by_tag_btn", type="primary"):
                if not available_tags:
                    st.warning("Add tags first.")
                elif not split_new_id:
                    st.warning("Enter a new session ID.")
                else:
                    moved = golf_db.split_session_by_tag(selected_session_id, sel_tag, split_new_id)
                    clear_all_caches()
                    st.success(f"Moved {moved} shots to '{split_new_id}'")
                    st.rerun()

            st.divider()
            st.subheader("Delete Tagged Shots")
            del_tag_choice = st.selectbox(
                "Tag to Delete",
                available_tags if available_tags else ["No tags yet"],
                disabled=not available_tags,
                key="delete_tag_select",
            )
            confirm_del = st.checkbox("Confirm deletion", key="confirm_delete_tag")
            if st.button("Delete Tag", key="delete_tag_btn", disabled=not confirm_del):
                if available_tags:
                    deleted = golf_db.delete_shots_by_tag(selected_session_id, del_tag_choice)
                    clear_all_caches()
                    st.success(f"Deleted {deleted} shots tagged '{del_tag_choice}'")
                    st.rerun()


# ================================================================
# TAB 4: AUTOMATION (Sync + History)
# ================================================================
with tab_automation:
    from services.sync_service import (
        has_credentials, load_credentials, save_credentials,
        clear_credentials, run_sync, get_sync_history,
        get_automation_status, check_playwright_available,
    )

    st.header("Uneekor Sync")

    # ── Connection Status ──
    st.subheader("Connection")
    auto_status = get_automation_status()

    if auto_status['credentials_configured']:
        st.success(f"Configured — {auto_status['username']}")
        if auto_status.get('cookies_valid'):
            st.caption(f"Session cookies valid until {auto_status.get('cookies_expires', 'unknown')}")
        else:
            st.caption("No active session cookies (will login on next sync)")
        if st.button("Clear Credentials", key="clear_creds_btn"):
            clear_credentials()
            st.success("Credentials cleared.")
            st.rerun()
    else:
        st.warning("No credentials configured.")

    # ── Credential Form ──
    with st.expander("Update Credentials", expanded=not auto_status['credentials_configured']):
        with st.form("automation_creds_form"):
            existing = load_credentials()
            auto_user = st.text_input(
                "Uneekor Email",
                value=existing.get('username', '') if existing else '',
                key="auto_email",
            )
            auto_pass = st.text_input("Uneekor Password", type="password", key="auto_pass")
            if st.form_submit_button("Save Credentials", type="primary"):
                if auto_user and auto_pass:
                    save_credentials(auto_user, auto_pass)
                    st.success("Credentials saved.")
                    st.rerun()
                else:
                    st.error("Both email and password are required.")

    st.divider()

    # ── Sync Controls ──
    st.subheader("Sync Sessions")

    pw_ok, pw_msg = check_playwright_available()
    if not pw_ok:
        st.error(f"Sync unavailable: {pw_msg}")
        st.info("Install: `pip install playwright && playwright install chromium`")
    else:
        sync_c1, sync_c2 = st.columns([2, 1])
        with sync_c1:
            max_sessions_input = st.number_input(
                "Max sessions to import", min_value=1, max_value=50,
                value=10, step=5, key="auto_max_sessions",
            )
        with sync_c2:
            st.write("")  # vertical alignment spacer
            st.write("")
            run_sync_btn = st.button(
                "Run Sync", type="primary", use_container_width=True,
                key="auto_run_sync_btn", disabled=not has_credentials(),
            )

        if run_sync_btn:
            creds = load_credentials()
            if not creds:
                st.error("Configure credentials first.")
            else:
                with st.status("Syncing with Uneekor...", expanded=True) as status_ui:
                    status_text = st.empty()
                    sync_result = run_sync(
                        username=creds['username'],
                        password=creds['password'],
                        on_status=lambda msg: status_text.write(msg),
                        max_sessions=max_sessions_input,
                    )
                    if sync_result.success:
                        if sync_result.status == 'no_new_sessions':
                            status_ui.update(label="Already up to date", state="complete")
                            st.info("No new sessions found.")
                        else:
                            status_ui.update(label="Sync complete!", state="complete")
                            st.success(
                                f"Imported {sync_result.sessions_imported} session(s), "
                                f"{sync_result.total_shots} shots, "
                                f"{sync_result.dates_updated} dates updated."
                            )
                            clear_all_caches()
                            st.rerun()
                    else:
                        status_ui.update(label="Sync failed", state="error")
                        st.error(sync_result.error_message or "Sync failed.")
                        if sync_result.errors:
                            with st.expander("Error details"):
                                for err in sync_result.errors:
                                    st.code(err)

    st.divider()

    # ── Sync History ──
    st.subheader("Sync History")
    history = get_sync_history(limit=10)
    if history:
        history_rows = []
        for run in history:
            started = run.get('started_at', '')
            if isinstance(started, str) and len(started) > 19:
                started = started[:19]
            history_rows.append({
                "Status": run.get('status', 'unknown'),
                "Sessions": run.get('sessions_imported', 0),
                "Shots": run.get('total_shots', 0),
                "Failed": run.get('sessions_failed', 0),
                "Started": started,
            })
        st.dataframe(
            pd.DataFrame(history_rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No sync runs yet. Click 'Run Sync' to get started.")

    st.divider()

    # ── Recent Events ──
    st.subheader("Recent Sync Events")
    recent_syncs = observability.read_recent_events("sync_runs.jsonl", limit=5)
    if recent_syncs:
        for event in recent_syncs:
            ts = event.get('timestamp', '')[:19] if event.get('timestamp') else ''
            evt_status = event.get('status', 'unknown')
            shots = event.get('shots', 0)
            st.caption(f"{ts} | {evt_status} | {shots} shots")
    else:
        st.caption("No sync events logged yet.")


# ================================================================
# TAB 5: DISPLAY (relocated from sidebar)
# ================================================================
with tab_display:
    st.header("Display & Data Source")
    st.caption("Controls previously in the sidebar — now centralized here.")

    st.subheader("Data Source")
    render_data_source()

    st.divider()

    st.subheader("Sync Status")
    render_sync_status()

    st.divider()

    st.subheader("Layout")
    render_compact_toggle()
    render_mode_toggle()

    st.divider()

    st.subheader("Appearance")
    render_appearance_toggle()
