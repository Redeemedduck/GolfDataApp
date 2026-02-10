"""
Session quality scoring component for golf practice sessions.

Provides composite quality score (0-100) based on consistency, performance,
and improvement relative to historical baseline.
"""
import streamlit as st
import pandas as pd
from typing import Dict, Optional, List
from analytics.utils import normalize_score, normalize_inverse


def _calculate_quality_score(stats: dict, historical: List[dict] = None) -> dict:
    """
    Calculate composite session quality score from session statistics.

    Args:
        stats: Session statistics dict from golf_db.get_session_metrics
        historical: List of historical session stats dicts for comparison

    Returns:
        Dictionary with:
        - overall_score: Composite score 0-100
        - consistency_score: Consistency component (0-100)
        - performance_score: Performance component (0-100)
        - improvement_score: Improvement component (0-100)
        - component_details: Dict with sub-metric contributions
    """
    component_details = {}

    # === CONSISTENCY (40%) ===
    # Lower std deviations = better consistency
    consistency_metrics = []
    consistency_weights = []

    # Face angle consistency (weight 0.5 of consistency)
    if stats.get('std_face_angle') is not None:
        std_face = stats['std_face_angle']
        # Range: 0.5° (excellent) to 5.0° (inconsistent)
        face_score = normalize_inverse(std_face, 0.5, 5.0)
        consistency_metrics.append(face_score)
        consistency_weights.append(0.5)
        component_details['std_face_angle'] = {
            'value': std_face,
            'score': face_score,
            'weight': 0.5,
            'component': 'consistency'
        }

    # Club path consistency (weight 0.3 of consistency)
    if stats.get('std_club_path') is not None:
        std_path = stats['std_club_path']
        # Range: 0.5° (excellent) to 4.0° (inconsistent)
        path_score = normalize_inverse(std_path, 0.5, 4.0)
        consistency_metrics.append(path_score)
        consistency_weights.append(0.3)
        component_details['std_club_path'] = {
            'value': std_path,
            'score': path_score,
            'weight': 0.3,
            'component': 'consistency'
        }

    # Strike distance consistency (weight 0.2 of consistency)
    if stats.get('std_strike_distance') is not None:
        std_strike = stats['std_strike_distance']
        # Range: 0.1" (excellent) to 0.5" (inconsistent)
        strike_score = normalize_inverse(std_strike, 0.1, 0.5)
        consistency_metrics.append(strike_score)
        consistency_weights.append(0.2)
        component_details['std_strike_distance'] = {
            'value': std_strike,
            'score': strike_score,
            'weight': 0.2,
            'component': 'consistency'
        }

    # Calculate weighted consistency score
    if consistency_metrics:
        # Normalize weights (redistribute if some metrics missing)
        total_weight = sum(consistency_weights)
        normalized_weights = [w / total_weight for w in consistency_weights]
        consistency_score = sum(m * w for m, w in zip(consistency_metrics, normalized_weights))
    else:
        consistency_score = 50.0  # Neutral if no data

    # === PERFORMANCE (30%) ===
    # Higher values = better performance
    performance_metrics = []
    performance_weights = []

    # Smash factor (weight 0.5 of performance)
    if stats.get('avg_smash') is not None:
        avg_smash = stats['avg_smash']
        # Range: 1.30 (poor) to 1.50 (excellent)
        smash_score = normalize_score(avg_smash, 1.30, 1.50)
        performance_metrics.append(smash_score)
        performance_weights.append(0.5)
        component_details['avg_smash'] = {
            'value': avg_smash,
            'score': smash_score,
            'weight': 0.5,
            'component': 'performance'
        }

    # Ball speed (weight 0.3 of performance)
    if stats.get('avg_ball_speed') is not None:
        avg_speed = stats['avg_ball_speed']
        # Range: 100 mph (beginner) to 170 mph (advanced)
        speed_score = normalize_score(avg_speed, 100, 170)
        performance_metrics.append(speed_score)
        performance_weights.append(0.3)
        component_details['avg_ball_speed'] = {
            'value': avg_speed,
            'score': speed_score,
            'weight': 0.3,
            'component': 'performance'
        }

    # Carry distance (weight 0.2 of performance)
    if stats.get('avg_carry') is not None:
        avg_carry = stats['avg_carry']
        # Range: 100 yds (short irons) to 280 yds (driver)
        carry_score = normalize_score(avg_carry, 100, 280)
        performance_metrics.append(carry_score)
        performance_weights.append(0.2)
        component_details['avg_carry'] = {
            'value': avg_carry,
            'score': carry_score,
            'weight': 0.2,
            'component': 'performance'
        }

    # Calculate weighted performance score
    if performance_metrics:
        total_weight = sum(performance_weights)
        normalized_weights = [w / total_weight for w in performance_weights]
        performance_score = sum(m * w for m, w in zip(performance_metrics, normalized_weights))
    else:
        performance_score = 50.0  # Neutral if no data

    # === IMPROVEMENT (30%) ===
    # Compare to historical average
    if not historical or len(historical) == 0:
        improvement_score = 50.0  # Neutral for first session
        component_details['improvement'] = {
            'value': None,
            'score': 50.0,
            'weight': 1.0,
            'component': 'improvement',
            'note': 'No baseline yet'
        }
    else:
        # Calculate historical mean carry
        hist_carries = [h.get('avg_carry') for h in historical if h.get('avg_carry') is not None]
        if hist_carries and stats.get('avg_carry') is not None:
            hist_mean = sum(hist_carries) / len(hist_carries)
            current_carry = stats['avg_carry']
            improvement_pct = ((current_carry - hist_mean) / hist_mean) * 100

            # Normalize: -10% = 0, 0% = 50, +10% = 100
            # Linear scale clamped to [0, 100]
            improvement_score = 50 + (improvement_pct * 5)
            improvement_score = max(0.0, min(100.0, improvement_score))

            component_details['improvement'] = {
                'value': improvement_pct,
                'score': improvement_score,
                'weight': 1.0,
                'component': 'improvement',
                'historical_mean': hist_mean,
                'current_value': current_carry
            }
        else:
            improvement_score = 50.0  # Neutral if no carry data
            component_details['improvement'] = {
                'value': None,
                'score': 50.0,
                'weight': 1.0,
                'component': 'improvement',
                'note': 'No carry data'
            }

    # === OVERALL SCORE ===
    # Weighted combination: 40% consistency, 30% performance, 30% improvement
    overall_score = (
        consistency_score * 0.40 +
        performance_score * 0.30 +
        improvement_score * 0.30
    )

    return {
        'overall_score': round(overall_score, 1),
        'consistency_score': round(consistency_score, 1),
        'performance_score': round(performance_score, 1),
        'improvement_score': round(improvement_score, 1),
        'component_details': component_details
    }


