"""
My Golf Data Lab - Landing Page

A comprehensive golf analytics platform with local-first hybrid architecture.
"""
import streamlit as st
import golf_db
import observability

st.set_page_config(
    layout="wide",
    page_title="My Golf Lab",
    page_icon="⛳",
    initial_sidebar_state="expanded"
)

# Initialize DB
golf_db.init_db()

# Cached data access
@st.cache_data(show_spinner=False)
def get_unique_sessions_cached(read_mode="auto"):
    return golf_db.get_unique_sessions(read_mode=read_mode)

@st.cache_data(show_spinner=False)
def get_session_data_cached(session_id=None, read_mode="auto"):
    return golf_db.get_session_data(session_id, read_mode=read_mode)

@st.cache_data(show_spinner=False)
def get_filtered_shots_cached(quality='clean', exclude_warmup=True, read_mode="auto"):
    return golf_db.get_filtered_shots(quality=quality, exclude_warmup=exclude_warmup, read_mode=read_mode)

# Main landing page
st.title("⛳ My Golf Data Lab")
st.subheader("High-Altitude Golf Analysis Platform")

st.markdown("""
Welcome to your personal golf analytics platform! This app helps you analyze your shot data
from Uneekor launch monitors with advanced visualizations and AI-powered insights.
""")

st.divider()

# Quick stats overview
col1, col2, col3 = st.columns(3)

read_mode = st.session_state.get("read_mode", "auto")
all_shots = get_session_data_cached(read_mode=read_mode)
filtered_shots = get_filtered_shots_cached(read_mode=read_mode)
all_sessions = get_unique_sessions_cached(read_mode=read_mode)

with col1:
    st.metric("Total Sessions", len(all_sessions) if all_sessions else 0)

with col2:
    st.metric("Analytics-Ready Shots", len(filtered_shots),
              help=f"{len(all_shots)} total — excludes warmup & flagged shots")

with col3:
    if 'club' in filtered_shots.columns:
        unique_clubs = filtered_shots['club'].nunique()
        st.metric("Unique Clubs", unique_clubs)
    else:
        st.metric("Unique Clubs", 0)

st.divider()

# Navigation cards
st.header("🚀 Quick Start")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📥 Import Data")
    st.markdown("""
    Import your golf shot data from Uneekor reports.

    **Features:**
    - Paste Uneekor URL to import
    - Automatic shot data extraction
    - Image download & storage
    - Local & cloud sync
    """)
    st.page_link("pages/1_📥_Data_Import.py", label="Go to Import", icon="📥", use_container_width=True)

with col2:
    st.subheader("📊 Dashboard")
    st.markdown("""
    View performance analytics and visualizations.

    **Features:**
    - Performance metrics (KPIs)
    - Carry distance charts
    - Dispersion plots
    - Shot-by-shot viewer
    """)
    st.page_link("pages/2_📊_Dashboard.py", label="Go to Dashboard", icon="📊", use_container_width=True)

with col3:
    st.subheader("🗄️ Database Manager")
    st.markdown("""
    Manage your golf data with CRUD operations.

    **Features:**
    - Rename clubs
    - Delete shots/sessions
    - Data quality checks
    - Sync status monitoring
    """)
    st.page_link("pages/3_🗄️_Database_Manager.py", label="Go to Manager", icon="🗄️", use_container_width=True)

# Second row for AI Coach
col4 = st.columns(3)[0]  # Only use first column for centered card

with col4:
    st.subheader("🤖 AI Coach")
    st.markdown("""
    Get personalized coaching with Gemini 3.0 AI.

    **Features:**
    - Interactive chat coaching
    - Data-driven insights
    - Performance analysis
    - Function calling for live data access
    """)
    st.page_link("pages/4_🤖_AI_Coach.py", label="Go to AI Coach", icon="🤖", use_container_width=True)

st.divider()

# Recent activity
st.header("📅 Recent Activity")

