"""
My Golf Data Lab - Landing Page

A comprehensive golf analytics platform with local-first hybrid architecture.
"""
import streamlit as st
import golf_db

st.set_page_config(
    layout="wide",
    page_title="My Golf Lab",
    page_icon="⛳",
    initial_sidebar_state="expanded"
)

# Initialize DB
golf_db.init_db()

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

all_shots = golf_db.get_session_data()
all_sessions = golf_db.get_unique_sessions()

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

st.divider()

# Recent activity
st.header("📅 Recent Activity")

if all_sessions:
    recent_sessions = all_sessions[:5]

    for session in recent_sessions:
        session_id = session['session_id']
        date_added = session.get('date_added', 'Unknown')

        # Get shot count for this session
        session_data = golf_db.get_session_data(session_id)
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

    st.header("⚙️ System Status")
    st.success("✅ SQLite Database: Connected")

    # Check Supabase connection
    if golf_db.supabase:
        st.success("✅ Supabase: Connected")
    else:
        st.warning("⚠️ Supabase: Not configured")

    st.divider()

    st.caption("Golf Data Lab v2.0 - Multi-Page Architecture")
    st.caption("Built with ❤️ for high-altitude golf analysis")