def render_session_quality(session_stats: dict, historical_stats: List[dict] = None) -> None:
    """
    Render session quality score with component breakdown.

    Note: This component takes a session_stats dict (from golf_db.get_session_metrics)
    rather than a raw DataFrame. This is a deliberate exception to the render_*(df)
    pattern because session quality scoring operates on pre-aggregated metrics
    (std_face_angle, avg_smash, etc.) from the session_stats table, not raw shot rows.

    Args:
        session_stats: Session statistics dict with keys like avg_carry, avg_smash,
                      std_face_angle, std_club_path, shot_count, etc.
        historical_stats: Optional list of historical session stat dicts for improvement
                         comparison
    """
    st.subheader("Session Quality Score")

    # Check for data
    if not session_stats or session_stats is None:
        st.info("No session metrics available")
        return

    # Check minimum shots
    shot_count = session_stats.get('shot_count', 0)
    if shot_count < 5:
        st.warning(f"Need 5+ shots for meaningful quality score (have {shot_count})")
        return

    # Calculate quality score
    quality_data = _calculate_quality_score(session_stats, historical_stats)

    # === OVERALL SCORE DISPLAY ===
    overall = quality_data['overall_score']
    delta = round(overall - 50, 1)  # Delta from neutral baseline

    # Determine interpretation
    if overall >= 86:
        interpretation = "🌟 Exceptional"
        color = "normal"
    elif overall >= 71:
        interpretation = "✅ Great session"
        color = "normal"
    elif overall >= 51:
        interpretation = "👍 Solid session"
        color = "normal"
    elif overall >= 31:
        interpretation = "⚠️ Below average"
        color = "inverse"
    else:
        interpretation = "🔧 Needs work"
        color = "inverse"

    st.metric(
        label="Overall Quality",
        value=f"{overall}/100",
        delta=f"{delta:+.1f} from baseline",
        delta_color=color
    )
    st.caption(interpretation)

    # === COMPONENT BREAKDOWN ===
    st.write("")  # Spacing
    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**Consistency**")
        consistency = quality_data['consistency_score']
        st.progress(consistency / 100)
        st.caption(f"{consistency:.1f}/100")

    with col2:
        st.write("**Performance**")
        performance = quality_data['performance_score']
        st.progress(performance / 100)
        st.caption(f"{performance:.1f}/100")

    with col3:
        st.write("**Improvement**")
        improvement = quality_data['improvement_score']
        if historical_stats and len(historical_stats) > 0:
            st.progress(improvement / 100)
            st.caption(f"{improvement:.1f}/100")
        else:
            st.caption("No baseline yet")

    # === DETAILED BREAKDOWN ===
    with st.expander("📊 Score Breakdown"):
        st.write("**Component Weights:**")
        st.write("- Consistency (40%): Based on standard deviation of face angle, club path, and strike location")
        st.write("- Performance (30%): Based on smash factor, ball speed, and carry distance")
        st.write("- Improvement (30%): Compared to your historical average")
        st.write("")

        # Build detailed metrics table
        details = quality_data['component_details']
        if details:
            rows = []
            for metric_name, metric_data in details.items():
                value = metric_data.get('value')
                if value is not None:
                    if metric_name == 'improvement':
                        value_str = f"{value:+.1f}%"
                    elif 'std' in metric_name or 'strike_distance' in metric_name:
                        value_str = f"{value:.2f}"
                    else:
                        value_str = f"{value:.1f}"
                else:
                    value_str = metric_data.get('note', 'N/A')

                rows.append({
                    'Metric': metric_name.replace('_', ' ').title(),
                    'Value': value_str,
                    'Score': f"{metric_data['score']:.1f}/100",
                    'Weight': f"{metric_data['weight'] * 100:.0f}%",
                    'Component': metric_data['component'].title()
                })

            df_details = pd.DataFrame(rows)
            st.dataframe(df_details, use_container_width=True, hide_index=True)

    # === ACTIONABLE TIP ===
    st.write("")  # Spacing
    lowest_component = min(
        [('consistency', quality_data['consistency_score']),
         ('performance', quality_data['performance_score']),
         ('improvement', quality_data['improvement_score'])],
        key=lambda x: x[1]
    )[0]

    if lowest_component == 'consistency':
        st.info("💡 **Focus Area:** Your consistency needs work. Focus on repeating your setup and swing tempo for more consistent results.")
    elif lowest_component == 'performance':
        st.info("💡 **Focus Area:** Your performance metrics could improve. Work on strike quality (center contact) to improve ball speed and carry.")
    elif lowest_component == 'improvement':
        if historical_stats and len(historical_stats) > 0:
            st.info("💡 **Focus Area:** Your consistency is good but you're not improving. Consider working with a coach or trying new drills.")
        # Don't show tip if no baseline yet
