import streamlit as st
import pandas as pd
import os
import golf_scraper
import golf_db

# Import anthropic at module level for efficiency
try:
    import anthropic
    ANTHROPIC_AVAILABLE = bool(os.getenv("ANTHROPIC_API_KEY"))
except ImportError:
    ANTHROPIC_AVAILABLE = False

st.set_page_config(layout="wide", page_title="My Golf Lab")

@st.cache_resource
def get_anthropic_client():
    """
    Get cached Anthropic client instance

    Uses Streamlit's cache_resource to avoid recreating the client
    on every interaction, improving performance.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)

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
tab_names = ["Dashboard", "Shot Viewer"]
if ANTHROPIC_AVAILABLE:
    tab_names.append("AI Coach")

tabs = st.tabs(tab_names)
tab1 = tabs[0]
tab2 = tabs[1]
tab3 = tabs[2] if len(tabs) > 2 else None

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

# TAB 3: AI COACH (if Anthropic API key is available)
if tab3:
    with tab3:
        st.header("AI Golf Coach")

        # Initialize chat history in session state, tied to current session
        # Reset chat when user switches to a different session
        if "messages" not in st.session_state or st.session_state.get("current_session_id") != selected_session_id:
            st.session_state.messages = []
            st.session_state.current_session_id = selected_session_id

        # Model selector
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("""
            Ask your AI coach questions about your swing data. Claude will analyze your shots and provide
            personalized coaching insights, drill recommendations, and answers to your golf questions.
            """)
        with col2:
            model_choice = st.selectbox(
                "Model",
                options=["Sonnet (Balanced)", "Opus (Best)", "Haiku (Fast)"],
                index=0,
                help="Sonnet: Best for most uses | Opus: Deep analysis | Haiku: Quick answers"
            )

        model_map = {
            "Sonnet (Balanced)": "claude-sonnet-4.5",
            "Opus (Best)": "claude-opus-4",
            "Haiku (Fast)": "claude-haiku-4"
        }
        selected_model = model_map[model_choice]

        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if user_input := st.chat_input("Ask about your golf data... (e.g., 'Why am I pulling my driver left?')"):
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.chat_message("user"):
                st.markdown(user_input)

            # Prepare context from current session data
            session_summary = f"""
**Session Data Context:**
- Club: {df['club'].iloc[0] if len(df) > 0 else 'Unknown'}
- Total Shots: {len(df)}
- Avg Carry: {df['carry'].mean():.1f} yards
- Avg Ball Speed: {df['ball_speed'].mean():.1f} mph
- Avg Club Speed: {df['club_speed'].mean():.1f} mph
- Avg Smash: {df['smash'].mean():.2f}
- Avg Launch: {df['launch_angle'].mean():.1f}°
- Avg Back Spin: {df['back_spin'].mean():.0f} rpm
- Avg Side Spin: {df['side_spin'].mean():.0f} rpm

**Shot Dispersion:**
- Side Distance Std Dev: {df['side_distance'].std():.1f} yards
- Carry Std Dev: {df['carry'].std():.1f} yards
"""

            # Call Claude API
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        # Get cached client instance
                        client = get_anthropic_client()

                        if not client:
                            st.error("Anthropic client not available. Check your API key.")
                            st.stop()

                        # Build system prompt with session data context
                        # This ensures the AI always has the current session's data
                        system_prompt = f"""You are an expert golf coach with 20+ years of experience analyzing launch monitor data.

The golfer is practicing at Denver altitude (5,280 ft), which affects ball flight:
- 10-15% more carry distance than sea level
- Lower spin rates due to air density
- Less ball roll due to altitude

**Current Session Data:**
{session_summary}

**Your coaching style:**
- Encouraging but honest
- Specific and data-driven
- Focused on actionable drills
- Ask clarifying questions when needed
- Compare to PGA Tour averages (altitude-adjusted)

**Key metrics to understand:**
- Smash Factor: ball speed / club speed (optimal: 1.48-1.50 for driver, 1.38-1.40 for irons)
- Launch: optimal varies by club (driver: 9-14°, 7-iron: 14-18°)
- Spin: back spin for height/control, side spin for shot shape
- Club Path: in-to-out (positive) vs out-to-in (negative)
- Face Angle: open (positive) vs closed (negative)
- Attack Angle: ascending (positive) for driver, descending (negative) for irons

Provide coaching in a conversational, supportive tone. Reference the session data when relevant."""

                        # Use conversation history directly
                        # The session context is now in the system prompt, so we don't need to include it in messages
                        messages = st.session_state.messages

                        # Call Claude
                        response = client.messages.create(
                            model=selected_model,
                            max_tokens=2048,
                            system=system_prompt,
                            messages=messages
                        )

                        assistant_message = response.content[0].text

                        # Display response
                        st.markdown(assistant_message)

                        # Add to chat history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": assistant_message
                        })

                    except anthropic.APIError as e:
                        st.error(f"Claude API Error: {e}")
                        st.info("Check your ANTHROPIC_API_KEY and account status")
                    except Exception as e:
                        st.error(f"Error communicating with Claude: {e}")
                        st.info("Make sure ANTHROPIC_API_KEY is set in your .env file")

        # Sidebar with quick actions
        with st.sidebar:
            st.divider()
            st.subheader("AI Coach Controls")

            if st.button("Clear Chat History"):
                st.session_state.messages = []
                st.rerun()

            if st.button("Quick Analysis"):
                quick_prompt = f"Analyze this session data and give me the top 3 things I should focus on:\n\n{session_summary}"
                st.session_state.messages.append({"role": "user", "content": quick_prompt})
                st.rerun()

            st.info("""
            **Example Questions:**
            - Why am I pulling my driver left?
            - How can I improve my consistency?
            - What's causing my slice?
            - Compare my stats to tour average
            - What drill should I work on?
            """)