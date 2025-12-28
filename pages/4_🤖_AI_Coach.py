"""
🤖 AI Coach - Cloud-Native Golf Coaching with Gemini 3.0

This page provides an interactive AI coaching experience powered by Google's Gemini 3.0 models.
The AI coach can query your golf data using function calling and provide personalized insights.

Features:
- Multi-turn conversations with context awareness
- Dynamic data access through function calling
- Model selection (Flash for speed, Pro for complex reasoning)
- Thinking level control for response depth
- Function call transparency
"""

import streamlit as st
import os
from datetime import datetime
import json
import gemini_coach
import golf_db


# Page config
st.set_page_config(
    page_title="AI Coach",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Golf Coach")
st.markdown("*Powered by Google Gemini 3.0 with Function Calling*")

# Initialize database
golf_db.init_db()

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Coach Settings")

    # API Key check
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY not set!")
        st.info("Set your API key in .env file:\n```\nGEMINI_API_KEY=your_key_here\n```")
        st.stop()
    else:
        st.success("✅ API Key Configured")

    # Model selection
    st.subheader("Model Selection")
    model_options = {
        'Gemini 3.0 Flash': 'flash',
        'Gemini 3.0 Pro': 'pro'
    }

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

    # Reset conversation
    st.divider()
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.coach = None
        st.rerun()

    # Show data stats
    st.divider()
    st.subheader("📊 Your Data")
    df = golf_db.get_all_shots()
    if not df.empty:
        st.metric("Total Shots", len(df))
        st.metric("Sessions", df['session_id'].nunique())
        st.metric("Clubs", df['club'].nunique())
    else:
        st.warning("No shot data available. Import data first!")

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'coach' not in st.session_state or st.session_state.coach is None:
    try:
        st.session_state.coach = gemini_coach.get_coach(
            model_type=model_options[selected_model],
            thinking_level=thinking_level
        )
    except Exception as e:
        st.error(f"Failed to initialize AI Coach: {str(e)}")
        st.stop()

# Main chat interface
st.subheader("💬 Chat with Your Coach")

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
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

# Suggested questions (show when no messages)
if len(st.session_state.messages) == 0:
    st.markdown("### 💡 Try asking:")
    suggested_questions = [
        "What's my average carry distance with Driver?",
        "How consistent is my ball striking?",
        "Show me my performance trends over time",
        "Do I have any club gapping issues?",
        "What should I work on in my next practice session?",
        "Are there any outliers in my recent data?",
        "How does my smash factor compare to optimal?",
        "What's my most consistent club?"
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
            response_data = st.session_state.coach.chat(prompt)

            # Display response
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
                "function_calls": response_data.get('function_calls', [])
            })

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
