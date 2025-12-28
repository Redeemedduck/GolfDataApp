"""
AI Coach Page - Machine Learning Powered Golf Coaching

Phase 5: Interactive AI coaching interface with ML predictions, insights, and diagnostics
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils import golf_db, ai_coach
from components import render_session_selector

st.set_page_config(layout="wide", page_title="AI Coach - My Golf Lab", page_icon="🤖")

# Initialize DB and AI Coach
golf_db.init_db()
coach = ai_coach.get_coach()

# Check if models are trained
models_available = any([
    coach.distance_model,
    coach.shape_classifier,
    coach.anomaly_detector
])

# Page header
st.title("🤖 AI Golf Coach")
st.subheader("Machine Learning Powered Performance Analysis")

if not models_available:
    st.warning("""
    ⚠️ **No ML models found!**

    Train your models first to unlock AI coaching features:

    ```bash
    python scripts/train_models.py --all
    ```

    Once trained, refresh this page to access:
    - 🎯 Shot predictions
    - 📊 Swing diagnostics
    - 💡 Personalized insights
    - 📈 Progress tracking
    """)
    st.stop()

st.divider()

# Tabs for different coaching features
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Shot Predictor",
    "🔍 Swing Diagnosis",
    "💡 Coaching Insights",
    "📈 Progress Tracker",
    "👤 Your Profile"
])

# ==================== TAB 1: SHOT PREDICTOR ====================
with tab1:
    st.header("🎯 Shot Distance Predictor")
    st.markdown("Use the ML model to predict carry distance based on swing parameters.")

    if not coach.distance_model:
        st.info("📊 Distance predictor not trained. Run: `python scripts/train_models.py --distance`")
    else:
        # Display model metadata
        if 'distance_predictor' in coach.metadata:
            meta = coach.metadata['distance_predictor']
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Training Samples", meta['n_samples'])
            col2.metric("RMSE", f"{meta['rmse']:.1f} yds")
            col3.metric("R² Score", f"{meta['r2']:.3f}")
            col4.metric("Last Trained", meta['trained_date'][:10])

        st.divider()

        # Interactive prediction interface
        st.subheader("🎮 Interactive Prediction")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### Ball & Club Metrics")

            ball_speed = st.slider(
                "Ball Speed (mph)",
                min_value=50.0,
                max_value=200.0,
                value=165.0,
                step=0.5,
                help="Speed of the ball immediately after impact"
            )

            club_speed = st.slider(
                "Club Speed (mph)",
                min_value=40.0,
                max_value=150.0,
                value=110.0,
                step=0.5,
                help="Speed of the clubhead at impact"
            )

            smash = ball_speed / club_speed if club_speed > 0 else 0
            st.info(f"⚡ Calculated Smash Factor: **{smash:.2f}**")

        with col2:
            st.markdown("##### Launch Conditions")

            launch_angle = st.slider(
                "Launch Angle (°)",
                min_value=0.0,
                max_value=30.0,
                value=12.0,
                step=0.1,
                help="Vertical angle at which the ball leaves the clubface"
            )

            back_spin = st.slider(
                "Back Spin (rpm)",
                min_value=0,
                max_value=10000,
                value=2500,
                step=100,
                help="Backspin rate of the ball"
            )

            attack_angle = st.slider(
                "Attack Angle (°)",
                min_value=-10.0,
                max_value=10.0,
                value=3.0,
                step=0.1,
                help="Vertical angle of the clubhead's path at impact"
            )

        # Club selection
        all_clubs = golf_db.get_all_shots()['club'].unique().tolist()
        selected_club = st.selectbox(
            "Select Club",
            options=all_clubs if len(all_clubs) > 0 else ['Driver'],
            index=0 if 'Driver' in all_clubs else 0,
            help="Choose the club for prediction"
        )

        # Predict button
        if st.button("🚀 Predict Distance", type="primary", use_container_width=True):
            features = {
                'ball_speed': ball_speed,
                'club_speed': club_speed,
                'launch_angle': launch_angle,
                'back_spin': back_spin,
                'attack_angle': attack_angle,
                'club': selected_club
            }

            prediction = coach.predict_distance(features)

            if prediction:
                st.success(f"### 🎯 Predicted Carry: **{prediction:.1f} yards**")

                # Show comparison to user's average
                user_profile = coach.calculate_user_profile(all_clubs)
                if selected_club in user_profile and user_profile[selected_club]['n_shots'] > 0:
                    avg_carry = user_profile[selected_club]['carry_avg']
                    diff = prediction - avg_carry

                    if abs(diff) > 1:
                        diff_text = f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}"
                        st.info(f"📊 Your {selected_club} avg: {avg_carry:.1f} yds ({diff_text} yds difference)")
            else:
                st.error("❌ Prediction failed. Check your model and feature data.")

        # Shot shape prediction (if available)
        if coach.shape_classifier:
            st.divider()
            st.subheader("🎨 Shot Shape Prediction")

            col1, col2, col3 = st.columns(3)

            with col1:
                side_spin = st.slider(
                    "Side Spin (rpm)",
                    min_value=-2000,
                    max_value=2000,
                    value=-300,
                    step=50,
                    help="Negative = Draw, Positive = Fade"
                )

            with col2:
                club_path = st.slider(
                    "Club Path (°)",
                    min_value=-10.0,
                    max_value=10.0,
                    value=-2.5,
                    step=0.1,
                    help="Negative = In-to-out, Positive = Out-to-in"
                )

            with col3:
                face_angle = st.slider(
                    "Face Angle (°)",
                    min_value=-10.0,
                    max_value=10.0,
                    value=-1.5,
                    step=0.1,
                    help="Negative = Closed, Positive = Open"
                )

            if st.button("🎨 Predict Shape", use_container_width=True):
                shape_features = {
                    'side_spin': side_spin,
                    'club_path': club_path,
                    'face_angle': face_angle,
                    'ball_speed': ball_speed
                }

                shape = coach.predict_shot_shape(shape_features)

                if shape:
                    shape_emoji = {
                        'Draw': '↪️',
                        'Slight Draw': '↗️',
                        'Straight': '⬆️',
                        'Slight Fade': '↖️',
                        'Fade': '↩️'
                    }

                    st.success(f"### {shape_emoji.get(shape, '🎯')} Predicted Shape: **{shape}**")

# ==================== TAB 2: SWING DIAGNOSIS ====================
with tab2:
    st.header("🔍 Swing Diagnostics")
    st.markdown("Detect anomalies and unusual patterns in your swing data.")

    # Session selector
    session_id, df, selected_clubs = render_session_selector(golf_db)

    if len(df) == 0:
        st.info("No data available for the selected session and clubs.")
    else:
        if not coach.anomaly_detector:
            st.info("📊 Anomaly detector not trained. Run: `python scripts/train_models.py --anomaly`")
        else:
            # Run anomaly detection
            df_with_anomalies = coach.detect_swing_anomalies(df)

            # Count anomalies
            anomalies = df_with_anomalies[df_with_anomalies['anomaly'] == -1]
            normal = df_with_anomalies[df_with_anomalies['anomaly'] == 1]

            # Display stats
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Shots", len(df_with_anomalies))
            col2.metric("Normal Swings", len(normal))
            col3.metric("Anomalies Detected", len(anomalies))
            col4.metric("Anomaly Rate", f"{len(anomalies)/len(df_with_anomalies)*100:.1f}%")

            if len(anomalies) > 0:
                st.divider()
                st.subheader("🚨 Detected Anomalies")

                # Show top anomalies table
                anomaly_display = anomalies.nsmallest(10, 'anomaly_score')[[
                    'shot_id', 'club', 'carry', 'ball_speed', 'club_speed',
                    'smash_factor', 'launch_angle', 'anomaly_score'
                ]].copy()

                anomaly_display.columns = ['Shot ID', 'Club', 'Carry', 'Ball Speed',
                                          'Club Speed', 'Smash', 'Launch', 'Anomaly Score']

                st.dataframe(
                    anomaly_display,
                    use_container_width=True,
                    hide_index=True
                )

                # Anomaly score distribution
                st.divider()
                st.subheader("📊 Anomaly Score Distribution")

                fig = px.histogram(
                    df_with_anomalies,
                    x='anomaly_score',
                    nbins=50,
                    color='anomaly',
                    color_discrete_map={1: 'green', -1: 'red'},
                    labels={'anomaly_score': 'Anomaly Score', 'anomaly': 'Classification'},
                    title='Distribution of Anomaly Scores (Lower = More Unusual)'
                )

                st.plotly_chart(fig, use_container_width=True)

                # Scatter plot: Smash vs Anomaly Score
                if 'smash_factor' in df_with_anomalies.columns:
                    st.divider()
                    st.subheader("🎯 Smash Factor vs Anomaly Score")

                    fig2 = px.scatter(
                        df_with_anomalies,
                        x='smash_factor',
                        y='anomaly_score',
                        color='anomaly',
                        color_discrete_map={1: 'green', -1: 'red'},
                        hover_data=['shot_id', 'club', 'carry'],
                        labels={'smash_factor': 'Smash Factor', 'anomaly_score': 'Anomaly Score'},
                        title='Smash Factor Quality vs Anomaly Detection'
                    )

                    st.plotly_chart(fig2, use_container_width=True)
            else:
                st.success("✅ No anomalies detected! All swings appear normal.")

# ==================== TAB 3: COACHING INSIGHTS ====================
with tab3:
    st.header("💡 Personalized Coaching Insights")
    st.markdown("AI-generated recommendations based on your performance data.")

    # Session selector
    session_id, df, selected_clubs = render_session_selector(golf_db)

    if len(df) == 0:
        st.info("No data available for the selected session and clubs.")
    else:
        # Overall insights
        st.subheader("📋 Overall Performance Analysis")

        insights = coach.generate_insights(df)

        for insight in insights:
            if '✅' in insight or '🎯' in insight:
                st.success(insight)
            elif '⚠️' in insight or '📉' in insight or '⬆️' in insight or '⬇️' in insight or '🌀' in insight:
                st.warning(insight)
            else:
                st.info(insight)

        # Club-specific insights
        st.divider()
        st.subheader("🏌️ Club-Specific Analysis")

        clubs_in_session = df['club'].value_counts().head(5).index.tolist()

        for club in clubs_in_session:
            with st.expander(f"📊 {club} ({df[df['club'] == club].shape[0]} shots)"):
                club_insights = coach.generate_insights(df, club=club)

                for insight in club_insights:
                    if '✅' in insight or '🎯' in insight:
                        st.success(insight)
                    elif '⚠️' in insight or '📉' in insight or '⬆️' in insight or '⬇️' in insight or '🌀' in insight:
                        st.warning(insight)
                    else:
                        st.info(insight)

                # Show club stats
                club_df = df[df['club'] == club]
                carry_data = club_df[(club_df['carry'] > 0) & (club_df['carry'] < 400)]['carry']

                if len(carry_data) > 0:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Avg Carry", f"{carry_data.mean():.1f} yds")
                    col2.metric("Std Dev", f"{carry_data.std():.1f} yds")
                    col3.metric("Best", f"{carry_data.max():.1f} yds")
                    col4.metric("Worst", f"{carry_data.min():.1f} yds")

# ==================== TAB 4: PROGRESS TRACKER ====================
with tab4:
    st.header("📈 Progress Tracker")
    st.markdown("Track your improvement over time with trend analysis.")

    # Load all sessions
    all_shots = golf_db.get_all_shots()

    if len(all_shots) == 0:
        st.info("No data available. Import some sessions to track progress.")
    else:
        # Get unique sessions sorted by date
        sessions = all_shots.groupby('session_id').agg({
            'session_date': 'first',
            'shot_id': 'count'
        }).reset_index()
        sessions.columns = ['session_id', 'date', 'shots']
        sessions = sessions.sort_values('date')

        if len(sessions) < 2:
            st.warning("Need at least 2 sessions to show progress trends.")
        else:
            # Club filter
            all_clubs = all_shots['club'].unique().tolist()
            selected_club_progress = st.selectbox(
                "Select club to track",
                options=['All Clubs'] + all_clubs,
                index=0
            )

            # Metric selector
            metric = st.selectbox(
                "Select metric to track",
                options=['carry', 'ball_speed', 'club_speed', 'smash_factor', 'launch_angle', 'back_spin'],
                format_func=lambda x: x.replace('_', ' ').title()
            )

            # Filter data
            if selected_club_progress != 'All Clubs':
                progress_df = all_shots[all_shots['club'] == selected_club_progress].copy()
            else:
                progress_df = all_shots.copy()

            # Group by session and calculate avg
            progress_by_session = progress_df.groupby(['session_id', 'session_date'])[metric].agg(['mean', 'std', 'count']).reset_index()
            progress_by_session = progress_by_session.sort_values('session_date')

            if len(progress_by_session) >= 2:
                # Line chart
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=progress_by_session['session_date'],
                    y=progress_by_session['mean'],
                    mode='lines+markers',
                    name=metric.replace('_', ' ').title(),
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=10)
                ))

                # Add trend line
                x_numeric = np.arange(len(progress_by_session))
                z = np.polyfit(x_numeric, progress_by_session['mean'], 1)
                p = np.poly1d(z)

                fig.add_trace(go.Scatter(
                    x=progress_by_session['session_date'],
                    y=p(x_numeric),
                    mode='lines',
                    name='Trend',
                    line=dict(color='red', dash='dash', width=2)
                ))

                fig.update_layout(
                    title=f"{metric.replace('_', ' ').title()} Progress Over Time",
                    xaxis_title="Session Date",
                    yaxis_title=metric.replace('_', ' ').title(),
                    hovermode='x unified',
                    height=500
                )

                st.plotly_chart(fig, use_container_width=True)

                # Stats
                first_avg = progress_by_session.iloc[0]['mean']
                last_avg = progress_by_session.iloc[-1]['mean']
                improvement = last_avg - first_avg
                improvement_pct = (improvement / first_avg * 100) if first_avg != 0 else 0

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("First Session", f"{first_avg:.1f}")
                col2.metric("Latest Session", f"{last_avg:.1f}")
                col3.metric("Improvement", f"{improvement:+.1f}", delta=f"{improvement_pct:+.1f}%")
                col4.metric("Total Sessions", len(progress_by_session))

# ==================== TAB 5: USER PROFILE ====================
with tab5:
    st.header("👤 Your Performance Profile")
    st.markdown("Baseline statistics and benchmarks for each club in your bag.")

    all_shots = golf_db.get_all_shots()

    if len(all_shots) == 0:
        st.info("No data available. Import some sessions to build your profile.")
    else:
        # Calculate user profile
        profile = coach.calculate_user_profile(all_shots)

        # Convert to DataFrame for display
        profile_df = pd.DataFrame(profile).T.reset_index()
        profile_df.columns = ['Club', 'Shots', 'Carry Avg', 'Carry Std',
                             'Ball Speed Avg', 'Smash Avg', 'Consistency Score']

        # Sort by carry distance
        profile_df = profile_df.sort_values('Carry Avg', ascending=False)

        # Display table
        st.subheader("📊 Club Performance Summary")

        # Format for display
        display_df = profile_df.copy()
        display_df['Carry Avg'] = display_df['Carry Avg'].apply(lambda x: f"{x:.1f} yds")
        display_df['Carry Std'] = display_df['Carry Std'].apply(lambda x: f"{x:.1f} yds")
        display_df['Ball Speed Avg'] = display_df['Ball Speed Avg'].apply(lambda x: f"{x:.1f} mph")
        display_df['Smash Avg'] = display_df['Smash Avg'].apply(lambda x: f"{x:.2f}")
        display_df['Consistency Score'] = display_df['Consistency Score'].apply(lambda x: f"{x:.0f}/100")

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        # Visualizations
        st.divider()
        st.subheader("📈 Visual Analysis")

        col1, col2 = st.columns(2)

        with col1:
            # Carry distance bar chart
            fig1 = px.bar(
                profile_df,
                x='Club',
                y='Carry Avg',
                title='Average Carry Distance by Club',
                labels={'Carry Avg': 'Carry (yards)'},
                color='Carry Avg',
                color_continuous_scale='viridis'
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            # Consistency score
            fig2 = px.bar(
                profile_df,
                x='Club',
                y='Consistency Score',
                title='Consistency Score by Club (0-100)',
                labels={'Consistency Score': 'Consistency'},
                color='Consistency Score',
                color_continuous_scale='RdYlGn'
            )
            fig2.update_yaxis(range=[0, 100])
            st.plotly_chart(fig2, use_container_width=True)

        # Gapping analysis
        st.divider()
        st.subheader("📏 Club Gapping Analysis")
        st.markdown("Distance gaps between consecutive clubs:")

        gaps = []
        for i in range(len(profile_df) - 1):
            club1 = profile_df.iloc[i]
            club2 = profile_df.iloc[i + 1]
            gap = club1['Carry Avg'] - club2['Carry Avg']
            gaps.append({
                'From': club1['Club'],
                'To': club2['Club'],
                'Gap': gap
            })

        if gaps:
            gaps_df = pd.DataFrame(gaps)
            gaps_df['Gap'] = gaps_df['Gap'].apply(lambda x: f"{x:.1f} yds")
            st.dataframe(gaps_df, use_container_width=True, hide_index=True)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>🤖 AI Coach powered by XGBoost, scikit-learn, and machine learning</p>
    <p>Phase 5: Interactive ML predictions and personalized coaching</p>
</div>
""", unsafe_allow_html=True)
