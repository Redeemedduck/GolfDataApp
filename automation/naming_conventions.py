"""
Naming Conventions for Clubs, Sessions, and Automatic Tagging.

Provides consistent naming across all imported data:
- Club names standardized (e.g., "7I" -> "7 Iron")
- Session names generated from metadata
- Automatic tagging based on session characteristics
- Session classification (practice, sim_round, drill, warmup, fitting)

Standard Club Names:
    Woods:   Driver, 3 Wood, 5 Wood, 7 Wood
    Hybrids: 3 Hybrid, 4 Hybrid, 5 Hybrid, 6 Hybrid
    Irons:   1 Iron, 2 Iron, ... 9 Iron
    Wedges:  PW, GW, AW, SW, LW (or with degrees: PW (46), SW (56), etc.)
    Putter:  Putter

Session Naming Patterns:
    Practice:  "Practice - Jan 25, 2026"
    Drill:     "Drill - Driver Consistency - Jan 25, 2026"
    Round:     "Pebble Beach Round - Jan 25, 2026"
    Fitting:   "Fitting - Driver - Jan 25, 2026"
    Warmup:    "Warmup - Jan 25, 2026"

Session Categories:
    practice:   Focused practice on specific clubs/skills
    sim_round:  Indoor simulated round of golf (wide club variety, hole-like patterns)
    drill:      Repetitive work with 1-2 clubs
    warmup:     Brief session (<10 shots)
    fitting:    Club fitting session
"""

import re
import math
from datetime import datetime
from typing import Any, Optional, List, Dict, Set, Tuple, Union
from dataclasses import dataclass, field
from collections import Counter, OrderedDict


@dataclass
class NormalizationResult:
    """Result of a club name normalization."""
    original: str
    normalized: str
    confidence: float  # 0.0 to 1.0
    matched_pattern: Optional[str] = None


