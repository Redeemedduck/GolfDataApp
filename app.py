import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
import golf_scraper
import golf_db

# Load environment variables
load_dotenv()

# AI availability checks
ANTHROPIC_AVAILABLE = False
GEMINI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = bool(os.getenv("ANTHROPIC_API_KEY"))
except ImportError:
    pass

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = bool(os.getenv("GEMINI_API_KEY"))
except ImportError:
    pass

st.set_page_config(layout="wide", page_title="My Golf Lab")

@st.cache_resource
def get_anthropic_client():
    """Get cached Anthropic client instance"""
    if not ANTHROPIC_AVAILABLE:
        return None
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        return anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        st.error(f"Failed to initialize Anthropic client: {e}")
        return None

@st.cache_resource
def get_gemini_client():
    """Get cached Gemini client instance"""
    if not GEMINI_AVAILABLE:
        return None
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        return genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Failed to initialize Gemini client: {e}")
        return None

def generate_session_summary(df):
    """Generate detailed session summary for AI context"""
    if df.empty:
        return "No data available."

    summary = f"""**Session Data Context:**
- Total Shots: {len(df)}
- Clubs: {', '.join(df['club'].unique())}
- Date Range: {df['date_added'].min() if 'date_added' in df.columns else 'Unknown'} to {df['date_added'].max() if 'date_added' in df.columns else 'Unknown'}

**Performance Metrics:**
"""

    # Group by club for detailed stats
    for club in df['club'].unique():
        club_data = df[df['club'] == club]
        summary += f"\n{club} ({len(club_data)} shots):\n"
        summary += f"  • Carry: {club_data['carry'].mean():.1f} ± {club_data['carry'].std():.1f} yds\n"
        summary += f"  • Ball Speed: {club_data['ball_speed'].mean():.1f} ± {club_data['ball_speed'].std():.1f} mph\n"
        summary += f"  • Club Speed: {club_data['club_speed'].mean():.1f} ± {club_data['club_speed'].std():.1f} mph\n"
        summary += f"  • Smash Factor: {club_data['smash'].mean():.2f} ± {club_data['smash'].std():.2f}\n"
        summary += f"  • Launch Angle: {club_data['launch_angle'].mean():.1f}° ± {club_data['launch_angle'].std():.1f}°\n"
        summary += f"  • Back Spin: {club_data['back_spin'].mean():.0f} ± {club_data['back_spin'].std():.0f} rpm\n"
        summary += f"  • Side Spin: {club_data['side_spin'].mean():.0f} ± {club_data['side_spin'].std():.0f} rpm\n"
        summary += f"  • Side Distance StdDev: {club_data['side_distance'].std():.1f} yds (consistency)\n"

    return summary

# Initialize DB
golf_db.init_db()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔗 Import Data")
    uneekor_url = st.text_input("Paste Uneekor Report URL")

    if st.button("Run Import", type="primary"):
        if uneekor_url:
            with st.status("Importing data...", expanded=True) as status:
                progress_messages = []

                def update_progress(msg):
                    progress_messages.append(msg)
                    st.write(f"✓ {msg}")

                try:
                    result = golf_scraper.run_scraper(uneekor_url, update_progress)
                    status.update(label="Import complete!", state="complete", expanded=False)
                    st.success(result)
                    st.rerun()
                except Exception as e:
                    status.update(label="Import failed", state="error", expanded=True)
                    st.error(f"Error: {str(e)}")
        else:
            st.error("Please enter a valid URL")

    st.divider()

    # --- Session Selector ---
    st.header("📊 Session")
    unique_sessions = golf_db.get_unique_sessions()
    session_options = [f"{s['session_id']} ({s.get('date_added', 'Unknown')})" for s in unique_sessions] if unique_sessions else []

    # Initialize variables
    has_data = False
    selected_session_id = None
    df = pd.DataFrame()
    all_clubs = []

    if session_options:
        has_data = True
        selected_session_str = st.selectbox("Select Session", session_options, label_visibility="collapsed")
        selected_session_id = selected_session_str.split(" ")[0]
        df = golf_db.get_session_data(selected_session_id)

        if not df.empty:
            # --- Club Filter ---
            st.header("🏌️ Filter by Club")
            all_clubs = df['club'].unique().tolist()
            selected_clubs = st.multiselect("Select Clubs", all_clubs, default=all_clubs, label_visibility="collapsed")

            if selected_clubs:
                df = df[df['club'].isin(selected_clubs)]
    else:
        st.info("No data yet. Import a report above to get started!")

