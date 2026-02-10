"""
🤖 AI Coach - Cloud-Native Golf Coaching with Modular Providers

This page provides an interactive AI coaching experience with modular AI providers.
The AI coach can query your golf data using function calling and provide personalized insights.

Features:
- Multi-turn conversations with context awareness
- Dynamic data access through function calling
- Model selection per provider (Flash for speed, Pro for complex reasoning)
- Thinking level control for response depth
- Function call transparency
"""

import streamlit as st
from datetime import datetime
import json
import golf_db
from services.ai import list_providers, get_provider
from components import render_retraining_ui

# Import ML components for model status (graceful degradation)
try:
    from ml.train_models import get_model_info, DISTANCE_MODEL_PATH
except ImportError:
    get_model_info = None
    DISTANCE_MODEL_PATH = None


# Page config
st.set_page_config(
    page_title="AI Coach",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Golf Coach")
st.markdown("*Powered by modular AI providers with function calling*")

# Initialize database
golf_db.init_db()

# Cached data access
@st.cache_data(show_spinner=False)
def get_all_shots_cached(read_mode="auto"):
    return golf_db.get_all_shots(read_mode=read_mode)

@st.cache_data(show_spinner=False)
def get_sessions_cached(read_mode="auto"):
    return golf_db.get_unique_sessions(read_mode=read_mode)

@st.cache_data(show_spinner=False)
def get_session_data_cached(session_id=None, read_mode="auto"):
    return golf_db.get_session_data(session_id, read_mode=read_mode)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Coach Settings")
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

    st.info(f"📌 Data Source: {golf_db.get_read_source()}")
    sync_status = golf_db.get_sync_status()
    counts = sync_status["counts"]
    st.caption(f"SQLite shots: {counts['sqlite']}")
    if golf_db.supabase:
        st.caption(f"Supabase shots: {counts['supabase']}")
        if sync_status["drift_exceeds"]:
            st.warning(f"⚠️ SQLite/Supabase drift: {sync_status['drift']} shots")

    st.header("🧠 AI Provider")
    providers = list_providers()
    if not providers:
        st.error("No AI providers registered.")
        st.stop()

    provider_labels = {spec.display_name: spec.provider_id for spec in providers}
    selected_provider_label = st.selectbox(
        "Provider",
        list(provider_labels.keys()),
        index=0
    )
    selected_provider_id = provider_labels[selected_provider_label]
    provider_spec = get_provider(selected_provider_id)
    provider_cls = provider_spec.provider_cls
    provider_ready = True
    if hasattr(provider_cls, "is_configured") and not provider_cls.is_configured():
        provider_ready = False
        st.warning("AI provider not configured. AI coach is disabled.")

    # Model selection
    st.subheader("Model Selection")
    model_options = getattr(provider_cls, "MODEL_OPTIONS", {"Default": "default"})

    selected_model = st.selectbox(
        "Choose Model",
        options=list(model_options.keys()),
        index=0,
        help="Flash: Faster, cost-effective ($0.50/1M in)\nPro: Complex reasoning, agentic workflows"
    )

    # Thinking level
    st.subheader("Thinking Depth")
    thinking_level = st.select_slider(
        "Reasoning Intensity",
        options=['minimal', 'low', 'medium', 'high'],
        value='medium',
        help="Higher levels provide more detailed reasoning but take longer"
    )

    st.divider()
    st.subheader("🎯 Analysis Focus")
    sessions = get_sessions_cached(read_mode=st.session_state.read_mode)
    session_options = [("All Sessions", None)]
    for session in sessions:
        # Prefer session_date (actual session date) over date_added (import timestamp)
        display_date = session.get('session_date') or session.get('date_added', 'Unknown')
        if display_date and display_date != 'Unknown':
            try:
                if hasattr(display_date, 'strftime'):
                    display_date = display_date.strftime('%Y-%m-%d')
                elif isinstance(display_date, str) and len(display_date) > 10:
                    display_date = display_date[:10]  # Truncate timestamp to date
            except:
                pass
        label = f"{session.get('session_id')} ({display_date})"
        if session.get('session_type'):
            label = f"{label} [{session.get('session_type')}]"
        session_options.append((label, session.get('session_id')))

    selected_session_label = st.selectbox(
        "Focus Session",
        [label for label, _ in session_options],
        index=0
    )
    focus_session_id = dict(session_options).get(selected_session_label)

    session_types = sorted({
        session.get('session_type') for session in sessions if session.get('session_type')
    })
    focus_session_type = st.selectbox(
        "Focus Session Type",
        ["All Types"] + session_types,
        index=0
    )

    focus_df = (
        get_session_data_cached(focus_session_id, read_mode=st.session_state.read_mode)
        if focus_session_id
        else get_all_shots_cached(read_mode=st.session_state.read_mode)
    )
    club_options = sorted(focus_df['club'].dropna().unique().tolist()) if not focus_df.empty else []
    focus_club = st.selectbox(
        "Focus Club",
        ["All Clubs"] + club_options,
        index=0
    )

    tag_catalog = golf_db.get_tag_catalog(read_mode=st.session_state.read_mode)
    focus_tag = st.selectbox(
        "Focus Tag",
        ["All Tags"] + tag_catalog,
        index=0
    )

    # Reset conversation
    st.divider()
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.coach = None
        st.rerun()

    # Show data stats
    st.divider()
    st.subheader("📊 Your Data")
    df = get_all_shots_cached(read_mode=st.session_state.read_mode)
    if not df.empty:
        st.metric("Total Shots", len(df))
        st.metric("Sessions", df['session_id'].nunique())
        st.metric("Clubs", df['club'].nunique())
    else:
        st.warning("No shot data available. Import data first!")

    # ML Model section
    st.divider()
    st.subheader("🤖 ML Model")

    # Show compact model status
    if get_model_info and DISTANCE_MODEL_PATH:
        try:
            from pathlib import Path
            if Path(DISTANCE_MODEL_PATH).exists():
                metadata = get_model_info(DISTANCE_MODEL_PATH)
                if metadata:
                    mae = metadata.metrics.get('mae', 0)
                    st.caption(f"Model: v{metadata.version}, MAE: {mae:.1f}yd")
                else:
                    st.caption("Model exists (no metadata)")
            else:
                st.caption("No model trained")
        except Exception:
            st.caption("Model status unavailable")
    else:
        st.caption("ML not available")

    # Retrain button
    if st.button("⚙️ Manage Model", key="sidebar_retrain", use_container_width=True):
        st.session_state.show_retrain = True

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'coach_key' not in st.session_state:
    st.session_state.coach_key = None

if 'coach' not in st.session_state:
    st.session_state.coach = None

model_type = model_options[selected_model]
coach_key = f"{selected_provider_id}:{model_type}:{thinking_level}"

if not provider_ready:
    st.session_state.coach = None
else:
    if st.session_state.coach is None or st.session_state.coach_key != coach_key:
        try:
            st.session_state.coach = provider_cls(
                model_type=model_type,
                thinking_level=thinking_level
            )
            st.session_state.coach_key = coach_key
            st.session_state.messages = []
        except Exception as e:
            st.error(f"Failed to initialize AI Coach: {str(e)}")
            st.stop()

if not provider_ready:
    st.info("AI coach is disabled until the provider is configured.")
    st.stop()

# Main chat interface
st.subheader("💬 Chat with Your Coach")

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Check if message contains a practice plan
        has_practice_plan = (
            message.get("data") and
            isinstance(message["data"], dict) and
            'plan' in message["data"]
        )

        if has_practice_plan:
            # Render practice plan visually
            render_practice_plan(message["data"]["plan"])
        else:
            # Display standard message content
            st.markdown(message["content"])

        # Show function calls if present
        if message.get("function_calls"):
            with st.expander("🔧 Function Calls Made"):
                for i, fn_call in enumerate(message["function_calls"], 1):
                    st.markdown(f"**{i}. {fn_call['function']}**")
                    st.json(fn_call['arguments'])
                    # Show result preview
                    try:
                        result_data = json.loads(fn_call['result'])
                        if 'error' in result_data:
                            st.error(f"Error: {result_data['error']}")
                        else:
                            # Show summary of result
                            if 'count' in result_data:
                                st.info(f"Retrieved {result_data['count']} shots")
                            elif 'metric' in result_data:
                                st.info(f"Calculated stats for {result_data['metric']}")
                    except:
                        pass


def build_context_prompt(user_prompt: str) -> str:
    """Build prompt with current focus context."""
    context_lines = []
    if focus_session_id:
        context_lines.append(f"Focus session_id: {focus_session_id}")
    if focus_session_type != "All Types":
        context_lines.append(f"Focus session_type: {focus_session_type}")
    if focus_club != "All Clubs":
        context_lines.append(f"Focus club: {focus_club}")
    if focus_tag != "All Tags":
        context_lines.append(f"Focus shot_tag: {focus_tag}")
    if not context_lines:
        return user_prompt
    context = "Context:\n" + "\n".join([f"- {line}" for line in context_lines])
    return f"{context}\n\n{user_prompt}"


def render_practice_plan(plan_data: dict) -> None:
    """
    Render a practice plan visually with drill expanders.

    Args:
        plan_data: Practice plan dict with keys:
            - duration_min: Total duration
            - focus_areas: List of focus areas
            - drills: List of drill dicts (name, duration_min, reps, instructions)
            - rationale: Explanation of why these drills were selected
    """
    st.subheader(f"📋 Practice Plan ({plan_data['duration_min']} min)")
    st.caption(f"Focus: {', '.join(plan_data['focus_areas'])}")

    for i, drill in enumerate(plan_data['drills'], 1):
        with st.expander(f"{i}. {drill['name']} ({drill['duration_min']} min, {drill['reps']} reps)"):
            st.markdown(drill['instructions'])

    st.info(f"**Rationale:** {plan_data['rationale']}")


# Check if we need to generate a response (e.g., after button click rerun)
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    # Last message is from user with no response - generate one now
    last_user_msg = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            coach_prompt = build_context_prompt(last_user_msg)
            response_data = st.session_state.coach.chat(coach_prompt)

            # Check if response contains a practice plan
            has_practice_plan = (
                response_data.get('data') and
                isinstance(response_data['data'], dict) and
                'plan' in response_data['data']
            )

            if has_practice_plan:
                # Render practice plan visually instead of plain text
                render_practice_plan(response_data['data']['plan'])
            else:
                # Display standard response
                st.markdown(response_data['response'])

            # Show function calls if any
            if response_data.get('function_calls'):
                with st.expander("🔧 Function Calls Made", expanded=False):
                    for i, fn_call in enumerate(response_data['function_calls'], 1):
                        st.markdown(f"**{i}. {fn_call['function']}**")
                        st.json(fn_call['arguments'])

            # Add assistant message to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_data['response'],
                "function_calls": response_data.get('function_calls', []),
                "data": response_data.get('data')
            })