if all_sessions:
    recent_sessions = all_sessions[:5]

    for session in recent_sessions:
        session_id = session['session_id']
        date_added = session.get('date_added', 'Unknown')

        # Get shot count for this session
        session_data = get_session_data_cached(session_id)
        shot_count = len(session_data)

        with st.expander(f"📊 Session {session_id} - {date_added} ({shot_count} shots)"):
            if not session_data.empty and 'club' in session_data.columns:
                clubs = session_data['club'].unique()
                st.write(f"**Clubs**: {', '.join(clubs)}")

                # Show quick stats
                if shot_count > 0:
                    avg_carry = session_data['carry'].mean()
                    avg_smash = session_data[session_data['smash'] > 0]['smash'].mean()

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Shots", shot_count)
                    col2.metric("Avg Carry", f"{avg_carry:.1f} yds" if avg_carry > 0 else "N/A")
                    col3.metric("Avg Smash", f"{avg_smash:.2f}" if avg_smash > 0 else "N/A")
else:
    st.info("No sessions yet. Import your first session to get started!")
    st.page_link("pages/1_📥_Data_Import.py", label="Import First Session", icon="📥")

st.divider()

# Architecture info
with st.expander("ℹ️ About This App"):
    st.markdown("""
    ## Architecture

    This is a **local-first hybrid architecture** golf analytics platform:

    ### Data Flow
    ```
    Uneekor API → SQLite (local) → Supabase (cloud backup) → BigQuery (warehouse) → Gemini AI
    ```

    ### Key Features
    - **Local-First**: All data stored in SQLite for offline access
    - **Cloud Sync**: Optional Supabase backup for multi-device access
    - **Advanced Analytics**: BigQuery data warehouse for complex queries
    - **AI Insights**: Gemini API for personalized coaching

    ### Tech Stack
    - **UI**: Streamlit multi-page app
    - **Database**: SQLite (local), Supabase (cloud), BigQuery (warehouse)
    - **API**: Uneekor REST API for data fetching
    - **AI**: Google Gemini API for analysis

    ### Database Schema
    30+ fields per shot including:
    - Ball flight (speed, spin, angles)
    - Club data (path, face angle, attack angle)
    - Impact location (Optix precise data)
    - Shot classification & images

    For more details, see `CLAUDE.md` and `IMPROVEMENT_ROADMAP.md`.
    """)

# Sidebar
with st.sidebar:
    st.header("📖 Documentation")
    st.markdown("""
    - [Main README](README.md)
    - [Setup Guide](SETUP_GUIDE.md)
    - [Pipeline Docs](PIPELINE_COMPLETE.md)
    - [Roadmap](IMPROVEMENT_ROADMAP.md)
    """)

    st.divider()

    st.header("🧭 Data Source")
    if "read_mode" not in st.session_state:
        st.session_state.read_mode = "auto"
    read_mode_options = {
        "Auto (SQLite first)": "auto",
        "SQLite": "sqlite",
        "Supabase": "supabase"
    }
    selected_label = st.selectbox(
        "Read Mode",
        list(read_mode_options.keys()),
        index=list(read_mode_options.values()).index(st.session_state.read_mode),
        help="Auto uses SQLite when available and falls back to Supabase if empty."
    )
    selected_mode = read_mode_options[selected_label]
    if selected_mode != st.session_state.read_mode:
        st.session_state.read_mode = selected_mode
        golf_db.set_read_mode(selected_mode)
        st.cache_data.clear()

    st.header("⚙️ System Status")
    st.success("✅ SQLite Database: Connected")
    st.info(f"📌 Data Source: {golf_db.get_read_source()}")

    # Check Supabase connection
    if golf_db.supabase:
        st.success("✅ Supabase: Connected")
    else:
        st.warning("⚠️ Supabase: Not configured")

    sync_status = golf_db.get_sync_status()
    counts = sync_status["counts"]
    st.caption(f"SQLite shots: {counts['sqlite']}")
    if golf_db.supabase:
        st.caption(f"Supabase shots: {counts['supabase']}")
        if sync_status["drift_exceeds"]:
            st.warning(f"⚠️ SQLite/Supabase drift: {sync_status['drift']} shots")

    st.divider()

    st.header("🩺 Health")
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

    st.caption("Golf Data Lab v2.0 - Multi-Page Architecture")
    st.caption("Built with ❤️ for high-altitude golf analysis")
