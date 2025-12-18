import streamlit as st
import pandas as pd
import golf_scraper
import golf_db

st.set_page_config(layout="wide", page_title="My Golf Lab")

# Initialize DB
golf_db.init_db()

# --- SIDEBAR ---
with st.sidebar:
    st.header("Import Data")
    uneekor_url = st.text_input("Paste Uneekor Report URL")
    
    if st.button("Run Import"):
        if uneekor_url:
            st.info("Starting import... Images will be downloaded to Cloud Storage.")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(msg):
                status_text.text(msg)

            # Run scraper
            result = golf_scraper.run_scraper(uneekor_url, update_progress)
            st.success(result)
            progress_bar.empty()
            status_text.empty()
        else:
            st.error("Please enter a valid URL")

# --- MAIN CONTENT ---
st.title("⛳ My Golf Data Lab")

# Fetch Data
unique_sessions = golf_db.get_unique_sessions()
# Create options using correct keys
session_options = [f"{s['session_id']} ({s.get('date_added', 'Unknown')})" for s in unique_sessions] if unique_sessions else []

if not session_options:
    st.info("No data yet. Import a report on the left to get started!")
    st.stop()

selected_session_str = st.selectbox("Select Session", session_options)
selected_session_id = selected_session_str.split(" ")[0]
df = golf_db.get_session_data(selected_session_id)

if df.empty:
    st.warning("Selected session has no data.")
    st.stop()


# --- TABS ---
tab1, tab2 = st.tabs(["Dashboard", "Shot Viewer"])

# TAB 1: DASHBOARD
with tab1:
    st.header("Performance Overview")
    
    # KPI Row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Shots", len(df))
    
    # Dynamic metrics based on available clubs
    unique_clubs = df['club'].unique()
    if len(unique_clubs) > 0:
        col2.metric(f"Avg Carry ({unique_clubs[0]})", f"{df[df['club']==unique_clubs[0]]['carry'].mean():.1f} yds")
    if len(unique_clubs) > 1:
        col3.metric(f"Avg Carry ({unique_clubs[1]})", f"{df[df['club']==unique_clubs[1]]['carry'].mean():.1f} yds")

    avg_smash = df[df['smash'] > 0]['smash'].mean()
    col4.metric("Avg Smash Factor", f"{avg_smash:.2f}" if avg_smash > 0 else "N/A")

    st.divider()

    # Charts
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Carry by Club")
        st.bar_chart(df, x='club', y='carry')
    
    with c2:
        st.subheader("Dispersion")
        st.scatter_chart(df, x='side_distance', y='carry')

# TAB 2: SHOT VIEWER
with tab2:
    st.header("Detailed Shot Analysis")
    
    # Grid View
    col_table, col_media = st.columns([1, 1])
    
    with col_table:
        st.write("Click a row to view details")
        # Display table with key metrics
        # Ensure column names match DB schema
        display_cols = ['club', 'carry', 'total', 'ball_speed', 'club_speed', 'smash', 'back_spin', 'side_spin']
        # Filter strictly
        valid_cols = [c for c in display_cols if c in df.columns]
        
        event = st.dataframe(
            df[valid_cols].round(1),
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True
        )

    with col_media:
        if len(event.selection.rows) > 0:
            selected_row_index = event.selection.rows[0]
            shot = df.iloc[selected_row_index]

            st.subheader(f"{shot['club']} - {shot['carry']:.1f} yds")

            # Display detailed shot metrics in columns
            m1, m2, m3 = st.columns(3)
            m1.metric("Ball Speed", f"{shot['ball_speed']:.1f} mph")
            m2.metric("Club Speed", f"{shot['club_speed']:.1f} mph")
            m3.metric("Smash", f"{shot['smash']:.2f}")

            m4, m5, m6 = st.columns(3)
            m4.metric("Launch", f"{shot['launch_angle']:.1f}°")
            m5.metric("Apex", f"{shot['apex']:.1f} yds")
            m6.metric("Flight Time", f"{shot['flight_time']:.1f}s")

            st.divider()

            # Images
            if shot.get('impact_img') or shot.get('swing_img'):
                img_col1, img_col2 = st.columns(2)

                if shot.get('impact_img'):
                    img_col1.image(shot['impact_img'], caption="Impact", use_container_width=True)
                else:
                    img_col1.info("No Impact Image")

                if shot.get('swing_img'):
                    img_col2.image(shot['swing_img'], caption="Swing View", use_container_width=True)
                else:
                    img_col2.info("No Swing Image")
            else:
                st.info("No images available for this shot.")