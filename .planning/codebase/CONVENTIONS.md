# Coding Conventions

**Analysis Date:** 2026-02-09

## Naming Patterns

**Files:**
- Lowercase with underscores: `local_coach.py`, `golf_db.py`, `naming_conventions.py`
- Components: `render_*.py` (e.g., `metrics_card.py`, `trend_chart.py`)
- Test files: `test_*.py` (unit tests in `tests/unit/`, integration in `tests/integration/`)
- Modules organized in directories: `automation/`, `ml/`, `services/ai/`, `components/`

**Functions:**
- `snake_case` for all function definitions
- Private functions prefixed with single underscore: `_normalize_read_mode()`, `_ensure_default_tags()`
- Helper utilities are private by default
- Public API functions have no underscore prefix
- Render functions: `render_metrics_row()`, `render_*()` pattern for Streamlit components (stateless, return None, take DataFrame as first arg)

**Variables:**
- `snake_case` for all variables and parameters
- Constants in `UPPER_CASE`: `INTENT_PATTERNS`, `STANDARD_CLUBS`, `SQLITE_DB_PATH`
- Private module-level variables use underscore prefix: `_load_ml_models()`
- Descriptive names over abbreviations: `session_date` not `sess_date`, `carry_distance` → `carry`

**Types:**
- `PascalCase` for classes: `LocalCoach`, `CoachResponse`, `ValidationError`, `DatabaseError`, `SessionInfo`
- Enum-like classes: `ShotShape`, `SwingFlaw`, `ImportStatus`
- Dataclasses with `@dataclass` decorator: `CoachResponse`, `NormalizationResult`, `SessionInfo`

## Code Style

**Formatting:**
- 4-space indentation (standard Python)
- No formatter configured; keep diffs clean
- Line length: practical limit (~100 chars, but no hard rule)
- Empty lines: 2 blank lines between top-level functions/classes, 1 blank line within class methods

**Linting:**
- CI runs `python -m py_compile` for syntax validation
- No ESLint, Prettier, or Black configured
- Manual code review for consistency

**Imports:**
Organized in three groups (separated by blank lines):
1. Standard library: `import os`, `import sys`, `import sqlite3`, `from pathlib import Path`
2. Third-party: `import pandas as pd`, `import numpy as np`, `import streamlit as st`
3. Local imports: `import golf_db`, `from exceptions import ValidationError`

Order within groups: alphabetical by module name.

**Conditional Imports:**
Used for optional dependencies (ML, pandas, etc.):
```python
try:
    from ml.train_models import DistancePredictor
    HAS_ML = True
except ImportError:
    HAS_ML = False
```

Path setup for tests:
```python
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

## Error Handling

**Pattern: Custom Exception Hierarchy**

All errors inherit from `GolfDataAppError` (base in `exceptions.py`):

```python
from exceptions import ValidationError, DatabaseError

if not validate_shot(data):
    raise ValidationError(
        "Invalid shot data: missing carry distance",
        field='carry',
        value=shot.get('carry')
    )

try:
    save_shot(data)
except DatabaseError as e:
    logger.error(f"Database error: {e}")
except ValidationError as e:
    logger.warning(f"Validation: {e}")
```

**Exception Types and Usage:**
- `ValidationError`: Data validation failures (field, value context)
- `DatabaseError`: Database operation failures (operation, table context)
- `ModelNotTrainedError`: ML model not available (model name context)
- `DataImportError`: Session/shot import failures (session_id, source context)
- `ConfigurationError`: Missing config (config_key context)
- `RateLimitError`: Rate limit exceeded (retry_after_seconds context)
- `AuthenticationError`: Auth failures (provider context)

All exceptions carry a `details` dict for logging context. Use with f-strings:
```python
except ValidationError as e:
    print(f"Error: {e}")  # Includes details in string repr
    print(e.details)     # Access raw dict
```

**Soft Deletions:**
Database deletions use "archive then delete" pattern (in `golf_db.py`):
1. Copy record to `shots_archive` table
2. Delete from main table
3. Record in `change_log` for audit trail

## Logging

**Framework:** None configured; uses print statements and f-strings

**Patterns:**
- Status messages: `print(f"Processing session {session_id}...")`
- Warnings on startup: `print("Warning: Supabase credentials not found. Cloud sync disabled.")`
- No structured logging configured (could add via environment var `GOLFDATA_LOGGING`)

**In comments:** Document why, not what:
```python
# Enable WAL mode for better concurrent access
# WAL (Write-Ahead Logging) allows readers and writers to operate simultaneously
cursor.execute("PRAGMA journal_mode=WAL")
```

## Comments

**When to Comment:**
- Algorithm explanations (e.g., rate limiting, D-plane shot shape theory)
- Non-obvious business logic (e.g., sentinel value `99999` for "no data")
- Configuration trade-offs
- Workarounds for portal limitations (e.g., Uneekor session date accuracy)

**JSDoc/Docstring Pattern:**
- All functions have docstrings (triple quotes)
- Include Args, Returns, Raises sections
- Module-level docstrings describe purpose and usage

Example from `golf_db.py`:
```python
def save_shot(data):
    """Save shot data to local SQLite and Supabase (hybrid).

    Args:
        data: Dict containing shot data. Must include 'id'/'shot_id' and 'session'/'session_id'.

    Raises:
        ValidationError: If shot_id or session_id is missing/null
    """