# --- MAIN CONTENT ---
st.title("⛳ My Golf Data Lab")

# --- TABS ---
tab_names = ["📈 Dashboard", "🔍 Shot Viewer", "🛠️ Manage Data"]
if ANTHROPIC_AVAILABLE or GEMINI_AVAILABLE:
    tab_names.append("🤖 AI Coach")

tabs = st.tabs(tab_names)
tab1 = tabs[0]
tab2 = tabs[1]
tab3 = tabs[2]
tab4 = tabs[3] if len(tabs) > 3 else None

# TAB 1: DASHBOARD
with tab1:
    st.header("Performance Overview")

    if not has_data or df.empty:
        st.info("📊 No session data available. Import a report to see your performance metrics!")
    else:
        # KPI Row
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Shots", len(df))
        col2.metric("Avg Carry", f"{df['carry'].mean():.1f} yds" if len(df) > 0 else "N/A")
        col3.metric("Avg Total", f"{df['total'].mean():.1f} yds" if len(df) > 0 else "N/A")
        avg_smash = df[df['smash'] > 0]['smash'].mean()
        col4.metric("Avg Smash", f"{avg_smash:.2f}" if avg_smash > 0 else "N/A")
        col5.metric("Avg Ball Speed", f"{df['ball_speed'].mean():.1f} mph" if len(df) > 0 else "N/A")

        st.divider()

        # Charts Row
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Carry by Club")
            fig_carry = px.box(df, x='club', y='carry', color='club',
                               labels={'carry': 'Carry (yds)', 'club': 'Club'},
                               title="Carry Distance Distribution")
            fig_carry.update_layout(showlegend=False)
            st.plotly_chart(fig_carry, use_container_width=True)

        with c2:
            st.subheader("Dispersion Plot (Top-Down View)")
            fig_dispersion = go.Figure()

            # Add distance circles
            for dist in [50, 100, 150, 200, 250]:
                fig_dispersion.add_shape(type="circle",
                    xref="x", yref="y",
                    x0=-dist, y0=0, x1=dist, y1=dist*2,
                    line_color="lightgray", line_dash="dot"
                )

            # Add shot dots
            fig_dispersion.add_trace(go.Scatter(
                x=df['side_distance'],
                y=df['carry'],
                mode='markers',
                marker=dict(size=10, color=df['smash'], colorscale='Viridis', showscale=True, colorbar=dict(title="Smash")),
                text=df['club'],
                hovertemplate="<b>%{text}</b><br>Carry: %{y:.1f} yds<br>Side: %{x:.1f} yds<extra></extra>"
            ))

            fig_dispersion.update_layout(
                xaxis_title="Side Distance (yds)",
                yaxis_title="Carry Distance (yds)",
                xaxis=dict(range=[-50, 50], zeroline=True, zerolinewidth=2, zerolinecolor='green'),
                yaxis=dict(range=[0, df['carry'].max() * 1.1 if len(df) > 0 else 250]),
                height=500
            )
            st.plotly_chart(fig_dispersion, use_container_width=True)

# TAB 2: SHOT VIEWER
with tab2:
    st.header("Detailed Shot Analysis")

    if not has_data or df.empty:
        st.info("🔍 No session data available. Import a report to view detailed shot analysis!")
    else:
        # Grid View
        col_table, col_media = st.columns([1, 1])

        with col_table:
            st.write("Click a row to view details")
            display_cols = ['club', 'carry', 'total', 'ball_speed', 'club_speed', 'smash', 'back_spin', 'side_spin', 'face_angle', 'attack_angle']
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

                # Display detailed shot metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Ball Speed", f"{shot['ball_speed']:.1f} mph")
                m2.metric("Club Speed", f"{shot['club_speed']:.1f} mph")
                m3.metric("Smash", f"{shot['smash']:.2f}")

                m4, m5, m6 = st.columns(3)
                m4.metric("Launch", f"{shot['launch_angle']:.1f}°" if pd.notna(shot.get('launch_angle')) else "N/A")
                m5.metric("Face Angle", f"{shot['face_angle']:.1f}°" if pd.notna(shot.get('face_angle')) and shot.get('face_angle') != 0 else "N/A")
                m6.metric("Attack Angle", f"{shot['attack_angle']:.1f}°" if pd.notna(shot.get('attack_angle')) and shot.get('attack_angle') != 0 else "N/A")

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

