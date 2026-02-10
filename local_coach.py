"""
Local AI Coach Module for GolfDataApp.

Provides AI coaching functionality without cloud dependencies:
- Template-based insights generation
- ML model predictions (when available)
- Database queries for performance analysis
- Works entirely offline

Usage:
    coach = LocalCoach()
    response = coach.get_response("How's my driver doing?")
    insights = coach.get_session_insights(session_id)
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np

import golf_db

# ML imports with explicit feature flags
try:
    from ml import (
        ML_AVAILABLE,
        ML_MISSING_DEPS,
        DistancePredictor,
        ShotShapeClassifier,
        classify_shot_shape,
        ShotShape,
        SwingFlawDetector,
        detect_swing_flaws,
        SwingFlaw,
    )
except ImportError:
    # Fallback if ml module itself can't be imported
    ML_AVAILABLE = False
    ML_MISSING_DEPS = ["ml module"]
    DistancePredictor = None
    ShotShapeClassifier = None
    classify_shot_shape = None
    ShotShape = None
    SwingFlawDetector = None
    detect_swing_flaws = None
    SwingFlaw = None


@dataclass
class CoachResponse:
    """Response from the local coach."""
    message: str
    data: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    confidence: float = 0.8


class LocalCoach:
    """
    Local AI golf coach with template-based insights.

    Provides personalized coaching without requiring cloud APIs.
    Uses rule-based analysis and optional ML models for predictions.

    Usage:
        coach = LocalCoach()

        # General questions
        response = coach.get_response("What's my average driver distance?")

        # Session analysis
        insights = coach.get_session_insights("session_123")

        # Club comparison
        comparison = coach.get_club_comparison(["Driver", "3 Wood"])
    """

    # Intent patterns for routing queries
    INTENT_PATTERNS = {
        'driver_stats': r'\b(driver|1w|1-wood)\b.*|.*(how|what).*\b(driver|1w|1-wood)\b',
        'iron_stats': r'\b(\d+)\s*iron\b|\b(\d+i)\b',
        'club_comparison': r'\bcompare\b|\bvs\b|\bbetween\b',
        'session_analysis': r'\bsession\b|\btoday\b|\blast\b.*\bpractice\b',
        'trend_analysis': r'\btrend\b|\bprogress\b|\bimproving\b|\bgetting\b',
        'swing_issue': r'\bslice\b|\bhook\b|\bfade\b|\bdraw\b|\bshank\b|\btopping\b',
        'consistency': r'\bconsisten\b|\bvariabl\b|\binconsisten\b',
        'gapping': r'\bgap\b|\bdistance\s*gap\b|\byardage\b',
        'profile': r'\bprofile\b|\boverall\b|\bsummary\b',
    }

    def __init__(self):
        """Initialize the local coach."""
        self.distance_predictor = None
        self.shot_classifier = None
        self.flaw_detector = None

        # Try to load ML models if available
        if ML_AVAILABLE:
            self._load_ml_models()

    @property
    def ml_available(self) -> bool:
        """Check if ML models are loaded and available."""
        return ML_AVAILABLE

    def get_ml_status(self) -> Dict[str, Any]:
        """
        Get ML feature availability status.

        Returns:
            Dict with availability, missing dependencies, and user-friendly message
        """
        if ML_AVAILABLE:
            return {
                'available': True,
                'missing_deps': [],
                'message': 'ML features are available and ready to use.',
            }
        else:
            deps_list = ', '.join(ML_MISSING_DEPS)
            return {
                'available': False,
                'missing_deps': ML_MISSING_DEPS,
                'message': f'ML features unavailable. Install missing dependencies: pip install {deps_list}',
            }

    def _load_ml_models(self) -> None:
        """Load ML models if available."""
        if not ML_AVAILABLE:
            return

        try:
            # Distance prediction - check if class is available
            if DistancePredictor is not None:
                predictor = DistancePredictor()
                if Path(predictor.model_path).exists():
                    predictor.load()
                    self.distance_predictor = predictor
        except Exception:
            pass

        # Shot classifier and flaw detector use rule-based by default
        try:
            if ShotShapeClassifier is not None:
                self.shot_classifier = ShotShapeClassifier()
            if SwingFlawDetector is not None:
                self.flaw_detector = SwingFlawDetector()
        except Exception:
            pass

    def _detect_intent(self, query: str) -> Tuple[str, Optional[str]]:
        """
        Detect the user's intent from their query.

        Args:
            query: User's question

        Returns:
            Tuple of (intent, extracted_entity)
        """
        query_lower = query.lower()

        for intent, pattern in self.INTENT_PATTERNS.items():
            match = re.search(pattern, query_lower)
            if match:
                # Extract entity (e.g., club name, session ID)
                entity = None
                if match.groups():
                    entity = next((g for g in match.groups() if g), None)
                return intent, entity

        return 'general', None

    def get_response(self, query: str) -> CoachResponse:
        """
        Get a response to a user's question.

        Args:
            query: User's question

        Returns:
            CoachResponse with message and data
        """
        intent, entity = self._detect_intent(query)

        handlers = {
            'driver_stats': self._handle_driver_stats,
            'iron_stats': lambda e: self._handle_club_stats(f"{e} Iron" if e else None),
            'club_comparison': self._handle_comparison,
            'session_analysis': self._handle_session_analysis,
            'trend_analysis': self._handle_trends,
            'swing_issue': self._handle_swing_issue,
            'consistency': self._handle_consistency,
            'gapping': self._handle_gapping,
            'profile': self._handle_profile,
            'general': self._handle_general,
        }

        handler = handlers.get(intent, self._handle_general)
        return handler(entity)

    def _handle_driver_stats(self, _: Any) -> CoachResponse:
        """Handle driver statistics queries."""
        return self._handle_club_stats("Driver")

    def _handle_club_stats(self, club: Optional[str]) -> CoachResponse:
        """Handle statistics for a specific club."""
        df = golf_db.get_all_shots()

        if df.empty:
            return CoachResponse(
                message="I don't have any shot data yet. Import some sessions first!",
                confidence=0.9
            )

        if club:
            # Validate club column exists and is string type before using .str accessor
            if 'club' not in df.columns:
                return CoachResponse(
                    message="No club data found in shots. Check your data import.",
                    confidence=0.8
                )
            club_df = df[df['club'].astype(str).str.lower() == club.lower()]
            if club_df.empty:
                available = df['club'].unique().tolist()
                return CoachResponse(
                    message=f"No data for {club}. Available clubs: {', '.join(available[:5])}",
                    data={'available_clubs': available},
                    confidence=0.8
                )
        else:
            club_df = df

        # Calculate stats
        stats = self._calculate_club_stats(club_df)
        club_name = club or "all clubs"

        message = self._format_club_stats(club_name, stats)
        suggestions = self._generate_suggestions(stats, club_name)

        return CoachResponse(
            message=message,
            data=stats,
            suggestions=suggestions,
            confidence=0.85
        )

    def _calculate_club_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate statistics for a DataFrame of shots."""
        stats = {}
        metrics = ['carry', 'total', 'ball_speed', 'club_speed', 'smash', 'launch_angle', 'back_spin']

        for metric in metrics:
            if metric in df.columns:
                data = df[metric].replace([0, 99999], np.nan).dropna()
                if len(data) > 0:
                    stats[metric] = {
                        'avg': round(float(data.mean()), 1),
                        'std': round(float(data.std()), 1),
                        'min': round(float(data.min()), 1),
                        'max': round(float(data.max()), 1),
                    }

        stats['shot_count'] = len(df)
        stats['session_count'] = df['session_id'].nunique()

        return stats

    def _format_club_stats(self, club: str, stats: Dict[str, Any]) -> str:
        """Format club statistics into a readable message."""
        parts = [f"Here's your {club} performance:"]

        if 'carry' in stats:
            parts.append(f"  - Carry: {stats['carry']['avg']:.0f} yards (range: {stats['carry']['min']:.0f}-{stats['carry']['max']:.0f})")

        if 'ball_speed' in stats:
            parts.append(f"  - Ball Speed: {stats['ball_speed']['avg']:.0f} mph")

        if 'smash' in stats:
            smash = stats['smash']['avg']
            quality = "excellent" if smash > 1.48 else "good" if smash > 1.42 else "needs work"
            parts.append(f"  - Smash Factor: {smash:.2f} ({quality})")

        if 'launch_angle' in stats:
            parts.append(f"  - Launch Angle: {stats['launch_angle']['avg']:.1f}°")

        parts.append(f"  - Based on {stats['shot_count']} shots across {stats['session_count']} sessions")

        return "\n".join(parts)

    def _generate_suggestions(self, stats: Dict[str, Any], club: str) -> List[str]:
        """Generate improvement suggestions based on stats."""
        suggestions = []

        # Check smash factor
        if 'smash' in stats:
            smash = stats['smash']['avg']
            if smash < 1.42:
                suggestions.append("Focus on center-face contact to improve compression")
            if stats['smash']['std'] > 0.05:
                suggestions.append("Work on strike consistency - your smash factor varies too much")

        # Check carry variance
        if 'carry' in stats:
            cv = stats['carry']['std'] / stats['carry']['avg'] * 100 if stats['carry']['avg'] > 0 else 0
            if cv > 8:
                suggestions.append(f"Your {club} distance varies quite a bit ({cv:.0f}% CV). Work on tempo")

        # Check launch angle for driver
        if 'launch_angle' in stats and 'driver' in club.lower():
            la = stats['launch_angle']['avg']
            if la < 10:
                suggestions.append("Your launch angle is low. Try teeing higher or moving ball forward")
            elif la > 16:
                suggestions.append("Launch angle is high. Check ball position and tee height")

        if not suggestions:
            suggestions.append("Looking good! Keep up the consistent practice")

        return suggestions

    def _handle_comparison(self, _: Any) -> CoachResponse:
        """Handle club comparison queries."""
        return self.get_club_comparison()

    def get_club_comparison(self, clubs: Optional[List[str]] = None) -> CoachResponse:
        """
        Compare performance across clubs.

        Args:
            clubs: List of club names to compare (uses all if not specified)

        Returns:
            CoachResponse with comparison data
        """
        df = golf_db.get_all_shots()

        if df.empty:
            return CoachResponse(
                message="No shot data available for comparison.",
                confidence=0.9
            )

        # Validate required columns exist
        required_cols = ['club', 'carry', 'total', 'shot_id']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return CoachResponse(
                message=f"Missing required columns for comparison: {', '.join(missing_cols)}",
                confidence=0.7
            )

        # Get club averages
        club_stats = df.groupby('club').agg({
            'carry': lambda x: x.replace([0, 99999], np.nan).mean(),
            'total': lambda x: x.replace([0, 99999], np.nan).mean(),
            'shot_id': 'count'
        }).rename(columns={'shot_id': 'shots'})

        club_stats = club_stats.dropna().sort_values('carry', ascending=False)

        if clubs:
            club_stats = club_stats[club_stats.index.isin(clubs)]

        # Format message
        parts = ["Club Comparison (by carry distance):"]
        for club, row in club_stats.head(10).iterrows():
            parts.append(f"  - {club}: {row['carry']:.0f} yards ({int(row['shots'])} shots)")

        # Calculate gapping
        gaps = club_stats['carry'].diff().dropna()
        avg_gap = gaps.mean()
        parts.append(f"\nAverage gap between clubs: {abs(avg_gap):.0f} yards")

        return CoachResponse(
            message="\n".join(parts),
            data={'clubs': club_stats.to_dict('index')},
            suggestions=["Aim for 10-15 yard gaps between clubs for optimal course management"],
            confidence=0.85
        )

    def _handle_session_analysis(self, _: Any) -> CoachResponse:
        """Handle session analysis queries."""
        df = golf_db.get_all_shots()

        if df.empty:
            return CoachResponse(
                message="No sessions available to analyze.",
                confidence=0.9
            )

        # Validate date_added column exists and has valid values
        if 'date_added' not in df.columns:
            return CoachResponse(
                message="No session date data available. Import some sessions first!",
                confidence=0.8
            )

        df['date_added'] = pd.to_datetime(df['date_added'], errors='coerce')

        # Filter to rows with valid dates
        valid_dates = df[df['date_added'].notna()]
        if valid_dates.empty:
            # Fallback: use first session_id if no valid dates
            latest_session = df['session_id'].iloc[0]
        else:
            latest_session = valid_dates.loc[valid_dates['date_added'].idxmax(), 'session_id']

        return self.get_session_insights(latest_session)

    def get_session_insights(self, session_id: str) -> CoachResponse:
        """
        Get insights for a specific session.

        Args:
            session_id: Session ID to analyze

        Returns:
            CoachResponse with session insights
        """
        df = golf_db.get_session_data(session_id)

        if df is None or df.empty:
            return CoachResponse(
                message=f"No data found for session {session_id}",
                confidence=0.9
            )

        stats = self._calculate_club_stats(df)
        clubs_used = df['club'].unique().tolist()

        parts = [f"Session Analysis ({session_id}):"]
        parts.append(f"  - {stats['shot_count']} shots with {len(clubs_used)} clubs")
        parts.append(f"  - Clubs used: {', '.join(clubs_used[:5])}")

        # Best and worst shots
        if 'carry' in df.columns:
            valid_carry = df[df['carry'].notna() & (df['carry'] > 0) & (df['carry'] < 400)]
            if not valid_carry.empty:
                best = valid_carry.loc[valid_carry['carry'].idxmax()]
                worst = valid_carry.loc[valid_carry['carry'].idxmin()]
                parts.append(f"  - Best shot: {best['carry']:.0f} yards ({best['club']})")
                parts.append(f"  - Shortest: {worst['carry']:.0f} yards ({worst['club']})")

        # Analyze for issues
        suggestions = []
        if self.flaw_detector:
            analysis = self.flaw_detector.analyze_session(df)
            if analysis.get('most_common_flaw'):
                parts.append(f"  - Most common issue: {analysis['most_common_flaw']}")
                suggestions.extend(analysis.get('recommendations', []))

        return CoachResponse(
            message="\n".join(parts),
            data={'session_id': session_id, 'stats': stats},
            suggestions=suggestions or ["Great session! Keep up the practice"],
            confidence=0.85
        )

    def _handle_trends(self, _: Any) -> CoachResponse:
        """Handle trend analysis queries."""
        df = golf_db.get_all_shots()

        if df.empty:
            return CoachResponse(
                message="No data available for trend analysis.",
                confidence=0.9
            )

        # Analyze carry trend
        session_avgs = df.groupby('session_id')['carry'].apply(
            lambda x: x.replace([0, 99999], np.nan).mean()
        ).dropna()

        if len(session_avgs) < 3:
            return CoachResponse(
                message="Need at least 3 sessions for trend analysis. Keep practicing!",
                confidence=0.8
            )

        # Calculate trend
        x = np.arange(len(session_avgs))
        y = session_avgs.values
        slope, _ = np.polyfit(x, y, 1)

        trend_dir = "improving" if slope > 0.5 else "declining" if slope < -0.5 else "stable"
        message = f"Your overall distance is {trend_dir} (trend: {slope:+.1f} yards/session)"

        suggestions = []
        if trend_dir == "improving":
            suggestions.append("Great progress! You're gaining distance consistently")
        elif trend_dir == "declining":
            suggestions.append("Consider focusing on fundamentals - tempo, grip pressure, balance")

        return CoachResponse(
            message=message,
            data={'trend_slope': slope, 'sessions': len(session_avgs)},
            suggestions=suggestions,
            confidence=0.8
        )

    def _handle_swing_issue(self, entity: Any) -> CoachResponse:
        """Handle swing issue queries."""
        df = golf_db.get_all_shots()

        if df.empty:
            return CoachResponse(
                message="Import some shot data to analyze your swing patterns.",
                confidence=0.9
            )

        # Analyze shot shapes if we have the data
        if 'face_angle' in df.columns and 'club_path' in df.columns:
            if self.shot_classifier:
                shapes = self.shot_classifier.classify_batch(df)
                shape_counts = shapes.value_counts()

                parts = ["Shot Shape Analysis:"]
                for shape, count in shape_counts.head(5).items():
                    pct = count / len(df) * 100
                    parts.append(f"  - {shape}: {count} shots ({pct:.0f}%)")

                dominant = shape_counts.idxmax()
                suggestions = []

                if dominant in ['slice', 'fade']:
                    suggestions.append("You're fading/slicing. Work on closing the clubface or in-to-out path")
                elif dominant in ['hook', 'draw']:
                    suggestions.append("You're drawing/hooking. Check grip strength and face control")

                return CoachResponse(
                    message="\n".join(parts),
                    data={'shapes': shape_counts.to_dict()},
                    suggestions=suggestions,
                    confidence=0.85
                )

        return CoachResponse(
            message="I don't have enough face angle and club path data to analyze your shot shapes. "
                   "Make sure your launch monitor captures this data.",
            confidence=0.7
        )

    def _handle_consistency(self, _: Any) -> CoachResponse:
        """Handle consistency analysis queries."""
        df = golf_db.get_all_shots()

        if df.empty:
            return CoachResponse(
                message="No data available to analyze consistency.",
                confidence=0.9
            )

        # Calculate consistency metrics
        cv_by_club = df.groupby('club')['carry'].apply(
            lambda x: x.replace([0, 99999], np.nan).std() / x.replace([0, 99999], np.nan).mean() * 100
        ).dropna().sort_values()

        parts = ["Consistency Analysis (lower % = more consistent):"]
        for club, cv in cv_by_club.head(5).items():
            quality = "excellent" if cv < 5 else "good" if cv < 8 else "needs work"
            parts.append(f"  - {club}: {cv:.1f}% variation ({quality})")

        most_consistent = cv_by_club.idxmin()
        least_consistent = cv_by_club.idxmax()

        parts.append(f"\nMost consistent: {most_consistent}")
        parts.append(f"Needs work: {least_consistent}")

        return CoachResponse(
            message="\n".join(parts),
            data={'consistency': cv_by_club.to_dict()},
            suggestions=[f"Focus practice time on {least_consistent} to improve consistency"],
            confidence=0.85
        )

    def _handle_gapping(self, _: Any) -> CoachResponse:
        """Handle distance gapping queries."""
        return self.get_club_comparison()  # Uses same logic

    def _handle_profile(self, _: Any) -> CoachResponse:
        """Handle profile/summary queries."""
        df = golf_db.get_all_shots()

        if df.empty:
            return CoachResponse(
                message="No data yet! Import some sessions to build your profile.",
                confidence=0.9
            )

        total_shots = len(df)
        total_sessions = df['session_id'].nunique()
        clubs_used = df['club'].nunique()

        parts = ["Your Golf Profile:"]
        parts.append(f"  - Total shots: {total_shots}")
        parts.append(f"  - Sessions: {total_sessions}")
        parts.append(f"  - Clubs in bag: {clubs_used}")

        # Top clubs by usage
        top_clubs = df['club'].value_counts().head(3)
        parts.append("\nMost practiced clubs:")
        for club, count in top_clubs.items():
            parts.append(f"  - {club}: {count} shots")

        return CoachResponse(
            message="\n".join(parts),
            data={
                'total_shots': total_shots,
                'sessions': total_sessions,
                'clubs': clubs_used,
            },
            confidence=0.9
        )

    def _handle_general(self, _: Any) -> CoachResponse:
        """Handle general queries."""
        return CoachResponse(
            message="I can help you with:\n"
                   "  - Club statistics (\"How's my driver?\")\n"
                   "  - Club comparisons (\"Compare my irons\")\n"
                   "  - Session analysis (\"Analyze my last session\")\n"
                   "  - Trend analysis (\"Am I improving?\")\n"
                   "  - Shot shape analysis (\"Why do I slice?\")\n"
                   "  - Consistency metrics (\"How consistent am I?\")\n"
                   "  - Overall profile (\"Show my profile\")\n\n"
                   "What would you like to know?",
            suggestions=["Try asking about your driver distance", "Ask about your progress over time"],
            confidence=0.9
        )

    def predict_distance(
        self,
        ball_speed: float,
        launch_angle: float = 12.0,
        back_spin: float = 2500,
        club_speed: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Predict carry distance using ML model.

        Args:
            ball_speed: Ball speed in mph
            launch_angle: Launch angle in degrees
            back_spin: Back spin in rpm
            club_speed: Club speed in mph (optional)

        Returns:
            Dict with predicted distance and confidence
        """
        if not self.distance_predictor:
            return {
                'error': 'Distance prediction model not available. Train it first.',
                'fallback_estimate': self._estimate_distance(ball_speed),
            }

        try:
            result = self.distance_predictor.predict(
                ball_speed=ball_speed,
                launch_angle=launch_angle,
                back_spin=back_spin,
                club_speed=club_speed,
            )
            return {
                'predicted_carry': result.predicted_value,
                'confidence': result.confidence,
                'feature_importance': result.feature_importance,
            }
        except Exception as e:
            return {
                'error': str(e),
                'fallback_estimate': self._estimate_distance(ball_speed),
            }

    def _estimate_distance(self, ball_speed: float) -> float:
        """Simple distance estimate based on ball speed."""
        # Rough approximation: carry ≈ ball_speed * 1.65
        return ball_speed * 1.65


# Convenience function
def get_coach() -> LocalCoach:
    """Get a LocalCoach instance."""
    return LocalCoach()
