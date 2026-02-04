"""
Data Import Page - Fetch shot data from Uneekor API
"""
import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import golf_scraper
import golf_db
import observability
from services.data_access import get_unique_sessions, get_session_data, clear_all_caches
from utils.session_state import get_read_mode
from utils.responsive import add_responsive_css
from components import render_shared_sidebar

st.set_page_config(layout="wide", page_title="Data Import - My Golf Lab")

# Add responsive CSS
add_responsive_css()

# Initialize DB
golf_db.init_db()

# Get read mode
read_mode = get_read_mode()

st.title("Import Golf Data")

st.markdown("""
Import your golf shot data from Uneekor reports. Simply paste the URL from your Uneekor session
and click **Run Import** to fetch all shots and save them to your local database.
""")

st.divider()

# Main import section
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Import from Uneekor URL")

    uneekor_url = st.text_input(
        "Paste Uneekor Report URL",
        placeholder="https://myuneekor.com/report?id=12345&key=abc123...",
        help="Copy the full URL from your Uneekor report page"
    )

    if st.button("Run Import", type="primary", use_container_width=True):
        if uneekor_url:
            st.info("Starting import...")

            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(msg):
                status_text.text(msg)

            # Run scraper
            result = golf_scraper.run_scraper(uneekor_url, update_progress)
            clear_all_caches()

            progress_bar.empty()
            status_text.empty()

            # Handle result (now returns dict with status and message)
            if result.get('status') == 'success':
                st.success(f"✅ {result.get('message', 'Import complete!')}")
                st.balloons()
                st.info("Go to the **Dashboard** page to view your data.")
            else:
                st.error(f"❌ Import failed: {result.get('message', 'Unknown error')}")
            report_id, _ = golf_scraper.extract_url_params(uneekor_url)
            invalid_shots_df = golf_db.validate_shot_data(session_id=report_id)
            if not invalid_shots_df.empty:
                st.warning(
                    f"⚠️ Found {len(invalid_shots_df)} shots missing critical fields in this import."
                )

        else:
            st.error("Please enter a valid Uneekor URL")

with col2:
    st.subheader("Import History")

    # Show recent sessions
    unique_sessions = get_unique_sessions(read_mode=read_mode)

    if unique_sessions:
        st.write(f"**{len(unique_sessions)} sessions** in database")

        # Display last 5 imports
        recent_sessions = unique_sessions[:5]
        for session in recent_sessions:
            # Prefer session_date (actual session date) over date_added (import timestamp)
            display_date = session.get('session_date') or session.get('date_added', 'Unknown')
            if display_date and display_date != 'Unknown' and hasattr(display_date, 'strftime'):
                display_date = display_date.strftime('%Y-%m-%d')
            st.caption(f"📊 {session['session_id']} - {display_date}")
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
                "timestamp": item.get("timestamp", ""),
            }
            for item in recent_imports
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.caption("No import runs logged yet")

st.divider()

# Instructions section
with st.expander("How to Import Data"):
    st.markdown("""
    ### Step-by-Step Instructions

    1. **Log in to your Uneekor account** at [myuneekor.com](https://myuneekor.com)
    2. **Find your practice session** in the reports section
    3. **Copy the full URL** from your browser's address bar
    4. **Paste the URL** in the input field above
    5. **Click "Run Import"** to fetch all shots

    ### What Gets Imported?

    The import process will fetch:
    - ✅ All shots from all clubs in the session
    - ✅ Ball flight data (speed, spin, angles)
    - ✅ Club data (path, face angle, attack angle)
    - ✅ Impact location (Optix data)
    - ✅ Shot images (impact & swing views)

    ### Where Is Data Stored?

    - **Local**: SQLite database (`golf_stats.db`) for offline access
    - **Cloud**: Supabase (optional backup if configured)
    - **Images**: Stored in Supabase Storage with public URLs

    ### Troubleshooting

    - **"Could not extract report ID"**: Make sure you copied the complete URL including `?id=` and `&key=` parameters
    - **"No data found"**: The session may be empty or the URL may have expired
    - **Images missing**: Some sessions may not have images available from Uneekor
    """)

# Sidebar - using shared component
render_shared_sidebar(
    show_navigation=True,
    show_data_source=True,
    show_sync_status=True,
    current_page="import"
)

# Additional sidebar content
with st.sidebar:
    st.divider()
    st.header("Stats")

    # Get total shot count
    all_shots = get_session_data(read_mode=read_mode)
    total_shots = len(all_shots)

    st.metric("Total Shots", total_shots)
    st.metric("Total Sessions", len(unique_sessions) if unique_sessions else 0)

    if total_shots > 0:
        # Show clubs in database
        if 'club' in all_shots.columns:
            unique_clubs = all_shots['club'].nunique()
            st.metric("Unique Clubs", unique_clubs)

    st.divider()
    st.header("Health")
    latest_import = observability.read_latest_event("import_runs.jsonl")
    if latest_import:
        st.caption(f"Last Import: {latest_import.get('status', 'unknown')}")
        st.caption(f"Shots: {latest_import.get('shots_imported', 0)}")
        st.caption(f"Duration: {latest_import.get('duration_sec', 0)}s")
    else:
        st.caption("Last Import: none")