class ClubNameNormalizer:
    """
    Normalizes club names to a consistent standard format.

    Usage:
        normalizer = ClubNameNormalizer()

        # Single club
        result = normalizer.normalize("7i")
        print(result.normalized)  # "7 Iron"

        # Batch normalization
        clubs = ["DR", "7i", "pw", "Sand"]
        normalized = normalizer.normalize_all(clubs)
        # ["Driver", "7 Iron", "PW", "SW"]

        # Add custom mappings
        normalizer.add_custom_mapping("my weird club", "7 Iron")
    """

    # Standard club names (the canonical forms)
    STANDARD_CLUBS = [
        # Woods
        'Driver', '2 Wood', '3 Wood', '4 Wood', '5 Wood', '7 Wood', '9 Wood',
        # Hybrids
        '2 Hybrid', '3 Hybrid', '4 Hybrid', '5 Hybrid', '6 Hybrid', '7 Hybrid',
        # Irons
        '1 Iron', '2 Iron', '3 Iron', '4 Iron', '5 Iron', '6 Iron', '7 Iron', '8 Iron', '9 Iron',
        # Wedges (standard abbreviations)
        'PW', 'GW', 'AW', 'SW', 'LW',
        # Putter
        'Putter',
    ]

    # Pattern mappings: regex -> standard name
    # Order matters - more specific patterns should come first
    CLUB_PATTERNS = [
        # === Driver variations ===
        (r'^(dr|driver|1w|1 wood|1wood|d)$', 'Driver'),
        # Simulator/system-generated driver formats
        (r'^(m?\s*driver|drv|dvr)$', 'Driver'),
        (r'^driver\s*(?:sim|sys|#?\d*)$', 'Driver'),

        # === Woods ===
        (r'^(2w|2 wood|2wood|fairway 2|2\s*wd)$', '2 Wood'),
        (r'^(3w|3 wood|3wood|fairway 3|3wd|3\s*wd)$', '3 Wood'),
        (r'^(4w|4 wood|4wood|fairway 4|4\s*wd)$', '4 Wood'),
        (r'^(5w|5 wood|5wood|fairway 5|5wd|5\s*wd)$', '5 Wood'),
        (r'^(7w|7 wood|7wood|fairway 7|7\s*wd)$', '7 Wood'),
        (r'^(9w|9 wood|9wood|fairway 9|9\s*wd)$', '9 Wood'),
        # Reversed formats: "wood 3", "fw3"
        (r'^wood\s*([2-9])$', '_WOOD_NUM'),
        (r'^fw\s*([2-9])$', '_WOOD_NUM'),
        # M-prefixed simulator formats: "m3w", "m 5 wood"
        (r'^m\s*([2-9])\s*w(?:ood)?$', '_WOOD_NUM'),

        # === Hybrids ===
        (r'^(2h|2 hybrid|hybrid 2|2hy|2 hy|rescue 2|2\s*ut)$', '2 Hybrid'),
        (r'^(3h|3 hybrid|hybrid 3|3hy|3 hy|rescue 3|3\s*ut)$', '3 Hybrid'),
        (r'^(4h|4 hybrid|hybrid 4|4hy|4 hy|rescue 4|4\s*ut)$', '4 Hybrid'),
        (r'^(5h|5 hybrid|hybrid 5|5hy|5 hy|rescue 5|5\s*ut)$', '5 Hybrid'),
        (r'^(6h|6 hybrid|hybrid 6|6hy|6 hy|rescue 6|6\s*ut)$', '6 Hybrid'),
        (r'^(7h|7 hybrid|hybrid 7|7hy|7 hy|rescue 7|7\s*ut)$', '7 Hybrid'),
        # Reversed/utility formats
        (r'^hybrid\s*([2-7])$', '_HYBRID_NUM'),
        (r'^(?:ut|utility)\s*([2-7])$', '_HYBRID_NUM'),
        (r'^m\s*([2-7])\s*h(?:ybrid)?$', '_HYBRID_NUM'),

        # === Irons ===
        (r'^(1i|1 iron|iron 1|1-iron|one iron|1\s*ir)$', '1 Iron'),
        (r'^(2i|2 iron|iron 2|2-iron|two iron|2\s*ir)$', '2 Iron'),
        (r'^(3i|3 iron|iron 3|3-iron|three iron|3\s*ir)$', '3 Iron'),
        (r'^(4i|4 iron|iron 4|4-iron|four iron|4\s*ir)$', '4 Iron'),
        (r'^(5i|5 iron|iron 5|5-iron|five iron|5\s*ir)$', '5 Iron'),
        (r'^(6i|6 iron|iron 6|6-iron|six iron|6\s*ir)$', '6 Iron'),
        (r'^(7i|7 iron|iron 7|7-iron|seven iron|7\s*ir)$', '7 Iron'),
        (r'^(8i|8 iron|iron 8|8-iron|eight iron|8\s*ir)$', '8 Iron'),
        (r'^(9i|9 iron|iron 9|9-iron|nine iron|9\s*ir)$', '9 Iron'),
        # M-prefixed simulator formats: "m7i", "m 8 iron"
        (r'^m\s*([1-9])\s*i(?:ron)?$', '_IRON_NUM'),
        # Bare number in iron context (handled specially below)
        # "iron+context" compound: "7 iron approach", "8iron dst"
        (r'^([1-9])\s*iron\s+\w+$', '_IRON_NUM'),

        # === Wedges - specific lofts ===
        (r'^(pw|p wedge|pitching wedge|pitching|p\.w\.|46\s*deg|46\s*°)$', 'PW'),
        (r'^(gw|g wedge|gap wedge|gap|g\.w\.|50\s*deg|50\s*°|52\s*deg|52\s*°)$', 'GW'),
        (r'^(aw|a wedge|approach wedge|approach|a\.w\.)$', 'AW'),
        (r'^(sw|s wedge|sand wedge|sand|s\.w\.|54\s*deg|54\s*°|56\s*deg|56\s*°)$', 'SW'),
        (r'^(lw|l wedge|lob wedge|lob|l\.w\.|58\s*deg|58\s*°|60\s*deg|60\s*°|62\s*deg|62\s*°)$', 'LW'),
        # M-prefixed wedge formats: "mpw", "m sw"
        (r'^m\s*pw$', 'PW'),
        (r'^m\s*gw$', 'GW'),
        (r'^m\s*aw$', 'AW'),
        (r'^m\s*sw$', 'SW'),
        (r'^m\s*lw$', 'LW'),

        # === Generic wedge with degree ===
        (r'^(\d{2})\s*(deg|degree|°).*$', '_DEGREE_WEDGE'),
        # Degree-only: bare "56", "60" (in wedge range 44-62)
        (r'^(4[4-9]|5\d|6[0-2])$', '_DEGREE_WEDGE_BARE'),

        # === Putter ===
        (r'^(putter|putt|putting)$', 'Putter'),
    ]

    # Degree to wedge mapping for generic wedge detection
    DEGREE_TO_WEDGE = {
        44: 'PW', 45: 'PW', 46: 'PW', 47: 'PW', 48: 'PW',
        49: 'GW', 50: 'GW', 51: 'GW', 52: 'GW',
        53: 'SW', 54: 'SW', 55: 'SW', 56: 'SW',
        57: 'LW', 58: 'LW', 59: 'LW', 60: 'LW', 61: 'LW', 62: 'LW',
    }

    def __init__(self):
        """Initialize the normalizer."""
        # Compile regex patterns for efficiency
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in self.CLUB_PATTERNS
        ]

        # Custom user-defined mappings
        self._custom_mappings: Dict[str, str] = {}

    def add_custom_mapping(self, original: str, normalized: str) -> None:
        """
        Add a custom club name mapping.

        Args:
            original: The original club name (case-insensitive)
            normalized: The normalized club name to map to
        """
        self._custom_mappings[original.lower().strip()] = normalized

    def normalize(self, club_name: str) -> NormalizationResult:
        """
        Normalize a single club name.

        Args:
            club_name: Raw club name from Uneekor

        Returns:
            NormalizationResult with normalized name and confidence
        """
        if not club_name:
            return NormalizationResult(
                original=club_name,
                normalized='Unknown',
                confidence=0.0
            )

        original = club_name
        cleaned = club_name.strip().lower()

        # Check custom mappings first
        if cleaned in self._custom_mappings:
            return NormalizationResult(
                original=original,
                normalized=self._custom_mappings[cleaned],
                confidence=1.0,
                matched_pattern='custom_mapping'
            )

        # Check if already a standard name (case-insensitive)
        for standard in self.STANDARD_CLUBS:
            if cleaned == standard.lower():
                return NormalizationResult(
                    original=original,
                    normalized=standard,
                    confidence=1.0,
                    matched_pattern='exact_match'
                )

        # Try pattern matching
        for pattern, name in self._compiled_patterns:
            match = pattern.match(cleaned)
            if match:
                if name == '_DEGREE_WEDGE':
                    # Special handling for degree-based wedge
                    try:
                        degree = int(match.group(1))
                        normalized = self.DEGREE_TO_WEDGE.get(degree, f'{degree} Wedge')
                        return NormalizationResult(
                            original=original,
                            normalized=normalized,
                            confidence=0.9,
                            matched_pattern='degree_wedge'
                        )
                    except (ValueError, IndexError):
                        continue
                elif name == '_DEGREE_WEDGE_BARE':
                    # Bare degree number (e.g., "56" -> SW)
                    try:
                        degree = int(match.group(1))
                        normalized = self.DEGREE_TO_WEDGE.get(degree, f'{degree} Wedge')
                        return NormalizationResult(
                            original=original,
                            normalized=normalized,
                            confidence=0.85,
                            matched_pattern='degree_wedge_bare'
                        )
                    except (ValueError, IndexError):
                        continue
                elif name == '_IRON_NUM':
                    # Dynamic iron from captured number
                    try:
                        num = match.group(1)
                        return NormalizationResult(
                            original=original,
                            normalized=f'{num} Iron',
                            confidence=0.95,
                            matched_pattern='iron_num'
                        )
                    except (ValueError, IndexError):
                        continue
                elif name == '_WOOD_NUM':
                    # Dynamic wood from captured number
                    try:
                        num = match.group(1)
                        return NormalizationResult(
                            original=original,
                            normalized=f'{num} Wood',
                            confidence=0.95,
                            matched_pattern='wood_num'
                        )
                    except (ValueError, IndexError):
                        continue
                elif name == '_HYBRID_NUM':
                    # Dynamic hybrid from captured number
                    try:
                        num = match.group(1)
                        return NormalizationResult(
                            original=original,
                            normalized=f'{num} Hybrid',
                            confidence=0.95,
                            matched_pattern='hybrid_num'
                        )
                    except (ValueError, IndexError):
                        continue
                else:
                    return NormalizationResult(
                        original=original,
                        normalized=name,
                        confidence=0.95,
                        matched_pattern=pattern.pattern
                    )

        # Bare single digit: attempt iron detection (e.g., "7" -> "7 Iron")
        bare_num_match = re.match(r'^([1-9])$', cleaned)
        if bare_num_match:
            num = bare_num_match.group(1)
            return NormalizationResult(
                original=original,
                normalized=f'{num} Iron',
                confidence=0.7,
                matched_pattern='bare_number_iron'
            )

        # No match found - return original with low confidence
        # Capitalize first letter of each word
        fallback = ' '.join(word.capitalize() for word in cleaned.split())
        return NormalizationResult(
            original=original,
            normalized=fallback,
            confidence=0.3,
            matched_pattern=None
        )

    def normalize_all(self, club_names: List[str]) -> List[str]:
        """
        Normalize a list of club names.

        Args:
            club_names: List of raw club names

        Returns:
            List of normalized club names
        """
        return [self.normalize(name).normalized for name in club_names]

    def get_normalization_report(self, club_names: List[str]) -> Dict[str, any]:
        """
        Generate a detailed normalization report.

        Args:
            club_names: List of raw club names

        Returns:
            Report with statistics and details
        """
        results = [self.normalize(name) for name in club_names]

        high_confidence = [r for r in results if r.confidence >= 0.9]
        medium_confidence = [r for r in results if 0.5 <= r.confidence < 0.9]
        low_confidence = [r for r in results if r.confidence < 0.5]

        return {
            'total': len(results),
            'high_confidence': len(high_confidence),
            'medium_confidence': len(medium_confidence),
            'low_confidence': len(low_confidence),
            'low_confidence_clubs': [
                {'original': r.original, 'normalized': r.normalized}
                for r in low_confidence
            ],
            'unique_normalized': list(set(r.normalized for r in results)),
        }


