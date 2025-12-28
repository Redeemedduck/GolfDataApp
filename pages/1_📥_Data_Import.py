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

st.set_page_config(layout="wide", page_title="Data Import - My Golf Lab")

# Initialize DB
golf_db.init_db()

st.title("📥 Import Golf Data")

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

    if st.button("🚀 Run Import", type="primary", use_container_width=True):
        if uneekor_url:
            st.info("Starting import...")

            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(msg):
                status_text.text(msg)

            # Run scraper
            result = golf_scraper.run_scraper(uneekor_url, update_progress)

            progress_bar.empty()
            status_text.empty()

            st.success(result)

            # Show success message with next steps
            st.balloons()
            st.info("✅ Import complete! Go to the **Dashboard** page to view your data.")

        else:
            st.error("Please enter a valid Uneekor URL")

with col2:
    st.subheader("Import History")

    # Show recent sessions
    unique_sessions = golf_db.get_unique_sessions()

    if unique_sessions:
        st.write(f"**{len(unique_sessions)} sessions** in database")

        # Display last 5 imports
        recent_sessions = unique_sessions[:5]
        for session in recent_sessions:
            st.caption(f"📊 {session['session_id']} - {session.get('date_added', 'Unknown')}")
    else:
        st.info("No sessions imported yet")

st.divider()

# Instructions section
with st.expander("📖 How to Import Data"):
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

# Database stats in sidebar
with st.sidebar:
    st.header("📊 Database Stats")

    # Get total shot count
    all_shots = golf_db.get_session_data()
    total_shots = len(all_shots)

    st.metric("Total Shots", total_shots)
    st.metric("Total Sessions", len(unique_sessions) if unique_sessions else 0)

    if total_shots > 0:
        # Show clubs in database
        if 'club' in all_shots.columns:
            unique_clubs = all_shots['club'].nunique()
            st.metric("Unique Clubs", unique_clubs)