# Suggested questions (show when no messages)
if len(st.session_state.messages) == 0:
    st.markdown("### 💡 Try asking:")
    suggested_questions = [
        "What's my average carry distance with Driver?",
        "How consistent is my ball striking?",
        "Show me my performance trends over time",
        "Do I have any club gapping issues?",
        "Generate a personalized practice plan for me",
        "What are my biggest weaknesses?",
        "What should I work on in my next practice session?",
        "Are there any outliers in my recent data?",
        "How does my smash factor compare to optimal?",
        "What's my most consistent club?",
        "Summarize my current session and tag distribution",
        "Which sessions look like full rounds vs practice?"
    ]

    cols = st.columns(2)
    for i, question in enumerate(suggested_questions):
        col_idx = i % 2
        with cols[col_idx]:
            if st.button(question, key=f"suggested_{i}", use_container_width=True):
                # Add to messages and process
                st.session_state.messages.append({
                    "role": "user",
                    "content": question
                })
                st.rerun()


# Chat input
if prompt := st.chat_input("Ask me anything about your golf game..."):
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            coach_prompt = build_context_prompt(prompt)
            response_data = st.session_state.coach.chat(coach_prompt)

            # Check if response contains a practice plan
            has_practice_plan = (
                response_data.get('data') and
                isinstance(response_data['data'], dict) and
                'plan' in response_data['data']
            )

            if has_practice_plan:
                # Render practice plan visually instead of plain text
                render_practice_plan(response_data['data']['plan'])
            else:
                # Display standard response
                st.markdown(response_data['response'])

            # Show function calls if any were made
            if response_data.get('function_calls'):
                with st.expander("🔧 Function Calls Made", expanded=False):
                    for i, fn_call in enumerate(response_data['function_calls'], 1):
                        st.markdown(f"**{i}. {fn_call['function']}**")
                        st.json(fn_call['arguments'])

                        # Show result preview
                        try:
                            result_data = json.loads(fn_call['result'])
                            if 'error' in result_data:
                                st.error(f"Error: {result_data['error']}")
                            else:
                                # Show summary
                                if 'count' in result_data:
                                    st.info(f"Retrieved {result_data['count']} shots")
                                elif 'metric' in result_data:
                                    st.info(f"Stats: avg={result_data.get('mean', 'N/A'):.1f}, std={result_data.get('std', 'N/A'):.1f}")
                                elif 'total_shots' in result_data:
                                    st.info(f"Profile: {result_data['total_shots']} total shots")
                                elif 'club' in result_data and 'sessions' in result_data:
                                    st.info(f"Trend: {result_data['sessions']} sessions analyzed")
                                elif 'gaps' in result_data:
                                    st.info(f"Gapping: {len(result_data['gaps'])} gaps analyzed")
                                elif 'total_outliers' in result_data:
                                    st.info(f"Found {result_data['total_outliers']} outliers")
                        except:
                            pass

            # Add assistant message to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_data['response'],
                "function_calls": response_data.get('function_calls', []),
                "data": response_data.get('data')
            })