# TAB 3: MANAGE DATA
with tab3:
    st.header("Data Management")

    if not has_data or df.empty:
        st.info("🛠️ No session data available. Import a report to manage your data!")
    else:
        st.caption("Clean up your session data by renaming clubs or deleting shots.")

        mgmt_col1, mgmt_col2 = st.columns(2)

        with mgmt_col1:
            st.subheader("Rename Club")
            rename_club = st.selectbox("Select Club to Rename", all_clubs, key="rename_select")
            new_name = st.text_input("New Club Name", key="new_name_input")
            if st.button("Rename", key="rename_btn"):
                if new_name:
                    golf_db.rename_club(selected_session_id, rename_club, new_name)
                    st.success(f"Renamed '{rename_club}' to '{new_name}'")
                    st.rerun()
                else:
                    st.warning("Please enter a new name.")

        with mgmt_col2:
            st.subheader("Delete Club from Session")
            delete_club = st.selectbox("Select Club to Delete", all_clubs, key="delete_club_select")
            st.warning(f"This will delete ALL shots for '{delete_club}' in this session.")
            if st.button("Delete All Shots for Club", key="delete_club_btn", type="primary"):
                golf_db.delete_club_session(selected_session_id, delete_club)
                st.success(f"Deleted all shots for '{delete_club}'")
                st.rerun()

        st.divider()

        st.subheader("Delete Individual Shot")
        if 'shot_id' in df.columns:
            shot_to_delete = st.selectbox("Select Shot ID to Delete", df['shot_id'].tolist(), key="delete_shot_select")
            if st.button("Delete Shot", key="delete_shot_btn"):
                golf_db.delete_shot(shot_to_delete)
                st.success(f"Deleted shot {shot_to_delete}")
                st.rerun()
        else:
            st.info("No shot IDs available for deletion.")

# TAB 4: AI COACH
if tab4:
    with tab4:
        st.header("🤖 AI Golf Coach")

        if not has_data or df.empty:
            st.info("🤖 No session data available. Import a report to start chatting with your AI golf coach!")
            st.markdown("""
            **The AI Coach will help you:**
            - Analyze your swing data with advanced metrics
            - Identify areas for improvement
            - Provide personalized drills and recommendations
            - Answer technical questions about your ball flight
            - Compare your stats to tour averages (altitude-adjusted for Denver)

            **Available AI Models:**
            - **Claude** (Anthropic): Conversational coaching style
            - **Gemini** (Google): Data analysis with code execution
            """)
        else:
            # Initialize chat history per session
            if "messages" not in st.session_state or st.session_state.get("current_session_id") != selected_session_id:
                st.session_state.messages = []
                st.session_state.current_session_id = selected_session_id

            # AI Model Selector
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("""
                Ask your AI coach questions about your swing data. The AI will analyze your shots and provide
                personalized coaching insights, drill recommendations, and answers to your golf questions.
                """)

            with col2:
                # Determine available models
                available_models = []
                if ANTHROPIC_AVAILABLE:
                    available_models.extend(["Claude Sonnet", "Claude Opus", "Claude Haiku"])
                if GEMINI_AVAILABLE:
                    available_models.extend(["Gemini Pro (Code)", "Gemini Flash"])

                if not available_models:
                    st.error("No AI models available. Set ANTHROPIC_API_KEY or GEMINI_API_KEY in .env")
                    st.stop()

                model_choice = st.selectbox(
                    "AI Model",
                    options=available_models,
                    index=0,
                    help="Claude: Conversational | Gemini: Code execution for data analysis"
                )

            # Model mapping
            model_configs = {
                "Claude Sonnet": ("anthropic", "claude-3-5-sonnet-latest"),
                "Claude Opus": ("anthropic", "claude-3-opus-latest"),
                "Claude Haiku": ("anthropic", "claude-3-5-haiku-latest"),
                "Gemini Pro (Code)": ("gemini", "gemini-2.0-flash-exp"),
                "Gemini Flash": ("gemini", "gemini-2.0-flash-exp")
            }

            ai_provider, model_id = model_configs[model_choice]
            use_code_execution = "Code" in model_choice

            # Display chat history
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Chat input
            if user_input := st.chat_input("Ask about your golf data... (e.g., 'Why am I pulling my driver left?')"):
                # Add user message
                st.session_state.messages.append({"role": "user", "content": user_input})

                with st.chat_message("user"):
                    st.markdown(user_input)

                # Generate session summary
                session_summary = generate_session_summary(df)

                # AI Response
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            if ai_provider == "anthropic":
                                # Claude API
                                client = get_anthropic_client()
                                if not client:
                                    st.error("Anthropic client not initialized. Check your API key.")
                                    st.stop()

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
- Compare to PGA Tour averages (altitude-adjusted)

