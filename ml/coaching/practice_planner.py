"""
Practice plan generation module.

Generates structured 15-30 minute practice plans with named drills,
durations, rep counts, and instructions based on detected weaknesses.
"""

import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional

try:
    from ml.coaching.weakness_mapper import WeaknessMapper
    WEAKNESS_MAPPER_AVAILABLE = True
except ImportError:
    WEAKNESS_MAPPER_AVAILABLE = False


@dataclass
class Drill:
    """
    Single practice drill with specific instructions.

    Attributes:
        name: Drill name (e.g., "Alignment Stick Setup")
        duration_min: Time allocation in minutes
        focus: Primary focus area (e.g., "alignment", "tempo")
        instructions: Step-by-step instructions
        reps: Number of repetitions
        weakness_key: Weakness type this drill addresses
    """
    name: str
    duration_min: int
    focus: str
    instructions: str
    reps: int
    weakness_key: str


@dataclass
class PracticePlan:
    """
    Complete practice session plan.

    Attributes:
        duration_min: Total plan duration in minutes
        drills: List of Drill objects
        focus_areas: List of focus areas addressed
        rationale: Explanation of why these drills were selected
        weaknesses_addressed: Dict of {weakness_key: severity} that plan targets
    """
    duration_min: int
    drills: List[Drill]
    focus_areas: List[str]
    rationale: str
    weaknesses_addressed: Dict[str, float]


