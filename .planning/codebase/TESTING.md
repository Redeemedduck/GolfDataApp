# Testing Patterns

**Analysis Date:** 2026-02-09

## Test Framework

**Runner:**
- `unittest` (standard library)
- Compatible with `pytest` (uses `unittest.TestCase` syntax)
- Config: `.github/workflows/ci.yml` defines CI test run

**Assertion Library:**
- Built-in unittest assertions: `assertEqual`, `assertIn`, `assertIsNone`, `assertGreater`, `assertTrue`, `assertRaises`
- No external assertion library

**Run Commands:**
```bash
# Run all tests (unittest discovery)
python -m unittest discover -s tests -v

# Run single test file
python -m unittest tests.unit.test_local_coach
python -m unittest tests.integration.test_automation_flow

# Run single test class
python -m unittest tests.unit.test_exceptions.TestDatabaseError

# Run single test method
python -m unittest tests.unit.test_exceptions.TestDatabaseError.test_with_operation_and_table

# Syntax validation (CI linting)
python -m py_compile app.py golf_db.py local_coach.py exceptions.py
python -m py_compile automation/*.py ml/*.py utils/*.py services/ai/*.py
```

## Test File Organization

**Location:**
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- E2E tests: `tests/e2e/`
- Shared fixtures: `tests/conftest.py`

**Naming:**
- Test files: `test_*.py`
- Test classes: `Test*` (e.g., `TestGolfDB`, `TestDatabaseError`)
- Test methods: `test_*` (e.g., `test_save_and_get_session_data`)
- Descriptive test names that describe the scenario: `test_duplicate_session_returns_false`, `test_invalid_field_rejected_by_allowlist`

**Structure:**
```
tests/
├── conftest.py                    # Shared fixtures
├── test_golf_db.py               # Golf DB module tests
├── test_scraper.py               # Scraper tests
│
├── unit/                         # Unit tests (single module/function)
│   ├── __init__.py
│   ├── test_local_coach.py      # LocalCoach intent detection, response generation
│   ├── test_ml_models.py        # Shot shape classification, swing flaw detection
│   ├── test_exceptions.py       # Exception hierarchy and message formatting
│   ├── test_naming_conventions.py
│   ├── test_credential_manager.py
│   ├── test_date_parsing.py
│   └── test_observability.py
│
├── integration/                  # Integration tests (multiple modules)
│   ├── __init__.py
│   ├── test_automation_flow.py  # Session discovery, deduplication, backfill
│   └── test_date_reclassification.py
│
└── e2e/                         # End-to-end tests (full flows)
    ├── __init__.py
    ├── test_coach_flow.py       # Complete coach interaction
    └── test_data_flow.py        # Data import → analysis → export
```

## Test Structure

**Suite Organization:**

```python
import unittest
from exceptions import ValidationError

class TestGolfDB(unittest.TestCase):
    """Test group for golf_db module."""

    def setUp(self):
        """Run before each test."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test.db")
        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.init_db()

    def tearDown(self):
        """Run after each test."""
        self.tmpdir.cleanup()

    def test_save_and_get_session_data(self):
        """Test that saved shots can be retrieved."""
        shot = {
            "shot_id": "s1",
            "session_id": "sess1",
            "club": "Driver",
            "carry": 250,
        }
        golf_db.save_shot(shot)

        df = golf_db.get_session_data("sess1")
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["shot_id"], "s1")
```

**Patterns:**
- `setUp()`: Initialize fixtures before each test (temporary DB, mock objects)
- `tearDown()`: Cleanup after each test (delete temp files, restore state)
- One assertion per test method (or logically related assertions)
- Descriptive assertion messages via test method names

## Mocking

**Framework:** `unittest.mock` (standard library)

**Common Patterns:**

```python
from unittest.mock import Mock, patch, AsyncMock

# Mock external service
with patch('golf_db.supabase') as mock_supabase:
    mock_supabase.table().select().execute.return_value = Mock(data=[...])
    # Test code that calls supabase

# Mock function return
@patch('automation.uneekor_portal.UneekorPortal.get_sessions')
def test_backfill(self, mock_get_sessions):
    mock_get_sessions.return_value = [SessionInfo(...), ...]
    # Test code

# AsyncMock for async operations
mock_browser = AsyncMock()
mock_browser.goto.return_value = None
```