```

Example from `local_coach.py`:
```python
def _detect_intent(self, query: str) -> Tuple[str, Optional[str]]:
    """
    Detect the user's intent from their query.

    Args:
        query: User's question

    Returns:
        Tuple of (intent, extracted_entity)
    """
```

## Function Design

**Size:** Keep functions focused; most range 10-50 lines

**Parameters:**
- Prefer explicit keyword args in public APIs
- Use `None` as default for optional parameters
- Document required vs. optional in docstring

Example from `naming_conventions.py`:
```python
def normalize(self, club_name: str, strict: bool = False) -> NormalizationResult:
    """Normalize a club name.

    Args:
        club_name: Club name to normalize (required)
        strict: If True, only accept exact matches (optional, default False)
    """
```

**Return Values:**
- Return dataclass/NamedTuple for structured results: `CoachResponse`, `NormalizationResult`, `ClassificationResult`
- Return dict for payloads going to database
- Return list for collections
- Return bool for success/failure
- Return None for side-effect operations (e.g., `render_*()` in Streamlit components)

Example:
```python
# Structured return
response: CoachResponse = coach.get_response(query)

# Dict return
payload = {
    'shot_id': shot_id,
    'carry': carry,
    ...
}

# Bool return
is_new: bool = discovery.save_discovered_session(session)
```

## Module Design

**Exports:**
- Clear public API at top of module
- Conditional imports wrapped in try/except
- Private helpers start with `_`

Example structure in `local_coach.py`:
```python
# Public exports
@dataclass
class CoachResponse: ...

class LocalCoach: ...

# Private
def _load_ml_models(): ...
```

**Barrel Files:**
- `services/ai/__init__.py` exports registry functions: `list_providers()`, `get_provider()`
- `components/__init__.py` imports component functions for convenience
- `ml/__init__.py` uses `__getattr__` for lazy loading of optional ML dependencies

Example from `ml/__init__.py`:
```python
def __getattr__(name):
    # Lazy load ML modules on demand
    # Graceful degradation if dependencies missing
```

## Type Hints

**Usage:**
- Function signatures use type hints
- Return types annotated: `-> CoachResponse`, `-> Tuple[str, Optional[str]]`
- Collection types: `Dict[str, Any]`, `List[str]`, `Optional[pd.DataFrame]`

Example from `local_coach.py`:
```python
def _detect_intent(self, query: str) -> Tuple[str, Optional[str]]:
    def get_response(self, query: str) -> CoachResponse:
    def _load_ml_models(self) -> None:
```

## Data Field Naming

**Shot Data:**
- Carry distance: `carry` (yards)
- Total distance: `total` (yards)
- Ball speed: `ball_speed` (mph)
- Club speed: `club_speed` (mph)
- Smash factor: `smash` (ratio)
- Launch angle: `launch_angle` (degrees)
- Club face angle: `face_angle` (degrees)
- Club path: `club_path` (degrees)
- Spin rates: `back_spin`, `side_spin` (RPM)
- Impact location: `impact_x`, `impact_y` (inches)
- Sentinel value: `99999` = "no data" (cleaned via `clean_value()`)

**Session Data:**
- Session ID: `session_id`
- Session date: `session_date` (when practice occurred)
- Date imported: `date_added` (when data was added to DB)
- Session type: `session_type` (e.g., "Practice", "Round")

## SQL & Database

**Parameterized Queries:**
All user-provided values use placeholders (prevents SQL injection):
```python
sql = f"INSERT INTO shots ({columns}) VALUES ({placeholders})"
cursor.execute(sql, list(payload.values()))
```

**Field Allowlist:**
`update_shot_metadata()` enforces allowed fields to prevent injection:
```python
ALLOWED_UPDATE_FIELDS = ['shot_tag', 'session_type', ...]
if field not in ALLOWED_UPDATE_FIELDS:
    raise ValueError(f"Invalid field: {field}")
```

**WAL Mode:**
SQLite uses WAL (Write-Ahead Logging) for concurrent reads/writes:
```python
cursor.execute("PRAGMA journal_mode=WAL")
```

---

*Convention analysis: 2026-02-09*