class PracticePlanner:
    """
    Generate structured practice plans based on detected weaknesses.

    Uses WeaknessMapper to analyze shot data and maps weaknesses to
    curated drills from the drill library.
    """

    # Curated drill library mapping weakness types to drills
    DRILL_LIBRARY = {
        'high_dispersion': [
            Drill(
                name="Alignment Stick Setup",
                duration_min=10,
                focus="alignment",
                instructions=(
                    "1. Place two alignment sticks parallel to target line\n"
                    "2. Position one at ball, one at feet\n"
                    "3. Hit 20 shots focusing on setup consistency\n"
                    "4. Check alignment before each shot\n"
                    "5. Track how many stay within target corridor"
                ),
                reps=20,
                weakness_key='high_dispersion'
            ),
            Drill(
                name="Gate Drill",
                duration_min=10,
                focus="path_control",
                instructions=(
                    "1. Create gate with two tees 6 inches apart\n"
                    "2. Place gate 12 inches in front of ball\n"
                    "3. Hit 15 shots through gate without touching tees\n"
                    "4. Start with slower swings for control\n"
                    "5. Gradually increase to full speed"
                ),
                reps=15,
                weakness_key='high_dispersion'
            ),
        ],
        'fade_pattern': [
            Drill(
                name="Face Control Headcover",
                duration_min=15,
                focus="clubface_control",
                instructions=(
                    "1. Place headcover 6 inches inside ball\n"
                    "2. Practice in-to-out swing path\n"
                    "3. Avoid hitting headcover on downswing\n"
                    "4. Feel club approaching from inside\n"
                    "5. Hit 15 shots with focus on path"
                ),
                reps=15,
                weakness_key='fade_pattern'
            ),
        ],
        'slice_pattern': [
            Drill(
                name="Inside Path Drill",
                duration_min=15,
                focus="swing_path",
                instructions=(
                    "1. Place second ball 6 inches outside and behind\n"
                    "2. Practice swinging inside-to-out without hitting outside ball\n"
                    "3. Feel club approaching from inside target line\n"
                    "4. Hit 20 shots focusing on path\n"
                    "5. Check ball flight for draw shape"
                ),
                reps=20,
                weakness_key='slice_pattern'
            ),
            Drill(
                name="Strong Grip Drill",
                duration_min=10,
                focus="grip_setup",
                instructions=(
                    "1. Rotate hands slightly stronger (clockwise for RH)\n"
                    "2. See 2-3 knuckles on lead hand\n"
                    "3. Practice setup without ball (5 reps)\n"
                    "4. Hit 10 half-speed shots\n"
                    "5. Monitor face closure through impact"
                ),
                reps=15,
                weakness_key='slice_pattern'
            ),
        ],
        'hook_pattern': [
            Drill(
                name="Weak Grip Face Control",
                duration_min=10,
                focus="face_control",
                instructions=(
                    "1. Rotate hands slightly weaker (counter-clockwise for RH)\n"
                    "2. See 1-2 knuckles on lead hand\n"
                    "3. Practice setup (5 reps)\n"
                    "4. Hit 10 half-speed shots\n"
                    "5. Feel face staying square through impact"
                ),
                reps=15,
                weakness_key='hook_pattern'
            ),
        ],
        'low_smash_factor': [
            Drill(
                name="Impact Tape Center Contact",
                duration_min=10,
                focus="contact",
                instructions=(
                    "1. Apply impact tape to club face\n"
                    "2. Hit 20 shots at 75% speed\n"
                    "3. Check strike location after each shot\n"
                    "4. Adjust setup if pattern off-center\n"
                    "5. Goal: 15+ center-face strikes"
                ),
                reps=20,
                weakness_key='low_smash_factor'
            ),
            Drill(
                name="Tee Height Drill",
                duration_min=10,
                focus="contact",
                instructions=(
                    "1. Experiment with 3 different tee heights\n"
                    "2. Hit 5 shots at each height\n"
                    "3. Monitor ball speed and smash factor\n"
                    "4. Find optimal height for center contact\n"
                    "5. Note which height produces best smash"
                ),
                reps=15,
                weakness_key='low_smash_factor'
            ),
        ],
        'inconsistent_distance': [
            Drill(
                name="Tempo Metronome",
                duration_min=15,
                focus="tempo",
                instructions=(
                    "1. Use metronome app set to 80 BPM\n"
                    "2. Backswing on beat 1, downswing on beat 2\n"
                    "3. Practice without ball (5 reps)\n"
                    "4. Hit 15 shots matching rhythm\n"
                    "5. Focus on smooth transition"
                ),
                reps=15,
                weakness_key='inconsistent_distance'
            ),
            Drill(
                name="3/4 Swing Drill",
                duration_min=10,
                focus="control",
                instructions=(
                    "1. Take backswing to 3/4 position (9 o'clock)\n"
                    "2. Focus on controlled, consistent swing\n"
                    "3. Hit 20 shots at 3/4 speed\n"
                    "4. Monitor carry distance consistency\n"
                    "5. Goal: < 5 yard variance"
                ),
                reps=20,
                weakness_key='inconsistent_distance'
            ),
        ],
        'high_launch': [
            Drill(
                name="Ball Position Forward",
                duration_min=10,
                focus="launch_control",
                instructions=(
                    "1. Move ball 1-2 inches back in stance\n"
                    "2. Maintain normal setup otherwise\n"
                    "3. Hit 15 shots monitoring launch angle\n"
                    "4. Feel slightly descending blow\n"
                    "5. Target: 12-14 degree launch"
                ),
                reps=15,
                weakness_key='high_launch'
            ),
        ],
        'low_launch': [
            Drill(
                name="Tee Height and Ball Position",
                duration_min=10,
                focus="launch_control",
                instructions=(
                    "1. Tee ball higher (1.5x normal height)\n"
                    "2. Move ball 1 inch forward in stance\n"
                    "3. Hit 15 shots monitoring launch\n"
                    "4. Feel slightly ascending blow\n"
                    "5. Target: 12-14 degree launch"
                ),
                reps=15,
                weakness_key='low_launch'
            ),
        ],
    }

    def __init__(self):
        """Initialize PracticePlanner."""
        pass

    def generate_plan(
        self,
        df: pd.DataFrame,
        target_duration: int = 30,
        clubs: Optional[List[str]] = None
    ) -> PracticePlan:
        """
        Generate practice plan from shot data.

        Args:
            df: DataFrame with shot data
            target_duration: Desired plan duration in minutes (15-30)
            clubs: Optional list of clubs to analyze

        Returns:
            PracticePlan with selected drills and rationale
        """
        if not WEAKNESS_MAPPER_AVAILABLE or df.empty:
            return self._default_plan()

        # Detect weaknesses
        mapper = WeaknessMapper()
        weaknesses = mapper.detect_weaknesses(df, clubs=clubs)

        if not weaknesses:
            return self._default_plan()

        return self.generate_plan_from_weaknesses(weaknesses, target_duration)

    def generate_plan_from_weaknesses(
        self,
        weaknesses: Dict[str, float],
        target_duration: int = 30
    ) -> PracticePlan:
        """
        Generate practice plan from pre-computed weaknesses.

        Useful when LocalCoach or other components have already detected weaknesses.

        Args:
            weaknesses: Dict of {weakness_key: severity} sorted by severity
            target_duration: Desired plan duration in minutes

        Returns:
            PracticePlan with selected drills
        """
        if not weaknesses:
            return self._default_plan()

        selected_drills = []
        remaining_time = target_duration
        focus_areas = []
        weaknesses_addressed = {}

        # Sort by severity (highest first)
        sorted_weaknesses = sorted(weaknesses.items(), key=lambda x: x[1], reverse=True)

        # Greedy drill selection
        for weakness_key, severity in sorted_weaknesses:
            if remaining_time < 10:
                break

            if weakness_key in self.DRILL_LIBRARY:
                # Get drills for this weakness
                available_drills = self.DRILL_LIBRARY[weakness_key]

                # Select first drill that fits (TODO: add variety/rotation in future)
                for drill in available_drills:
                    if drill.duration_min <= remaining_time:
                        selected_drills.append(drill)
                        focus_areas.append(drill.focus)
                        weaknesses_addressed[weakness_key] = severity
                        remaining_time -= drill.duration_min
                        break  # Only take one drill per weakness for now

        # Build rationale
        weakness_names = [
            key.replace('_', ' ').title()
            for key in list(weaknesses_addressed.keys())[:3]
        ]

        if weakness_names:
            if len(weaknesses_addressed) == 1:
                rationale = (
                    f"Detected primary issue: {weakness_names[0]} "
                    f"(severity: {list(weaknesses_addressed.values())[0]:.1%}). "
                    f"This plan targets your top weakness with proven drills."
                )
            else:
                rationale = (
                    f"Detected primary issues: {', '.join(weakness_names)}. "
                    f"This plan targets your top weaknesses with proven drills."
                )
        else:
            rationale = "General practice plan for skill development."

        actual_duration = target_duration - remaining_time

        return PracticePlan(
            duration_min=actual_duration,
            drills=selected_drills,
            focus_areas=list(set(focus_areas)),  # Unique focus areas
            rationale=rationale,
            weaknesses_addressed=weaknesses_addressed
        )

    def _default_plan(self) -> PracticePlan:
        """
        Return default practice plan when no data or no weaknesses detected.

        Returns:
            General warm-up practice plan
        """
        default_drills = [
            Drill(
                name="General Warm-up",
                duration_min=10,
                focus="warm_up",
                instructions=(
                    "1. Start with short wedge shots (10 reps)\n"
                    "2. Progress to mid-irons (10 reps)\n"
                    "3. Gradually increase swing speed\n"
                    "4. Focus on rhythm and balance\n"
                    "5. Loosen up before main practice"
                ),
                reps=20,
                weakness_key='general'
            ),
            Drill(
                name="Full Swing Practice",
                duration_min=20,
                focus="fundamentals",
                instructions=(
                    "1. Work through bag: wedges, mid-irons, long irons, woods\n"
                    "2. 5 shots per club type\n"
                    "3. Focus on quality contact and setup consistency\n"
                    "4. Note any recurring patterns\n"
                    "5. Track best/worst clubs for future analysis"
                ),
                reps=30,
                weakness_key='general'
            ),
        ]

        return PracticePlan(
            duration_min=30,
            drills=default_drills,
            focus_areas=['warm_up', 'fundamentals'],
            rationale=(
                "No specific weaknesses detected. "
                "General practice plan for skill maintenance and data collection."
            ),
            weaknesses_addressed={}
        )