**What to Mock:**
- External APIs: Supabase, Gemini, Uneekor portal
- File I/O: os.path, open(), file operations
- Browser interactions: Playwright Page, Browser
- Time/datetime: For deterministic tests

**What NOT to Mock:**
- Internal database functions (use temp SQLite instead)
- Exception classes (test actual exceptions)
- Data processing logic (test with real data)
- Local coach logic (test with real method calls)

Example from `test_automation_flow.py`:
```python
@unittest.skipUnless(HAS_DEPS, "playwright not installed")
class TestSessionDeduplication(unittest.TestCase):
    """Test that duplicate sessions are correctly handled."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_discovery.db")
        self.discovery = SessionDiscovery(db_path=self.db_path)
        self.discovery.init_tables()
```

## Fixtures and Factories

**Test Data:**

Fixtures defined in `tests/conftest.py`:

```python
@pytest.fixture
def temp_db_path():
    """Provide a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "test.db")

@pytest.fixture
def sample_shot_data():
    """Provide sample shot data for testing."""
    return {
        "shot_id": "shot_001",
        "session_id": "session_001",
        "club": "Driver",
        "carry": 250,
        "total": 270,
        "ball_speed": 165,
        "club_speed": 110,
        "smash": 1.5,
        "launch_angle": 12.5,
        "back_spin": 2500,
        "side_spin": 150,
    }

@pytest.fixture
def populated_golf_db(golf_db_instance, sample_shots_batch):
    """Provide a golf_db with sample data already inserted."""
    for shot in sample_shots_batch:
        golf_db_instance.save_shot(shot)
    return golf_db_instance
```

**Available Fixtures in conftest.py:**

| Fixture | Returns | Purpose |
|---------|---------|---------|
| `temp_db_path` | str | Path to temporary SQLite database (auto-cleaned) |
| `golf_db_instance` | module | Initialized golf_db with Supabase disabled |
| `populated_golf_db` | module | golf_db pre-loaded with 10 sample shots |
| `sample_shot_data` | dict | Single shot with realistic Driver metrics |
| `sample_shots_batch` | list[dict] | 10 shots with varying carry distances |
| `sample_session_info` | callable | Factory for SessionInfo objects |
| `discovery_db` | SessionDiscovery | Initialized discovery with temp DB |
| `ml_test_dataframe` | pd.DataFrame | 100-row DataFrame with synthetic launch data (seeded with np.random.seed(42)) |
| `mock_rate_limiter` | RateLimiter | Permissive rate limiter (1000 req/min) |
| `backfill_config` | BackfillConfig | Basic config for backfill tests (dry_run=True) |
| `local_coach` | LocalCoach | Stateless LocalCoach instance |
| `swing_data_good` | dict | Good swing metrics (0 degrees, centered) |
| `swing_data_flawed` | dict | Flawed swing metrics (over-the-top, off-center) |

**Location:**
- Fixture definitions: `tests/conftest.py`
- Used in all test files via pytest fixture injection

## Coverage

**Requirements:** No coverage threshold enforced

**View Coverage:**
```bash
# Install coverage module
pip install coverage

# Run with coverage
coverage run -m unittest discover -s tests
coverage report -m --include=.
coverage html
```

## Test Types

**Unit Tests** (`tests/unit/`):
- Scope: Single function or class method in isolation
- Dependencies: Mocked or faked
- Examples:
  - `test_exceptions.py`: Exception hierarchy, message formatting
  - `test_local_coach.py`: Intent detection, response generation (no database calls)
  - `test_ml_models.py`: Shot shape classification, swing flaw detection (standalone logic)
  - `test_naming_conventions.py`: Club name normalization patterns
  - `test_date_parsing.py`: Date extraction and validation

