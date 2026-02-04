"""
My Golf Data Lab - Landing Page

A comprehensive golf analytics platform with local-first hybrid architecture.
"""
import streamlit as st
import golf_db
import observability
from services.data_access import get_unique_sessions, get_session_data, clear_all_caches
from utils.session_state import get_read_mode
from components import (
    render_shared_sidebar,
    render_documentation_links,
    render_no_data_state,
)
from utils.responsive import add_responsive_css

st.set_page_config(
    layout="wide",
    page_title="My Golf Lab",
    page_icon="⛳",
    initial_sidebar_state="expanded"
)

# Add responsive CSS
add_responsive_css()

# Initialize DB
golf_db.init_db()

# Get data using centralized access layer
read_mode = get_read_mode()
all_shots = get_session_data(read_mode=read_mode)
all_sessions = get_unique_sessions(read_mode=read_mode)

# Main landing page
st.title("My Golf Data Lab")
st.subheader("High-Altitude Golf Analysis Platform")

st.markdown("""
Welcome to your personal golf analytics platform! This app helps you analyze your shot data
from Uneekor launch monitors with advanced visualizations and AI-powered insights.
""")

st.divider()

# Quick stats overview
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Sessions", len(all_sessions) if all_sessions else 0)

with col2:
    st.metric("Total Shots", len(all_shots))

with col3:
    if 'club' in all_shots.columns:
        unique_clubs = all_shots['club'].nunique()
        st.metric("Unique Clubs", unique_clubs)
    else:
        st.metric("Unique Clubs", 0)

st.divider()

# Navigation cards
st.header("Quick Start")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Import Data")
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
    st.subheader("Dashboard")
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
    st.subheader("Database Manager")
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
col4 = st.columns(3)[0]

with col4:
    st.subheader("AI Coach")
    st.markdown("""
    Get personalized coaching with AI-powered analysis.

    **Features:**
    - Interactive chat coaching
    - Data-driven insights
    - Performance analysis
    - Function calling for live data access
    """)
    st.page_link("pages/4_🤖_AI_Coach.py", label="Go to AI Coach", icon="🤖", use_container_width=True)

st.divider()

# Recent activity
st.header("Recent Activity")

if all_sessions:
    recent_sessions = all_sessions[:5]

    for session in recent_sessions:
        session_id = session['session_id']
        date_added = session.get('date_added', 'Unknown')

        # Get shot count for this session
        session_data = get_session_data(session_id, read_mode=read_mode)
        shot_count = len(session_data)

        with st.expander(f"Session {session_id} - {date_added} ({shot_count} shots)"):
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
    render_no_data_state()

st.divider()

# Architecture info - UPDATED to reflect actual architecture
with st.expander("About This App"):
    st.markdown("""
    ## Architecture

    This is a **local-first hybrid architecture** golf analytics platform:

    ### Data Flow
    ```
    Uneekor Portal → Playwright Scraper → SQLite (local) → Supabase (cloud sync)
                                              ↓
                                        Streamlit Pages
                                              ↓
                                    Local Coach / Gemini AI
    ```

    ### Key Features
    - **Local-First**: All data stored in SQLite for offline access and privacy
    - **Cloud Sync**: Optional Supabase backup for multi-device access
    - **Automated Import**: Playwright-based scraper with rate limiting and checkpointing
    - **AI Insights**: Local ML models for offline analysis + Gemini API for advanced coaching

    ### Tech Stack
    - **UI**: Streamlit multi-page app with custom components
    - **Database**: SQLite (local, WAL mode) + Supabase (cloud sync)
    - **Automation**: Playwright browser automation with cookie persistence
    - **AI**: Local XGBoost/sklearn models + Google Gemini API

    ### Database Schema
    30+ fields per shot including:
    - Ball flight (speed, spin, launch angle, side distance)
    - Club data (path, face angle, attack angle, dynamic loft)
    - Impact location (Optix precise coordinates)
    - Shot classification, tags, and images

    ### Privacy & Data Ownership
    - All data stored locally by default
    - Cloud sync is optional and configurable
    - No data sent to third parties except when using Gemini AI

    For more details, see `CLAUDE.md` and `IMPROVEMENT_ROADMAP.md`.
    """)

# Sidebar - using shared component
render_shared_sidebar(
    show_navigation=False,  # We're on the landing page
    show_data_source=True,
    show_sync_status=True,
    current_page="home"
)

with st.sidebar:
    st.divider()
    render_documentation_links()

    st.divider()

    st.header("Health")
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
    st.caption("Built for high-altitude golf analysis")