class SessionNamer:
    """
    Generates meaningful session names based on metadata.

    Usage:
        namer = SessionNamer()

        # Generate name from session data
        name = namer.generate_name(
            session_type='practice',
            session_date=datetime.now(),
            clubs_used=['Driver', '7 Iron', 'PW']
        )
        # Returns: "Practice - Jan 25, 2026"

        # With drill focus
        name = namer.generate_name(
            session_type='drill',
            session_date=datetime.now(),
            drill_focus='Driver Consistency'
        )
        # Returns: "Drill - Driver Consistency - Jan 25, 2026"
    """

    SESSION_TYPES = {
        'practice': 'Practice',
        'drill': 'Drill',
        'round': 'Round',
        'sim_round': 'Sim Round',
        'fitting': 'Fitting',
        'warmup': 'Warmup',
        'lesson': 'Lesson',
    }

    def __init__(self, date_format: str = '%b %d, %Y'):
        """
        Initialize session namer.

        Args:
            date_format: strftime format for dates (default: "Jan 25, 2026")
        """
        self.date_format = date_format

    def generate_name(
        self,
        session_type: str,
        session_date: datetime,
        clubs_used: Optional[List[str]] = None,
        course_name: Optional[str] = None,
        drill_focus: Optional[str] = None,
        shot_count: Optional[int] = None,
    ) -> str:
        """
        Generate a descriptive session name.

        Args:
            session_type: Type of session (practice, drill, round, etc.)
            session_date: Date of the session
            clubs_used: List of clubs used in the session
            course_name: Name of course (for sim rounds)
            drill_focus: Focus area for drill sessions
            shot_count: Number of shots in session

        Returns:
            Generated session name
        """
        date_str = session_date.strftime(self.date_format)
        type_name = self.SESSION_TYPES.get(session_type.lower(), session_type.capitalize())

        if session_type.lower() == 'round' and course_name:
            return f"{course_name} Round - {date_str}"

        if session_type.lower() == 'drill' and drill_focus:
            return f"Drill - {drill_focus} - {date_str}"

        if session_type.lower() == 'fitting' and clubs_used:
            # Use the primary club being fit
            primary_club = clubs_used[0] if len(clubs_used) == 1 else 'Multiple Clubs'
            return f"Fitting - {primary_club} - {date_str}"

        return f"{type_name} - {date_str}"

    def infer_session_type(
        self,
        shot_count: int,
        clubs_used: List[str],
        duration_minutes: Optional[int] = None,
    ) -> str:
        """
        Infer session type from characteristics.

        Logic:
        - 1-2 clubs + high shot count (>50) = Drill
        - Many clubs (10+) + moderate shot count = Practice
        - Shot count < 10 = Warmup
        - Very high shot count (>150) with many clubs = Round or extended practice

        Args:
            shot_count: Number of shots in session
            clubs_used: List of clubs used
            duration_minutes: Session duration if known

        Returns:
            Inferred session type
        """
        num_clubs = len(clubs_used)

        # Warmup: very few shots
        if shot_count < 10:
            return 'warmup'

        # Drill: 1-2 clubs with significant shot count
        if num_clubs <= 2 and shot_count >= 30:
            return 'drill'

        # Fitting: 1 club with very high shot count
        if num_clubs == 1 and shot_count >= 50:
            return 'fitting'

        # Practice: multiple clubs
        if num_clubs >= 3:
            return 'practice'

        # Default to practice
        return 'practice'

    # --- Club categories for distribution-based session type detection ---

    DRIVER_CLUBS = {'Driver'}
    IRON_CLUBS = {f'{i} Iron' for i in range(1, 10)}
    WEDGE_CLUBS = {'PW', 'GW', 'AW', 'SW', 'LW'}
    WOOD_CLUBS = {'3 Wood', '5 Wood', '7 Wood', '2 Wood', '4 Wood', '9 Wood'}
    HYBRID_CLUBS = {f'{i} Hybrid' for i in range(2, 7)}

    def detect_session_type(self, clubs: List[str], context_hint: Optional[str] = None) -> str:
        """
        Detect session type based on club distribution and shot sequencing.

        Uses the SessionClassifier to first check for sim rounds (indoor
        practice rounds with wide club variety and hole-like patterns),
        then falls back to category-proportion classification:
        - 'Sim Round' if classifier detects round-like patterns
        - 'Warmup' if <10 total shots
        - 'Driver Focus' if >60% driver shots
        - 'Iron Work' if >60% iron shots
        - 'Short Game' if >60% wedge shots
        - 'Woods Focus' if >60% wood/hybrid shots
        - 'Mixed Practice' otherwise

        Args:
            clubs: List of club names per shot (with repetitions).
                   Should be normalized canonical names.
            context_hint: Optional context string (e.g., "Sgt Rd1") for
                         direct classification signals.

        Returns:
            Session type string for display.
        """
        if not clubs:
            return 'Mixed Practice'

        total = len(clubs)

        if total < 10:
            return 'Warmup'

        # Check for sim round using the classifier
        classifier = SessionClassifier()
        classification = classifier.classify(clubs, context_hint=context_hint)
        if classification.category == 'sim_round' and classification.confidence >= 0.7:
            return 'Sim Round'

        driver_count = sum(1 for c in clubs if c in self.DRIVER_CLUBS)
        iron_count = sum(1 for c in clubs if c in self.IRON_CLUBS)
        wedge_count = sum(1 for c in clubs if c in self.WEDGE_CLUBS)
        wood_count = sum(1 for c in clubs if c in self.WOOD_CLUBS or c in self.HYBRID_CLUBS)

        if driver_count / total > 0.6:
            return 'Driver Focus'
        if iron_count / total > 0.6:
            return 'Iron Work'
        if wedge_count / total > 0.6:
            return 'Short Game'
        if wood_count / total > 0.6:
            return 'Woods Focus'

        return 'Mixed Practice'

    def generate_display_name(
        self,
        session_date: Union[datetime, str, None],
        clubs: List[str],
    ) -> str:
        """
        Generate a display name in standard format.

        Format: "{YYYY-MM-DD} {SessionType} ({shot_count} shots)"

        Args:
            session_date: Date of the session (datetime, string, or None).
            clubs: List of club names per shot (with repetitions).

        Returns:
            Display name string, e.g. "2026-01-25 Mixed Practice (47 shots)"
        """
        # Resolve date string
        if session_date is None:
            date_str = 'Unknown Date'
        elif isinstance(session_date, datetime):
            date_str = session_date.strftime('%Y-%m-%d')
        elif isinstance(session_date, str):
            date_str = session_date[:10]  # Handle both YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS
        else:
            date_str = str(session_date)[:10]

        session_type = self.detect_session_type(clubs)
        shot_count = len(clubs)

        return f"{date_str} {session_type} ({shot_count} shots)"


