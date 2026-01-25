"""
Naming Conventions for Clubs, Sessions, and Automatic Tagging.

Provides consistent naming across all imported data:
- Club names standardized (e.g., "7I" -> "7 Iron")
- Session names generated from metadata
- Automatic tagging based on session characteristics

Standard Club Names:
    Woods:   Driver, 3 Wood, 5 Wood, 7 Wood
    Hybrids: 3 Hybrid, 4 Hybrid, 5 Hybrid, 6 Hybrid
    Irons:   3 Iron, 4 Iron, 5 Iron, 6 Iron, 7 Iron, 8 Iron, 9 Iron
    Wedges:  PW, GW, SW, LW (or with degrees: PW (46), SW (56), etc.)
    Putter:  Putter

Session Naming Patterns:
    Practice:  "Practice - Jan 25, 2026"
    Drill:     "Drill - Driver Consistency - Jan 25, 2026"
    Round:     "Pebble Beach Round - Jan 25, 2026"
    Fitting:   "Fitting - Driver - Jan 25, 2026"
    Warmup:    "Warmup - Jan 25, 2026"
"""

import re
from datetime import datetime
from typing import Optional, List, Dict, Set, Tuple
from dataclasses import dataclass


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
        # Driver variations
        (r'^(dr|driver|1w|1 wood|1wood|d)$', 'Driver'),

        # Woods
        (r'^(2w|2 wood|2wood|fairway 2)$', '2 Wood'),
        (r'^(3w|3 wood|3wood|fairway 3|3wd)$', '3 Wood'),
        (r'^(4w|4 wood|4wood|fairway 4)$', '4 Wood'),
        (r'^(5w|5 wood|5wood|fairway 5|5wd)$', '5 Wood'),
        (r'^(7w|7 wood|7wood|fairway 7)$', '7 Wood'),
        (r'^(9w|9 wood|9wood|fairway 9)$', '9 Wood'),

        # Hybrids
        (r'^(2h|2 hybrid|hybrid 2|2hy|2 hy|rescue 2)$', '2 Hybrid'),
        (r'^(3h|3 hybrid|hybrid 3|3hy|3 hy|rescue 3)$', '3 Hybrid'),
        (r'^(4h|4 hybrid|hybrid 4|4hy|4 hy|rescue 4)$', '4 Hybrid'),
        (r'^(5h|5 hybrid|hybrid 5|5hy|5 hy|rescue 5)$', '5 Hybrid'),
        (r'^(6h|6 hybrid|hybrid 6|6hy|6 hy|rescue 6)$', '6 Hybrid'),
        (r'^(7h|7 hybrid|hybrid 7|7hy|7 hy|rescue 7)$', '7 Hybrid'),

        # Irons
        (r'^(1i|1 iron|iron 1|1-iron|one iron)$', '1 Iron'),
        (r'^(2i|2 iron|iron 2|2-iron|two iron)$', '2 Iron'),
        (r'^(3i|3 iron|iron 3|3-iron|three iron)$', '3 Iron'),
        (r'^(4i|4 iron|iron 4|4-iron|four iron)$', '4 Iron'),
        (r'^(5i|5 iron|iron 5|5-iron|five iron)$', '5 Iron'),
        (r'^(6i|6 iron|iron 6|6-iron|six iron)$', '6 Iron'),
        (r'^(7i|7 iron|iron 7|7-iron|seven iron)$', '7 Iron'),
        (r'^(8i|8 iron|iron 8|8-iron|eight iron)$', '8 Iron'),
        (r'^(9i|9 iron|iron 9|9-iron|nine iron)$', '9 Iron'),

        # Wedges - specific lofts
        (r'^(pw|p wedge|pitching wedge|pitching|p\.w\.|46\s*deg|46\s*\u00b0)$', 'PW'),
        (r'^(gw|g wedge|gap wedge|gap|g\.w\.|50\s*deg|50\s*\u00b0|52\s*deg|52\s*\u00b0)$', 'GW'),
        (r'^(aw|a wedge|approach wedge|approach|a\.w\.)$', 'AW'),
        (r'^(sw|s wedge|sand wedge|sand|s\.w\.|54\s*deg|54\s*\u00b0|56\s*deg|56\s*\u00b0)$', 'SW'),
        (r'^(lw|l wedge|lob wedge|lob|l\.w\.|58\s*deg|58\s*\u00b0|60\s*deg|60\s*\u00b0|62\s*deg|62\s*\u00b0)$', 'LW'),

        # Generic wedge with degree
        (r'^(\d{2})\s*(deg|degree|\u00b0).*$', '_DEGREE_WEDGE'),

        # Putter
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
                else:
                    return NormalizationResult(
                        original=original,
                        normalized=name,
                        confidence=0.95,
                        matched_pattern=pattern.pattern
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

    def __init__(self):
        """Initialize auto-tagger with default rules."""
        self._rules: List[Tuple[str, callable, str]] = [
            # (rule_name, condition_function, tag_to_apply)
            ('driver_only', self._is_driver_only, 'Driver Focus'),
            ('wedge_only', self._is_wedge_only, 'Short Game'),
            ('full_bag', self._is_full_bag, 'Full Bag'),
            ('high_volume', self._is_high_volume, 'High Volume'),
            ('warmup', self._is_warmup, 'Warmup'),
            ('iron_work', self._is_iron_work, 'Iron Work'),
            ('woods_focus', self._is_woods_focus, 'Woods Focus'),
        ]

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
        iron_clubs = {c for c in clubs if 'Iron' in c}
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


# Singleton instances for convenience
_normalizer: Optional[ClubNameNormalizer] = None
_session_namer: Optional[SessionNamer] = None
_auto_tagger: Optional[AutoTagger] = None


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
