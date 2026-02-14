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
from typing import Optional, List, Dict, Set, Tuple, Union
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

        # Reversed forms: 'Wedge Pitching' -> PW, 'Wedge 50' -> GW
        (r'^wedge\s*(pitching|p)$', 'PW'),
        (r'^wedge\s*(gap|g)$', 'GW'),
        (r'^wedge\s*(sand|s)$', 'SW'),
        (r'^wedge\s*(lob|l)$', 'LW'),
        (r'^wedge\s*(approach|a)$', 'AW'),
        (r'^wedge\s*(\d{2})$', '_WEDGE_DEGREE_NUM'),

        # No-space iron: 'Iron7' -> '7 Iron'
        (r'^iron(\d)$', '_IRON_NOSPACE'),
        (r'^wood\s*(\d)$', '_WOOD_NOSPACE'),
        (r'^hybrid(\d)$', '_HYBRID_NOSPACE'),

        # Standalone single digit: '9' -> '9 Iron' (common Uneekor shorthand)
        (r'^([1-9])$', '_SINGLE_DIGIT_IRON'),

        # Standalone bare degree: '56' -> SW, '50' -> GW
        (r'^(\d{2})$', '_BARE_DEGREE'),

        # "M" prefix shorthand: 'M 7' -> '7 Iron', 'M 56' -> SW
        (r'^m\s+(\d{1,2})(?:\s+iron)?$', '_M_PREFIX'),

        # Uneekor default format: 'IRON7 | MEDIUM', 'DRIVER | PREMIUM'
        (r'^driver\s*\|.*$', 'Driver'),
        (r'^iron(\d)\s*\|.*$', '_UNEEKOR_IRON'),
        (r'^wood(\d)\s*\|.*$', '_UNEEKOR_WOOD'),
        (r'^hybrid(\d)\s*\|.*$', '_UNEEKOR_HYBRID'),
        (r'^wedge(\d{2})\s*\|.*$', '_UNEEKOR_WEDGE'),
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
                elif name.startswith('_UNEEKOR_'):
                    try:
                        num = match.group(1)
                        club_type = name.replace('_UNEEKOR_', '').capitalize()
                        if club_type == 'Iron':
                            normalized = f'{num} Iron'
                        elif club_type == 'Wood':
                            normalized = f'{num} Wood'
                        elif club_type == 'Hybrid':
                            normalized = f'{num} Hybrid'
                        elif club_type == 'Wedge':
                            degree = int(num)
                            normalized = self.DEGREE_TO_WEDGE.get(degree, f'{num} Wedge')
                        else:
                            normalized = f'{num} {club_type}'
                        return NormalizationResult(
                            original=original,
                            normalized=normalized,
                            confidence=0.95,
                            matched_pattern='uneekor_format'
                        )
                    except (ValueError, IndexError):
                        continue
                elif name == '_WEDGE_DEGREE_NUM':
                    try:
                        degree = int(match.group(1))
                        normalized = self.DEGREE_TO_WEDGE.get(degree, f'{degree} Wedge')
                        return NormalizationResult(
                            original=original,
                            normalized=normalized,
                            confidence=0.9,
                            matched_pattern='wedge_degree_num'
                        )
                    except (ValueError, IndexError):
                        continue
                elif name in ('_IRON_NOSPACE', '_WOOD_NOSPACE', '_HYBRID_NOSPACE'):
                    num = match.group(1)
                    club_type = name.replace('_', '').replace('NOSPACE', '').capitalize()
                    return NormalizationResult(
                        original=original,
                        normalized=f'{num} {club_type}',
                        confidence=0.95,
                        matched_pattern='nospace_format'
                    )
                elif name == '_SINGLE_DIGIT_IRON':
                    num = match.group(1)
                    return NormalizationResult(
                        original=original,
                        normalized=f'{num} Iron',
                        confidence=0.9,
                        matched_pattern='single_digit_iron'
                    )
                elif name == '_BARE_DEGREE':
                    try:
                        degree = int(match.group(1))
                        if degree in self.DEGREE_TO_WEDGE:
                            return NormalizationResult(
                                original=original,
                                normalized=self.DEGREE_TO_WEDGE[degree],
                                confidence=0.9,
                                matched_pattern='bare_degree'
                            )
                    except (ValueError, IndexError):
                        pass
                    continue
                elif name == '_M_PREFIX':
                    try:
                        num = int(match.group(1))
                        if num <= 9:
                            normalized = f'{num} Iron'
                        elif num in self.DEGREE_TO_WEDGE:
                            normalized = self.DEGREE_TO_WEDGE[num]
                        else:
                            continue
                        return NormalizationResult(
                            original=original,
                            normalized=normalized,
                            confidence=0.9,
                            matched_pattern='m_prefix'
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

    # --- Club categories for distribution-based session type detection ---

    DRIVER_CLUBS = {'Driver'}
    IRON_CLUBS = {f'{i} Iron' for i in range(1, 10)}
    WEDGE_CLUBS = {'PW', 'GW', 'AW', 'SW', 'LW'}
    WOOD_CLUBS = {'3 Wood', '5 Wood', '7 Wood', '2 Wood', '4 Wood', '9 Wood'}
    HYBRID_CLUBS = {f'{i} Hybrid' for i in range(2, 7)}

    def detect_session_type(self, clubs: List[str]) -> str:
        """
        Detect session type based on club distribution (shot-level list).

        Uses the proportion of shots per club category to classify:
        - 'Warmup' if <10 total shots
        - 'Driver Focus' if >60% driver shots
        - 'Iron Work' if >60% iron shots
        - 'Short Game' if >60% wedge shots
        - 'Woods Focus' if >60% wood/hybrid shots
        - 'Mixed Practice' otherwise

        Args:
            clubs: List of club names per shot (with repetitions).
                   Should be normalized canonical names.

        Returns:
            Session type string for display.
        """
        if not clubs:
            return 'Mixed Practice'

        total = len(clubs)

        if total < 10:
            return 'Warmup'

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
        # Bare wedge degree near warmup context: "Warmup 50", "50 Warmup"
        (r'(?:warmup|wmup|warm)\s+(50|52|54|56|58|60)\b', 'degree'),
        (r'\b(50|52|54|56|58|60)\s+(?:warmup|wmup|warm)', 'degree'),
        # Bare iron digit near warmup/drill context: "warmup 8 dst", "8 Dst Warmup"
        (r'(?:warmup|wmup|dst|trainer|drill)\s+([6-9])\b', '{0} Iron'),
        (r'\b([6-9])\s+(?:dst|warmup|wmup|trainer|drill)', '{0} Iron'),
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


# Singleton instances for convenience
_normalizer: Optional[ClubNameNormalizer] = None
_session_namer: Optional[SessionNamer] = None
_auto_tagger: Optional[AutoTagger] = None
_context_parser: Optional[SessionContextParser] = None


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


def normalize_with_context(raw_value: str) -> Dict[str, Union[Optional[str], float]]:
    """
    Two-tier normalization: club normalizer first, session-context parser fallback.

    Returns a consistent schema regardless of which tier handled the input:
    {
        'club': Optional[str],
        'session_type': Optional[str],
        'original': str,
        'confidence': float,
    }
    """
    if not raw_value:
        return {
            'club': None,
            'session_type': None,
            'original': raw_value,
            'confidence': 0.0,
        }

    normalizer_result = get_normalizer().normalize(raw_value)

    # High-confidence club names should pass through directly.
    if normalizer_result.confidence >= 0.9:
        return {
            'club': normalizer_result.normalized,
            'session_type': None,
            'original': raw_value,
            'confidence': normalizer_result.confidence,
        }

    context = get_context_parser().parse(raw_value)
    extracted_club = context.get('club')
    session_type = context.get('session_type')

    # Context parse confidence is heuristic because parser output has no score.
    confidence = 0.8 if extracted_club else (0.4 if session_type else 0.1)

    return {
        'club': extracted_club,
        'session_type': session_type,
        'original': raw_value,
        'confidence': confidence,
    }


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