class AutoTagger:
    """
    Automatically applies tags based on session characteristics.

    Tags help categorize and filter sessions for analysis:
    - "Driver Focus" - Sessions focused on driver
    - "Short Game" - Wedge-only sessions
    - "Full Bag" - Sessions using 10+ clubs
    - "High Volume" - Sessions with 100+ shots
    - "Consistency Work" - Repeated shots with same club

    Usage:
        tagger = AutoTagger()
        tags = tagger.auto_tag(
            clubs_used=['Driver'],
            shot_count=75,
        )
        # Returns: ['Driver Focus', 'High Volume']
    """

    WEDGE_CLUBS = {'PW', 'GW', 'AW', 'SW', 'LW'}
    WOOD_CLUBS = {'Driver', '2 Wood', '3 Wood', '4 Wood', '5 Wood', '7 Wood', '9 Wood'}

    IRON_CLUBS_SET = {f'{i} Iron' for i in range(1, 10)}

    def __init__(self):
        """Initialize auto-tagger with default rules."""
        self._rules: List[Tuple[str, callable, str]] = [
            # (rule_name, condition_function, tag_to_apply)
            ('sim_round', self._is_sim_round, 'Sim Round'),
            ('driver_only', self._is_driver_only, 'Driver Focus'),
            ('wedge_only', self._is_wedge_only, 'Short Game'),
            ('full_bag', self._is_full_bag, 'Full Bag'),
            ('high_volume', self._is_high_volume, 'High Volume'),
            ('warmup', self._is_warmup, 'Warmup'),
            ('iron_work', self._is_iron_work, 'Iron Work'),
            ('woods_focus', self._is_woods_focus, 'Woods Focus'),
        ]

    def _is_sim_round(self, clubs: Set[str], shot_count: int, **kwargs) -> bool:
        """Detect sim round using the SessionClassifier."""
        club_list = kwargs.get('club_sequence', [])
        if not club_list:
            # Build a flat list from clubs set (less accurate without sequence)
            club_list = list(clubs) * max(1, shot_count // max(len(clubs), 1))
        classifier = SessionClassifier()
        result = classifier.classify(club_list)
        return result.category == 'sim_round' and result.confidence >= 0.7

    def _is_driver_only(self, clubs: Set[str], shot_count: int, **kwargs) -> bool:
        return len(clubs) == 1 and 'Driver' in clubs

    def _is_wedge_only(self, clubs: Set[str], shot_count: int, **kwargs) -> bool:
        return len(clubs) > 0 and clubs.issubset(self.WEDGE_CLUBS)

    def _is_full_bag(self, clubs: Set[str], shot_count: int, **kwargs) -> bool:
        return len(clubs) >= 10

    def _is_high_volume(self, clubs: Set[str], shot_count: int, **kwargs) -> bool:
        return shot_count >= 100

    def _is_warmup(self, clubs: Set[str], shot_count: int, **kwargs) -> bool:
        return shot_count < 10

    def _is_iron_work(self, clubs: Set[str], shot_count: int, **kwargs) -> bool:
        iron_clubs = {c for c in clubs if c in self.IRON_CLUBS_SET}
        return len(iron_clubs) >= 3 and iron_clubs == clubs

    def _is_woods_focus(self, clubs: Set[str], shot_count: int, **kwargs) -> bool:
        return len(clubs) > 0 and clubs.issubset(self.WOOD_CLUBS) and len(clubs) >= 2

    def auto_tag(
        self,
        clubs_used: List[str],
        shot_count: int,
        **kwargs
    ) -> List[str]:
        """
        Automatically generate tags for a session.

        Args:
            clubs_used: List of clubs used in the session
            shot_count: Number of shots in session
            **kwargs: Additional context for custom rules

        Returns:
            List of applicable tags
        """
        clubs_set = set(clubs_used)
        tags = []

        for rule_name, condition_fn, tag in self._rules:
            try:
                if condition_fn(clubs_set, shot_count, **kwargs):
                    tags.append(tag)
            except Exception:
                # Skip rule if it fails
                continue

        return tags

    def add_custom_rule(
        self,
        rule_name: str,
        condition_fn: callable,
        tag: str
    ) -> None:
        """
        Add a custom tagging rule.

        Args:
            rule_name: Name of the rule (for reference)
            condition_fn: Function(clubs: Set[str], shot_count: int, **kwargs) -> bool
            tag: Tag to apply if condition is true
        """
        self._rules.append((rule_name, condition_fn, tag))


class SessionContextParser:
    """
    Parses session context strings to extract club names and session types.

    Many Uneekor session names contain embedded club information:
    - "Warmup PW" -> session_type='warmup', club='PW'
    - "Wedge 50" -> session_type=None, club='GW' (50 degree)
    - "8 Iron Dst Trainer" -> session_type='drill', club='8 Iron'
    - "Sgt Rd1" -> session_type='sim_round', club=None

    Usage:
        parser = SessionContextParser()
        result = parser.parse("Warmup PW")
        print(result)  # {'session_type': 'warmup', 'club': 'PW', 'context': 'warmup'}
    """

    # Session type patterns (order matters - more specific first)
    SESSION_TYPE_PATTERNS = [
        # Simulated Golf Tour patterns
        (r'\bSgt\b.*\bRd\s*(\d)', 'sim_round', 'Sim Golf Tour Round'),
        (r'\bSgt\b', 'sim_round', 'Sim Golf Tour'),
        # Practice modes
        (r'\bWarmup\b|\bWmup\b', 'warmup', 'Warmup'),
        (r'\bBag\s*Mapping\b', 'bag_mapping', 'Bag Mapping'),
        (r'\bDst\b.*\b(Trainer|Compressor)\b', 'drill', 'Distance Trainer'),
        (r'\bDst\b', 'drill', 'Distance Work'),
        (r'\bDrill\b', 'drill', 'Drill'),
        (r'\bPar\s*3\b', 'practice', 'Par 3 Practice'),
        # Course play
        (r'\bSilvertip\b|\bShadow\s*Ridge\b|\bKapalua\b|\bWailaie\b|\bPlantation\b|\bSony\s*Open\b|\bNewport\b', 'sim_round', 'Course Play'),
    ]

    # Club extraction patterns (look for club names embedded in context)
    CLUB_EXTRACTION_PATTERNS = [
        # "Warmup PW", "Warmup 50 Degree"
        (r'\b(PW|GW|AW|SW|LW)\b', None),  # Wedge abbreviations
        (r'\b(\d{1,2})\s*(?:Iron|i)\b', '{0} Iron'),  # "8 Iron", "8i"
        (r'\b(\d{1,2})\s*(?:deg(?:ree)?|\u00b0)', 'degree'),  # "50 degree", "50°"
        (r'\bWedge\s*(\d{2})\b', 'degree'),  # "Wedge 50"
        (r'\bWedge\s*(Pitching|Sand|Lob|Gap|Approach)\b', 'wedge_type'),  # "Wedge Pitching"
        (r'\b(Driver|Putter)\b', None),
        (r'\b(\d)\s*(?:Wood|W)\b', '{0} Wood'),  # "3 Wood", "3W"
        (r'\b(\d)\s*(?:Hybrid|H)\b', '{0} Hybrid'),  # "4 Hybrid", "4H"
        # "Dst Compressor 8" or "Compressor 8" -> 8 Iron
        (r'(?:Dst\s*)?Compressor\s*(\d)\b', '{0} Iron'),
    ]

    # Wedge type to abbreviation
    WEDGE_TYPE_MAP = {
        'pitching': 'PW',
        'sand': 'SW',
        'lob': 'LW',
        'gap': 'GW',
        'approach': 'AW',
    }

    # Degree to wedge mapping
    DEGREE_TO_WEDGE = {
        44: 'PW', 45: 'PW', 46: 'PW', 47: 'PW', 48: 'PW',
        49: 'GW', 50: 'GW', 51: 'GW', 52: 'GW',
        53: 'SW', 54: 'SW', 55: 'SW', 56: 'SW',
        57: 'LW', 58: 'LW', 59: 'LW', 60: 'LW', 61: 'LW', 62: 'LW',
    }

    def __init__(self):
        """Initialize the parser."""
        self._type_patterns = [
            (re.compile(pattern, re.IGNORECASE), stype, label)
            for pattern, stype, label in self.SESSION_TYPE_PATTERNS
        ]
        self._club_patterns = [
            (re.compile(pattern, re.IGNORECASE), fmt)
            for pattern, fmt in self.CLUB_EXTRACTION_PATTERNS
        ]
        self._normalizer = ClubNameNormalizer()

    def parse(self, context_string: str) -> Dict[str, Optional[str]]:
        """
        Parse a session context string.

        Args:
            context_string: Raw context/club string from Uneekor

        Returns:
            Dict with 'session_type', 'club', 'context_label' keys
        """
        if not context_string:
            return {'session_type': None, 'club': None, 'context_label': None}

        result = {
            'session_type': None,
            'club': None,
            'context_label': None,
            'original': context_string,
        }

        # Try to detect session type
        for pattern, stype, label in self._type_patterns:
            if pattern.search(context_string):
                result['session_type'] = stype
                result['context_label'] = label
                break

        # Try to extract club name
        for pattern, fmt in self._club_patterns:
            match = pattern.search(context_string)
            if match:
                if fmt == 'degree':
                    # Handle degree-based wedge
                    try:
                        degree = int(match.group(1))
                        result['club'] = self.DEGREE_TO_WEDGE.get(degree, f'{degree} Wedge')
                    except (ValueError, IndexError):
                        continue
                elif fmt == 'wedge_type':
                    # Handle "Wedge Pitching" -> "PW"
                    wedge_type = match.group(1).lower()
                    result['club'] = self.WEDGE_TYPE_MAP.get(wedge_type, 'PW')
                elif fmt:
                    # Format with captured group
                    result['club'] = fmt.format(match.group(1))
                else:
                    # Direct match
                    result['club'] = match.group(1).upper() if len(match.group(1)) <= 2 else match.group(1)

                # Normalize the extracted club
                if result['club']:
                    result['club'] = self._normalizer.normalize(result['club']).normalized
                break

        # If no session type detected but no club found, it might be a standard club
        if not result['session_type'] and not result['club']:
            # Try normalizing the whole string as a club name
            norm_result = self._normalizer.normalize(context_string)
            if norm_result.confidence >= 0.9:
                result['club'] = norm_result.normalized

        return result

    def extract_club(self, context_string: str) -> Optional[str]:
        """
        Convenience method to extract just the club name.

        Args:
            context_string: Raw context/club string

        Returns:
            Normalized club name or None
        """
        return self.parse(context_string).get('club')

    def extract_session_type(self, context_string: str) -> Optional[str]:
        """
        Convenience method to extract just the session type.

        Args:
            context_string: Raw context/club string

        Returns:
            Session type or None
        """
        return self.parse(context_string).get('session_type')

    def parse_listing_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse dates from listing page (e.g., 'January 15, 2026').

        The Uneekor portal listing page displays session dates in various formats.
        This method handles common date formats found in the DOM.

        Args:
            date_str: Date string from listing page

        Returns:
            datetime object or None if parsing failed
        """
        if not date_str:
            return None

        date_str = date_str.strip()

        # Common date formats from Uneekor listing page
        formats = [
            '%B %d, %Y',      # January 15, 2026
            '%b %d, %Y',      # Jan 15, 2026
            '%m/%d/%Y',       # 01/15/2026
            '%Y-%m-%d',       # 2026-01-15
            '%d %B %Y',       # 15 January 2026
            '%d %b %Y',       # 15 Jan 2026
            '%B %d %Y',       # January 15 2026 (no comma)
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None


@dataclass
class ClassificationResult:
    """Result of session classification."""
    category: str  # practice, sim_round, drill, warmup, fitting
    confidence: float  # 0.0 to 1.0
    signals: Dict[str, Any] = field(default_factory=dict)
    display_type: str = ''  # Human-readable type for display

    def __post_init__(self):
        if not self.display_type:
            self.display_type = {
                'sim_round': 'Sim Round',
                'practice': 'Practice',
                'drill': 'Drill',
                'warmup': 'Warmup',
                'fitting': 'Fitting',
            }.get(self.category, self.category.replace('_', ' ').title())


class SessionClassifier:
    """
    Classifies sessions by analyzing club distribution, shot sequencing, and
    pattern matching to distinguish indoor sim rounds from practice sessions.

    Sim rounds exhibit distinct patterns:
    - Wide club variety spanning multiple categories (woods, irons, wedges)
    - Hole-like shot sequences (driver/wood -> iron -> wedge cycles)
    - Shot counts in typical round ranges (14-80 shots)
    - Even distribution across club categories (no single category > 60%)
    - May include 1 Iron (common in simulator play)

    Practice sessions exhibit:
    - Concentrated club usage (blocks of same club)
    - Single club category dominance (>60% one type)
    - Variable shot counts with repetition patterns

    Usage:
        classifier = SessionClassifier()

        # Classify from shot-level club list (ordered by shot sequence)
        result = classifier.classify(clubs=['Driver', '7 Iron', 'PW', 'Driver', '5 Iron', 'SW', ...])

        # Classify with additional shot data
        result = classifier.classify_with_data(shots_df)
    """

    # Club category definitions for classification
    LONG_CLUBS = {'Driver', '1 Iron', '2 Iron', '3 Iron',
                  '2 Wood', '3 Wood', '4 Wood', '5 Wood', '7 Wood', '9 Wood',
                  '2 Hybrid', '3 Hybrid', '4 Hybrid', '5 Hybrid', '6 Hybrid', '7 Hybrid'}
    MID_CLUBS = {'4 Iron', '5 Iron', '6 Iron', '7 Iron'}
    SHORT_CLUBS = {'8 Iron', '9 Iron', 'PW', 'GW', 'AW', 'SW', 'LW'}
    PUTTER = {'Putter'}

    # All irons including 1 Iron (important for sim round detection)
    ALL_IRONS = {f'{i} Iron' for i in range(1, 10)}
    ALL_WEDGES = {'PW', 'GW', 'AW', 'SW', 'LW'}
    ALL_WOODS = {'Driver', '2 Wood', '3 Wood', '4 Wood', '5 Wood', '7 Wood', '9 Wood'}
    ALL_HYBRIDS = {f'{i} Hybrid' for i in range(2, 8)}

    # Round-typical shot count range
    MIN_ROUND_SHOTS = 14  # 14 tee shots (par 3s don't use driver)
    MAX_ROUND_SHOTS = 80  # 18 holes, ~4.4 shots/hole average
    IDEAL_ROUND_SHOTS = (50, 72)  # Most common range for 18-hole sim

    def __init__(self):
        """Initialize the classifier."""
        pass

    def classify(
        self,
        clubs: List[str],
        context_hint: Optional[str] = None,
    ) -> ClassificationResult:
        """
        Classify a session based on its club usage pattern.

        Args:
            clubs: List of club names per shot (in sequence order).
                   Must be normalized canonical names.
            context_hint: Optional context string from Uneekor (e.g., "Sgt Rd1")
                         that may provide a direct classification signal.

        Returns:
            ClassificationResult with category, confidence, and diagnostic signals.
        """
        if not clubs:
            return ClassificationResult(
                category='practice',
                confidence=0.5,
                signals={'reason': 'empty_clubs'},
            )

        total = len(clubs)
        unique_clubs = set(clubs)
        num_unique = len(unique_clubs)

        # --- Check context hint first (highest priority) ---
        if context_hint:
            parser = SessionContextParser()
            parsed = parser.parse(context_hint)
            if parsed.get('session_type') == 'sim_round':
                return ClassificationResult(
                    category='sim_round',
                    confidence=0.95,
                    signals={'reason': 'context_hint', 'context': context_hint},
                )

        # --- Warmup: very few shots ---
        if total < 10:
            return ClassificationResult(
                category='warmup',
                confidence=0.9,
                signals={'reason': 'low_shot_count', 'total': total},
            )

        # --- Drill: 1-2 clubs with significant repetition ---
        if num_unique <= 2 and total >= 20:
            return ClassificationResult(
                category='drill',
                confidence=0.9,
                signals={'reason': 'repetitive_clubs', 'unique_clubs': num_unique, 'total': total},
            )

        # --- Compute category signals for round vs practice ---
        signals = self._compute_signals(clubs, unique_clubs, total)

        # --- Sim round detection ---
        round_score = self._compute_round_score(signals, clubs, total)

        if round_score >= 0.7:
            confidence = min(0.95, 0.6 + round_score * 0.35)
            return ClassificationResult(
                category='sim_round',
                confidence=confidence,
                signals=signals,
            )

        # --- Fitting detection: 1 club, very high volume ---
        if num_unique == 1 and total >= 50:
            return ClassificationResult(
                category='fitting',
                confidence=0.8,
                signals={'reason': 'single_club_high_volume', 'club': list(unique_clubs)[0], 'total': total},
            )

        # --- Default: practice ---
        return ClassificationResult(
            category='practice',
            confidence=0.8,
            signals=signals,
        )

    def classify_with_data(self, df) -> ClassificationResult:
        """
        Classify a session using full shot data (DataFrame).

        Extracts club sequence and uses carry distances to improve
        classification accuracy (e.g., distance variation across a round).

        Args:
            df: DataFrame with at least 'club' column. Optionally 'carry',
                'session_type', 'shot_id' columns.

        Returns:
            ClassificationResult with category, confidence, and signals.
        """
        if df is None or df.empty:
            return ClassificationResult(
                category='practice',
                confidence=0.5,
                signals={'reason': 'empty_dataframe'},
            )

        clubs = df['club'].dropna().tolist() if 'club' in df.columns else []
        if not clubs:
            return ClassificationResult(
                category='practice',
                confidence=0.5,
                signals={'reason': 'no_club_data'},
            )

        # Get context hint from session_type if available
        context_hint = None
        if 'session_type' in df.columns:
            session_types = df['session_type'].dropna().unique()
            if len(session_types) > 0:
                context_hint = session_types[0]

        result = self.classify(clubs, context_hint=context_hint)

        # Enhance with carry distance analysis if available
        if 'carry' in df.columns and result.category in ('practice', 'sim_round'):
            carry_data = df['carry'].replace([0, 99999], float('nan')).dropna()
            if len(carry_data) >= 10:
                carry_range = carry_data.max() - carry_data.min()
                carry_cv = carry_data.std() / carry_data.mean() if carry_data.mean() > 0 else 0

                # Rounds have high carry variance (driver vs wedge)
                # Practice tends to be lower (same club repetition)
                result.signals['carry_range'] = round(carry_range, 1)
                result.signals['carry_cv'] = round(carry_cv, 3)

                if carry_cv > 0.35 and result.category == 'practice':
                    # High carry variation suggests round-like behavior
                    round_score = result.signals.get('round_score', 0)
                    if round_score >= 0.5:
                        result.category = 'sim_round'
                        result.confidence = min(0.85, result.confidence + 0.1)
                        result.signals['upgraded_by'] = 'carry_variance'
                        result.display_type = 'Sim Round'

        return result

    def _compute_signals(
        self,
        clubs: List[str],
        unique_clubs: Set[str],
        total: int,
    ) -> Dict[str, Any]:
        """Compute classification signals from club distribution and sequencing."""
        club_counts = Counter(clubs)

        # Category counts
        long_count = sum(1 for c in clubs if c in self.LONG_CLUBS)
        mid_count = sum(1 for c in clubs if c in self.MID_CLUBS)
        short_count = sum(1 for c in clubs if c in self.SHORT_CLUBS)
        putter_count = sum(1 for c in clubs if c in self.PUTTER)

        # Category diversity: how many categories are represented
        categories_present = sum(1 for count in [long_count, mid_count, short_count, putter_count] if count > 0)

        # Dominance: max category proportion
        max_category = max(long_count, mid_count, short_count, putter_count) if total > 0 else 0
        dominance = max_category / total if total > 0 else 0

        # 1 Iron presence (common in sim rounds)
        has_1_iron = '1 Iron' in unique_clubs

        # Shot sequence analysis
        sequence_info = self._analyze_shot_sequence(clubs)

        # Repetition analysis: consecutive same-club blocks
        repetition_ratio = self._compute_repetition_ratio(clubs)

        return {
            'total': total,
            'unique_clubs': len(unique_clubs),
            'club_list': sorted(unique_clubs),
            'long_count': long_count,
            'mid_count': mid_count,
            'short_count': short_count,
            'putter_count': putter_count,
            'categories_present': categories_present,
            'dominance': round(dominance, 3),
            'has_1_iron': has_1_iron,
            'repetition_ratio': round(repetition_ratio, 3),
            **sequence_info,
        }

    def _compute_round_score(
        self,
        signals: Dict[str, Any],
        clubs: List[str],
        total: int,
    ) -> float:
        """
        Compute a composite score (0-1) indicating how likely this is a sim round.

        Factors:
        - Club variety (5+ unique clubs)
        - Category diversity (3+ categories represented)
        - Low dominance (no category > 60%)
        - Shot count in round range
        - Hole-like sequences detected
        - Low repetition ratio (not block practice)
        - 1 Iron presence (bonus)
        """
        score = 0.0
        weights_total = 0.0

        # Factor 1: Club variety (weight 1.5)
        unique = signals.get('unique_clubs', 0)
        if unique >= 8:
            score += 1.5
        elif unique >= 5:
            score += 1.0
        elif unique >= 3:
            score += 0.3
        weights_total += 1.5

        # Factor 2: Category diversity (weight 2.0) — strongest signal
        categories = signals.get('categories_present', 0)
        if categories >= 3:
            score += 2.0
        elif categories == 2:
            score += 0.5
        weights_total += 2.0

        # Factor 3: Low dominance (weight 1.5)
        dominance = signals.get('dominance', 1.0)
        if dominance <= 0.35:
            score += 1.5
        elif dominance <= 0.50:
            score += 1.0
        elif dominance <= 0.60:
            score += 0.5
        weights_total += 1.5

        # Factor 4: Shot count in round range (weight 1.0)
        if self.MIN_ROUND_SHOTS <= total <= self.MAX_ROUND_SHOTS:
            score += 1.0
            if self.IDEAL_ROUND_SHOTS[0] <= total <= self.IDEAL_ROUND_SHOTS[1]:
                score += 0.3  # Bonus for ideal range
        weights_total += 1.3

        # Factor 5: Hole-like sequences (weight 2.0) — strongest signal
        hole_sequences = signals.get('hole_sequences', 0)
        if hole_sequences >= 9:  # Half a round+
            score += 2.0
        elif hole_sequences >= 5:
            score += 1.5
        elif hole_sequences >= 3:
            score += 1.0
        elif hole_sequences >= 1:
            score += 0.4
        weights_total += 2.0

        # Factor 6: Low repetition (weight 1.0)
        repetition = signals.get('repetition_ratio', 1.0)
        if repetition <= 0.15:
            score += 1.0  # Very little block practice
        elif repetition <= 0.30:
            score += 0.6
        elif repetition <= 0.50:
            score += 0.2
        weights_total += 1.0

        # Factor 7: 1 Iron presence (bonus 0.3)
        if signals.get('has_1_iron'):
            score += 0.3
        weights_total += 0.3

        round_score = score / weights_total if weights_total > 0 else 0
        signals['round_score'] = round(round_score, 3)
        return round_score

    def _analyze_shot_sequence(self, clubs: List[str]) -> Dict[str, Any]:
        """
        Analyze the shot sequence for hole-like patterns.

        A hole-like pattern is a transition from a long club to progressively
        shorter clubs: driver/wood -> mid iron -> short iron/wedge.

        Returns dict with:
            hole_sequences: count of detected hole-like sequences
            avg_hole_length: average shots per detected hole
            transition_count: number of long-to-short transitions
        """
        if len(clubs) < 3:
            return {'hole_sequences': 0, 'avg_hole_length': 0, 'transition_count': 0}

        # Classify each shot into tier: 0=long, 1=mid, 2=short, 3=putter, -1=unknown
        tiers = []
        for club in clubs:
            if club in self.LONG_CLUBS:
                tiers.append(0)
            elif club in self.MID_CLUBS:
                tiers.append(1)
            elif club in self.SHORT_CLUBS:
                tiers.append(2)
            elif club in self.PUTTER:
                tiers.append(3)
            else:
                tiers.append(-1)

        # Detect hole-like sequences:
        # A hole starts with tier 0 (long club) and progresses to tier 2+ (short)
        hole_sequences = 0
        hole_lengths = []
        transition_count = 0

        i = 0
        while i < len(tiers):
            # Look for a hole start: long club (tier 0)
            if tiers[i] == 0:
                hole_start = i
                max_tier_seen = 0
                j = i + 1

                # Walk forward looking for progression
                while j < len(tiers):
                    current_tier = tiers[j]
                    if current_tier == -1:
                        j += 1
                        continue

                    # A new long club could be start of next hole
                    if current_tier == 0 and j > hole_start + 1:
                        break

                    if current_tier > max_tier_seen:
                        max_tier_seen = current_tier
                        transition_count += 1

                    j += 1

                # Valid hole: started with long club, reached short/wedge
                if max_tier_seen >= 2:
                    hole_sequences += 1
                    hole_lengths.append(j - hole_start)

                i = j
            else:
                i += 1

        avg_hole_length = sum(hole_lengths) / len(hole_lengths) if hole_lengths else 0

        return {
            'hole_sequences': hole_sequences,
            'avg_hole_length': round(avg_hole_length, 1),
            'transition_count': transition_count,
        }

    def _compute_repetition_ratio(self, clubs: List[str]) -> float:
        """
        Compute how much of the session is "block practice" (consecutive same-club).

        Returns a ratio (0-1) where:
        - 0.0 = every shot is a different club (round-like)
        - 1.0 = all shots are the same club (drill-like)

        Specifically: fraction of shots that are part of a consecutive
        same-club run of 3+ shots.
        """
        if len(clubs) < 3:
            return 0.0

        # Find runs of 3+ consecutive same club
        block_shots = 0
        i = 0
        while i < len(clubs):
            run_len = 1
            while i + run_len < len(clubs) and clubs[i + run_len] == clubs[i]:
                run_len += 1
            if run_len >= 3:
                block_shots += run_len
            i += run_len

        return block_shots / len(clubs)

    def get_category_breakdown(self, clubs: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get a detailed breakdown of club category distribution.

        Returns a dict with category names as keys and dicts of
        count, percentage, and clubs as values.
        """
        total = len(clubs)
        if total == 0:
            return {}

        categories = OrderedDict([
            ('Long Game', {'clubs': self.LONG_CLUBS, 'count': 0, 'items': []}),
            ('Mid Irons', {'clubs': self.MID_CLUBS, 'count': 0, 'items': []}),
            ('Short Game', {'clubs': self.SHORT_CLUBS, 'count': 0, 'items': []}),
            ('Putter', {'clubs': self.PUTTER, 'count': 0, 'items': []}),
        ])

        for club in clubs:
            for cat_name, cat_data in categories.items():
                if club in cat_data['clubs']:
                    cat_data['count'] += 1
                    if club not in cat_data['items']:
                        cat_data['items'].append(club)
                    break

        result = {}
        for cat_name, cat_data in categories.items():
            if cat_data['count'] > 0:
                result[cat_name] = {
                    'count': cat_data['count'],
                    'pct': round(cat_data['count'] / total * 100, 1),
                    'clubs': sorted(cat_data['items']),
                }

        return result


# Singleton instances for convenience
_normalizer: Optional[ClubNameNormalizer] = None
_session_namer: Optional[SessionNamer] = None
_auto_tagger: Optional[AutoTagger] = None
_context_parser: Optional[SessionContextParser] = None
_session_classifier: Optional[SessionClassifier] = None


def get_normalizer() -> ClubNameNormalizer:
    """Get the singleton ClubNameNormalizer instance."""
    global _normalizer
    if _normalizer is None:
        _normalizer = ClubNameNormalizer()
    return _normalizer


def get_session_namer() -> SessionNamer:
    """Get the singleton SessionNamer instance."""
    global _session_namer
    if _session_namer is None:
        _session_namer = SessionNamer()
    return _session_namer


def get_auto_tagger() -> AutoTagger:
    """Get the singleton AutoTagger instance."""
    global _auto_tagger
    if _auto_tagger is None:
        _auto_tagger = AutoTagger()
    return _auto_tagger


def normalize_club(club_name: str) -> str:
    """Convenience function to normalize a single club name."""
    return get_normalizer().normalize(club_name).normalized


def normalize_clubs(club_names: List[str]) -> List[str]:
    """Convenience function to normalize multiple club names."""
    return get_normalizer().normalize_all(club_names)


def get_context_parser() -> SessionContextParser:
    """Get the singleton SessionContextParser instance."""
    global _context_parser
    if _context_parser is None:
        _context_parser = SessionContextParser()
    return _context_parser


def parse_session_context(context_string: str) -> Dict[str, Optional[str]]:
    """Convenience function to parse a session context string."""
    return get_context_parser().parse(context_string)


def extract_club_from_context(context_string: str) -> Optional[str]:
    """Convenience function to extract club name from context string."""
    return get_context_parser().extract_club(context_string)


def parse_listing_date(date_str: str) -> Optional[datetime]:
    """Convenience function to parse a date from listing page."""
    return get_context_parser().parse_listing_date(date_str)


def get_session_classifier() -> SessionClassifier:
    """Get the singleton SessionClassifier instance."""
    global _session_classifier
    if _session_classifier is None:
        _session_classifier = SessionClassifier()
    return _session_classifier


def classify_session(clubs: List[str], context_hint: Optional[str] = None) -> ClassificationResult:
    """Convenience function to classify a session from its club list."""
    return get_session_classifier().classify(clubs, context_hint=context_hint)


def classify_session_df(df) -> ClassificationResult:
    """Convenience function to classify a session from a DataFrame."""
    return get_session_classifier().classify_with_data(df)