# Model retraining panel
if st.session_state.get('show_retrain', False):
    st.divider()
    render_retraining_ui()

    # Close button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("✖️ Close Model Management", use_container_width=True):
            st.session_state.show_retrain = False
            st.rerun()

# Help section at the bottom
with st.expander("ℹ️ How to Use the AI Coach"):
    st.markdown("""
    ### Getting Started

    The AI Coach can help you with:
    - **Performance Analysis**: Ask about averages, consistency, trends
    - **Club Recommendations**: Get insights on club gapping and selection
    - **Practice Planning**: Receive personalized drill recommendations
    - **Data Insights**: Identify outliers, patterns, and areas for improvement

    ### Example Questions

    **Basic Stats:**
    - "What's my average carry with 7 iron?"
    - "How consistent is my driver?"

    **Trends:**
    - "How has my ball speed improved over time?"
    - "Show me my carry distance trend with driver"

    **Technical Analysis:**
    - "What's my smash factor across all clubs?"
    - "Are there any outliers in my data?"
    - "Do I have club gapping issues?"

    **Coaching:**
    - "What should I work on?"
    - "How can I improve my consistency?"
    - "What's my strongest club?"

    **Advanced Features:**
    - **Prediction Intervals**: Ask "Predict my 7-iron distance" to see predictions with confidence intervals
    - **Practice Plans**: Ask "Give me a practice plan" to get a personalized drill plan based on your data

    ### Function Calling

    The AI Coach can access your data through function calling. When you ask a question,
    the coach may call functions to:
    - Query shot data from your database
    - Calculate statistics
    - Analyze trends over time
    - Generate your performance profile
    - Identify outliers

    You can see which functions were called by expanding the "🔧 Function Calls Made" section.

    ### Model Selection

    **Gemini 3.0 Flash** (Recommended):
    - Fastest responses
    - Most cost-effective
    - Great for general coaching questions

    **Gemini 3.0 Pro**:
    - Complex reasoning
    - Better for multi-step analysis
    - Agentic workflow capabilities

    ### Tips for Best Results

    1. **Be specific**: Ask about specific clubs, sessions, or metrics
    2. **Provide context**: Mention what you're working on or struggling with
    3. **Follow up**: The coach remembers conversation context
    4. **Check function calls**: See what data the coach accessed to answer
    5. **Reset if needed**: Start fresh with the reset button if conversation gets off track
    """)

# Footer
st.divider()
st.caption(f"🤖 Model: {selected_model} | 🧠 Thinking: {thinking_level} | 💬 Messages: {len(st.session_state.messages)}")