**Integration Tests** (`tests/integration/`):
- Scope: Multiple modules working together
- Dependencies: Real instances (temp DB, but no cloud APIs)
- Examples:
  - `test_automation_flow.py`: Session discovery → deduplication → backfill with checkpoint/resume
  - `test_date_reclassification.py`: Date extraction from Uneekor listing page and database updates

**E2E Tests** (`tests/e2e/`):
- Scope: Complete user workflows
- Dependencies: Real app components, mocked external APIs
- Examples:
  - `test_coach_flow.py`: User query → intent detection → response generation → UI rendering
  - `test_data_flow.py`: Import data → save to DB → sync to Supabase → render analytics

## Common Patterns

**Async Testing:**

Tests use `unittest` which doesn't natively support async. Async code tested via:
1. Mocking async calls with `AsyncMock`
2. Or wrapping in sync test using `asyncio.run()`

Example (hypothetical, if async code added):
```python
from unittest.mock import AsyncMock
import asyncio

class TestAsyncFunction(unittest.TestCase):
    def test_async_backfill(self):
        # Option 1: Mock the async call
        with patch('automation.UneekorPortal.fetch_sessions') as mock:
            mock.return_value = AsyncMock(return_value=[...])

        # Option 2: Run async code in test
        result = asyncio.run(async_function())
        self.assertEqual(result, expected)
```

**Error Testing:**

Test exception raising using `assertRaises`:

```python
def test_update_shot_metadata_rejects_invalid_field(self):
    """SQL injection should be prevented by field allowlist."""
    shot = {"shot_id": "s1", "session_id": "sess1", "club": "Driver", "carry": 250}
    golf_db.save_shot(shot)

    # Attempt SQL injection via field parameter
    with self.assertRaises(ValueError) as ctx:
        golf_db.update_shot_metadata(
            ["s1"],
            "club; DROP TABLE shots; --",  # Injection attempt
            "Hacked"
        )
    self.assertIn("Invalid field", str(ctx.exception))
    self.assertIn("Allowed fields", str(ctx.exception))
```

**Skipping Tests with Dependencies:**

Tests skip gracefully if optional dependencies missing:

```python
import unittest

try:
    import numpy as np
    import pandas as pd
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

@unittest.skipUnless(HAS_DEPS, "pandas not installed")
class TestLocalCoach(unittest.TestCase):
    def test_intent_detection(self):
        ...
```

## CI/CD Integration

**GitHub Actions** (`.github/workflows/ci.yml`):

1. **test job:** Runs on Python 3.10, 3.11, 3.12
   - Install dependencies: `pip install -r requirements.txt`
   - Lint with py_compile: `python -m py_compile app.py golf_db.py ...`
   - Run tests: `python -m unittest discover -s tests -v`

2. **validate-ml job:** Runs after test passes
   - Validate ML modules import without errors
   - Validate LocalCoach instantiates
   - Validate provider registry functions work

```yaml
- name: Run tests
  run: python -m unittest discover -s tests -v

- name: Validate ML modules load
  run: |
    python -c "from ml.train_models import DistancePredictor; print('OK')"
    python -c "from local_coach import LocalCoach; c = LocalCoach(); print('OK')"
```

## Test Utilities

**tempfile for isolation:**
```python
self.tmpdir = tempfile.TemporaryDirectory()
self.db_path = os.path.join(self.tmpdir.name, "test.db")
# ...
self.tmpdir.cleanup()
```

**Seeded random for reproducibility:**
```python
np.random.seed(42)
df = pd.DataFrame({
    'ball_speed': np.random.normal(160, 10, 100),
    'carry': np.random.normal(250, 15, 100),
})
```

**Context managers for mocking:**
```python
with patch('module.function') as mock:
    mock.return_value = expected
    # Test code
# Mock automatically cleaned up
```

## Known Test Gaps

- **E2E Streamlit tests:** Pages not directly unit-testable (require st.run)
- **Playwright automation tests:** Limited to discovery/dedup logic; actual browser interactions require manual testing
- **Supabase integration:** Tests mock Supabase; real cloud sync tested in staging environment
- **Concurrency:** WAL mode tested in isolation; concurrent reader/writer load testing not automated

---

*Testing analysis: 2026-02-09*