**Key metrics:**
- Smash Factor: optimal 1.48-1.50 for driver, 1.38-1.40 for irons
- Launch: driver 9-14°, 7-iron 14-18°
- Spin: back spin for height, side spin for shot shape
- Club Path: in-to-out (+) vs out-to-in (-)
- Face Angle: open (+) vs closed (-)
- Attack Angle: ascending (+) for driver, descending (-) for irons

Provide coaching in a conversational, supportive tone."""

                                response = client.messages.create(
                                    model=model_id,
                                    max_tokens=2048,
                                    system=system_prompt,
                                    messages=st.session_state.messages
                                )

                                assistant_message = response.content[0].text

                            elif ai_provider == "gemini":
                                # Gemini API
                                client = get_gemini_client()
                                if not client:
                                    st.error("Gemini client not initialized. Check your API key.")
                                    st.stop()

                                # Prepare data as CSV for code execution
                                csv_data = df.to_csv(index=False)

                                prompt = f"""You are an expert Golf Data Analyst and coach.

**IMPORTANT: The golfer practices at Denver altitude (5,280 ft elevation):**
- Expect 10-15% more carry distance than sea level
- Lower spin rates due to thinner air
- Adjust your analysis and recommendations for high altitude

**Session Data (CSV format):**
```csv
{csv_data}
```

**User Question:**
{user_input}

**Instructions:**
{"Use your Python code execution capabilities to analyze this data deeply. Write and run code to calculate metrics, correlations, and patterns. Use print() to show your calculations." if use_code_execution else "Analyze this data and provide insights based on the metrics. Be specific and data-driven."}

Provide your analysis in a conversational coaching style with:
1. Direct answer to the question
2. Supporting data/statistics
3. Actionable recommendations
4. Comparison to PGA Tour averages (altitude-adjusted)
"""

                                config = types.GenerateContentConfig(
                                    tools=[{'code_execution': {}}] if use_code_execution else None,
                                    temperature=0.7
                                )

                                response = client.models.generate_content(
                                    model=model_id,
                                    contents=prompt,
                                    config=config
                                )

                                assistant_message = response.text

                            else:
                                st.error(f"Unknown AI provider: {ai_provider}")
                                st.stop()

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
                            st.error(f"AI Error: {str(e)}")
                            st.info(f"Provider: {ai_provider}, Model: {model_id}")
                            import traceback
                            with st.expander("Error Details"):
                                st.code(traceback.format_exc())

            # Sidebar controls
            with st.sidebar:
                st.divider()
                st.subheader("🤖 AI Coach Controls")

                if st.button("Clear Chat History"):
                    st.session_state.messages = []
                    st.rerun()

                if st.button("Quick Analysis"):
                    quick_prompt = f"Analyze this session and give me the top 3 things I should focus on:\n\n{generate_session_summary(df)}"
                    st.session_state.messages.append({"role": "user", "content": quick_prompt})
                    st.rerun()

                st.info("""
                **Example Questions:**
                - Why am I pulling my driver left?
                - How can I improve my consistency?
                - What's causing my slice?
                - Compare my stats to tour average
                - What drill should I work on?
                - Analyze my spin axis patterns
                """)
