# Codebase Cleanup & Test Coverage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove ~3,500 lines of dead cloud infrastructure, improve test coverage from ~15% to meaningful coverage of all core modules, and consolidate documentation from 20+ to 7 root-level markdown files.

**Architecture:** Three sequential phases — delete dead weight first (safe, no deps), then add tests (validates nothing broke), then consolidate docs (reflects new reality). Each phase gets its own commit.

**Tech Stack:** Python unittest, git, bash for file operations

---

## Phase 1: Remove Dead Weight

### Task 1: Delete Cloud Infrastructure Files

**Files:**
- Delete: `cloudbuild.yaml` (71 lines)
- Delete: `deploy.sh` (68 lines)
- Delete: `setup_cron.sh` (111 lines)
- Delete: `Dockerfile` (85 lines)
- Delete: `docker-compose.yml` (129 lines)
- Delete: `.dockerignore` (85 lines)

**Step 1: Delete the files**

```bash
cd /Users/max1/Documents/GitHub/GolfDataApp
git rm cloudbuild.yaml deploy.sh setup_cron.sh Dockerfile docker-compose.yml .dockerignore
```

**Step 2: Verify no active imports reference these files**

```bash
grep -r "cloudbuild\|deploy\.sh\|setup_cron\|Dockerfile\|docker-compose" --include="*.py" .
```

Expected: No matches in active Python code.

**Step 3: Commit**

```bash
git add -A && git commit -m "chore: remove unused Cloud Run deployment infrastructure"
```

---

### Task 2: Delete Cloud Scripts

**Files:**
- Delete: `scripts/supabase_to_bigquery.py` (270 lines)
- Delete: `scripts/vertex_ai_analysis.py` (261 lines)
- Delete: `scripts/post_session.py` (128 lines)
- Delete: `scripts/auto_sync.py` (177 lines)
- Delete: `scripts/gemini_analysis.py` (imports BigQuery, cloud-only)

**Step 1: Delete the files**

```bash
git rm scripts/supabase_to_bigquery.py scripts/vertex_ai_analysis.py scripts/post_session.py scripts/auto_sync.py scripts/gemini_analysis.py
```

**Step 2: Verify no active imports**

```bash
grep -r "supabase_to_bigquery\|vertex_ai_analysis\|post_session\|auto_sync\|gemini_analysis" --include="*.py" . | grep -v "^./scripts/"
```

Expected: No matches outside scripts/ directory.

**Step 3: Commit**

```bash
git add -A && git commit -m "chore: remove unused cloud pipeline scripts (BigQuery, Vertex AI)"
```

---

### Task 3: Delete Cloud Schema and Cloud Requirements

**Files:**
- Delete: `bigquery_schema.json` (181 lines)
- Delete: `requirements_cloud.txt` (24 lines)

**Step 1: Delete the files**

```bash
git rm bigquery_schema.json requirements_cloud.txt
```

**Step 2: Commit**

```bash
git add -A && git commit -m "chore: remove BigQuery schema and cloud requirements file"
```

---

### Task 4: Delete Legacy Directory

**Files:**
- Delete entire `legacy/` directory (8 files, 656 lines):
  - `check_clubs.py`, `debug_scraper.py`, `debug_scraper2.py`, `debug_scraper3.py`
  - `golf_scraper_fixed.py`, `golf_scraper_selenium_backup.py`
  - `inspect_api_response.py`, `test_connection.py`

**Step 1: Verify no active imports from legacy/**

```bash
grep -r "from legacy\|import legacy" --include="*.py" . | grep -v "^./legacy/"
```

Expected: No matches.

**Step 2: Delete the directory**

```bash
git rm -r legacy/
```

**Step 3: Commit**

```bash
git add -A && git commit -m "chore: remove legacy debug scripts and old scraper backups"
```

---

### Task 5: Archive Historical Markdown and Delete Duplicate

**Files:**
- Create: `docs/archive/` directory
- Move to `docs/archive/`: `DEPLOYMENT_SUMMARY.md`, `PIPELINE_COMPLETE.md`, `PHASE1_SUMMARY.md`, `PHASE2_SUMMARY.md`, `PHASE3_SUMMARY.md`, `VERTEX_AI_SETUP.md`, `WORKFLOW_REVIEW.md`, `CLOUD_RUN_DEPLOYMENT.md`
- Delete: `IMPROVEMENT_PLAN.md` (duplicate of `IMPROVEMENT_ROADMAP.md`)

**Step 1: Create archive directory and move files**

```bash
mkdir -p docs/archive
git mv DEPLOYMENT_SUMMARY.md docs/archive/
git mv PIPELINE_COMPLETE.md docs/archive/
git mv PHASE1_SUMMARY.md docs/archive/
git mv PHASE2_SUMMARY.md docs/archive/
git mv PHASE3_SUMMARY.md docs/archive/
git mv VERTEX_AI_SETUP.md docs/archive/
git mv WORKFLOW_REVIEW.md docs/archive/
git mv CLOUD_RUN_DEPLOYMENT.md docs/archive/
git rm IMPROVEMENT_PLAN.md
```

**Step 2: Commit**

```bash
git add -A && git commit -m "chore: archive historical docs, delete duplicate IMPROVEMENT_PLAN.md"
```

---

### Task 6: Fix .gitignore

**Files:**
- Modify: `.gitignore`

**Step 1: Add missing entries**

The current `.gitignore` already covers `__pycache__/`, `*.py[cod]`, `*.db`, `.uneekor_cookies.enc`, `.uneekor_key`. But it has `*.db` which is too broad (blocks committing any .db file). It's missing:
- `*.db-shm`
- `*.db-wal`
- `/models/trained_*.pkl`
- `firebase-debug.log`

Add these entries to `.gitignore`:

```
# SQLite WAL files
*.db-shm
*.db-wal

# Trained ML models (too large for git)
/models/trained_*.pkl

# Firebase debug
firebase-debug.log
```

**Step 2: Remove tracked files that should be ignored**

```bash
git rm --cached golf_data.db golf_stats.db golf_stats.db-shm golf_stats.db-wal firebase-debug.log 2>/dev/null || true
```

**Step 3: Commit**

```bash
git add .gitignore && git commit -m "chore: fix .gitignore - add WAL files, model artifacts, firebase log"
```

---

### Task 7: Verify Phase 1 — Run existing tests

**Step 1: Run the full test suite**

```bash
python -m unittest discover -s tests -v 2>&1
```

Expected: At least 36 tests pass (the ones that ran before). No new failures.

**Step 2: Run py_compile on all active files**

```bash
python -m py_compile app.py golf_db.py local_coach.py exceptions.py
python -m py_compile automation/*.py
python -m py_compile ml/*.py
python -m py_compile utils/*.py
python -m py_compile services/ai/*.py services/ai/providers/*.py
```

Expected: All compile without errors.

---

## Phase 2: Improve Test Coverage

### Task 8: Add Skip Guards to Existing Tests

**Files:**
- Modify: `tests/test_golf_db.py`
- Modify: `tests/test_scraper.py`
- Modify: `tests/unit/test_local_coach.py`
- Modify: `tests/unit/test_ml_models.py`
- Modify: `tests/integration/test_date_reclassification.py`

**Step 1: Add skip guards**

Each file that fails on missing deps needs a guard at the top, before the test class. Pattern:

```python
import unittest

try:
    import pandas
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

@unittest.skipUnless(HAS_PANDAS, "pandas not installed")
class TestGolfDB(unittest.TestCase):
    ...
```

Apply to each file:
- `test_golf_db.py` — needs `pandas` guard
- `test_scraper.py` — needs `requests` guard
- `test_local_coach.py` — needs `pandas` guard
- `test_ml_models.py` — needs `numpy` and `sklearn` guards
- `test_date_reclassification.py` — needs `pandas` guard

**Step 2: Run full suite to verify clean execution**

```bash
python -m unittest discover -s tests -v 2>&1
```

Expected: No import errors. Tests either PASS or SKIP (no ERROR).

**Step 3: Commit**

```bash
git add tests/ && git commit -m "test: add skip guards for optional dependencies"
```

---

### Task 9: Test Naming Conventions Module

**Files:**
- Create: `tests/unit/test_naming_conventions.py`
- Test: `automation/naming_conventions.py`

**Step 1: Write the tests**

```python
"""Tests for automation.naming_conventions module."""

import unittest
from datetime import datetime
from automation.naming_conventions import (
    ClubNameNormalizer,
    SessionNamer,
    AutoTagger,
    normalize_club,
    normalize_clubs,
)


class TestClubNameNormalizer(unittest.TestCase):
    """Tests for ClubNameNormalizer."""

    def setUp(self):
        self.normalizer = ClubNameNormalizer()

    # --- Exact matches ---

    def test_exact_match_driver(self):
        result = self.normalizer.normalize("Driver")
        self.assertEqual(result.normalized, "Driver")
        self.assertEqual(result.confidence, 1.0)

    def test_exact_match_case_insensitive(self):
        result = self.normalizer.normalize("driver")
        self.assertEqual(result.normalized, "Driver")
        self.assertEqual(result.confidence, 1.0)

    def test_exact_match_7_iron(self):
        result = self.normalizer.normalize("7 Iron")
        self.assertEqual(result.normalized, "7 Iron")

    def test_exact_match_pw(self):
        result = self.normalizer.normalize("PW")
        self.assertEqual(result.normalized, "PW")

    # --- Alias patterns ---

    def test_alias_dr_to_driver(self):
        result = self.normalizer.normalize("dr")
        self.assertEqual(result.normalized, "Driver")

    def test_alias_7i_to_7_iron(self):
        result = self.normalizer.normalize("7i")
        self.assertEqual(result.normalized, "7 Iron")

    def test_alias_3w_to_3_wood(self):
        result = self.normalizer.normalize("3w")
        self.assertEqual(result.normalized, "3 Wood")

    def test_alias_4h_to_4_hybrid(self):
        result = self.normalizer.normalize("4h")
        self.assertEqual(result.normalized, "4 Hybrid")

    def test_alias_sand_to_sw(self):
        result = self.normalizer.normalize("sand")
        self.assertEqual(result.normalized, "SW")

    def test_alias_pitching_wedge(self):
        result = self.normalizer.normalize("pitching wedge")
        self.assertEqual(result.normalized, "PW")

    def test_alias_lob_to_lw(self):
        result = self.normalizer.normalize("lob")
        self.assertEqual(result.normalized, "LW")

    def test_alias_putter(self):
        result = self.normalizer.normalize("putt")
        self.assertEqual(result.normalized, "Putter")

    # --- Degree-based wedges ---

    def test_degree_56_to_sw(self):
        result = self.normalizer.normalize("56 deg")
        self.assertEqual(result.normalized, "SW")

    def test_degree_60_to_lw(self):
        result = self.normalizer.normalize("60 deg")
        self.assertEqual(result.normalized, "LW")

    def test_degree_46_to_pw(self):
        result = self.normalizer.normalize("46 deg")
        self.assertEqual(result.normalized, "PW")

    # --- Edge cases ---

    def test_empty_string(self):
        result = self.normalizer.normalize("")
        self.assertEqual(result.normalized, "Unknown")
        self.assertEqual(result.confidence, 0.0)

    def test_unknown_club(self):
        result = self.normalizer.normalize("banana")
        self.assertEqual(result.normalized, "Banana")
        self.assertLess(result.confidence, 0.5)

    def test_whitespace_handling(self):
        result = self.normalizer.normalize("  7i  ")
        self.assertEqual(result.normalized, "7 Iron")

    # --- Custom mappings ---

    def test_custom_mapping(self):
        self.normalizer.add_custom_mapping("my club", "7 Iron")
        result = self.normalizer.normalize("my club")
        self.assertEqual(result.normalized, "7 Iron")
        self.assertEqual(result.confidence, 1.0)

    # --- Batch normalization ---

    def test_normalize_all(self):
        result = self.normalizer.normalize_all(["dr", "7i", "pw"])
        self.assertEqual(result, ["Driver", "7 Iron", "PW"])

    # --- Report ---

    def test_normalization_report(self):
        report = self.normalizer.get_normalization_report(["Driver", "banana"])
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["high_confidence"], 1)
        self.assertEqual(report["low_confidence"], 1)


class TestConvenienceFunctions(unittest.TestCase):
    """Test module-level convenience functions."""

    def test_normalize_club(self):
        self.assertEqual(normalize_club("7i"), "7 Iron")

    def test_normalize_clubs(self):
        self.assertEqual(normalize_clubs(["dr", "pw"]), ["Driver", "PW"])


class TestSessionNamer(unittest.TestCase):
    """Tests for SessionNamer."""

    def setUp(self):
        self.namer = SessionNamer()
        self.date = datetime(2026, 1, 25)

    def test_practice_session(self):
        name = self.namer.generate_name("practice", self.date)
        self.assertEqual(name, "Practice - Jan 25, 2026")

    def test_drill_with_focus(self):
        name = self.namer.generate_name("drill", self.date, drill_focus="Driver Consistency")
        self.assertEqual(name, "Drill - Driver Consistency - Jan 25, 2026")

    def test_round_with_course(self):
        name = self.namer.generate_name("round", self.date, course_name="Pebble Beach")
        self.assertEqual(name, "Pebble Beach Round - Jan 25, 2026")

    def test_fitting_with_club(self):
        name = self.namer.generate_name("fitting", self.date, clubs_used=["Driver"])
        self.assertEqual(name, "Fitting - Driver - Jan 25, 2026")

    def test_unknown_type_capitalized(self):
        name = self.namer.generate_name("custom", self.date)
        self.assertEqual(name, "Custom - Jan 25, 2026")

    def test_infer_warmup(self):
        result = self.namer.infer_session_type(5, ["Driver"])
        self.assertEqual(result, "warmup")

    def test_infer_drill(self):
        result = self.namer.infer_session_type(50, ["Driver"])
        self.assertEqual(result, "fitting")

    def test_infer_practice(self):
        result = self.namer.infer_session_type(30, ["Driver", "7 Iron", "PW"])
        self.assertEqual(result, "practice")


class TestAutoTagger(unittest.TestCase):
    """Tests for AutoTagger."""

    def setUp(self):
        self.tagger = AutoTagger()

    def test_driver_focus(self):
        tags = self.tagger.auto_tag(["Driver"], 50)
        self.assertIn("Driver Focus", tags)

    def test_short_game(self):
        tags = self.tagger.auto_tag(["PW", "SW", "LW"], 30)
        self.assertIn("Short Game", tags)

    def test_full_bag(self):
        clubs = [f"{i} Iron" for i in range(3, 10)] + ["Driver", "3 Wood", "PW"]
        tags = self.tagger.auto_tag(clubs, 50)
        self.assertIn("Full Bag", tags)

    def test_high_volume(self):
        tags = self.tagger.auto_tag(["Driver", "7 Iron"], 150)
        self.assertIn("High Volume", tags)

    def test_warmup(self):
        tags = self.tagger.auto_tag(["Driver"], 5)
        self.assertIn("Warmup", tags)

    def test_iron_work(self):
        tags = self.tagger.auto_tag(["5 Iron", "6 Iron", "7 Iron"], 45)
        self.assertIn("Iron Work", tags)

    def test_custom_rule(self):
        self.tagger.add_custom_rule(
            "night_session",
            lambda clubs, count, **kw: count > 200,
            "Marathon"
        )
        tags = self.tagger.auto_tag(["Driver"], 250)
        self.assertIn("Marathon", tags)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the tests**

```bash
python -m unittest tests.unit.test_naming_conventions -v
```

Expected: All pass.

**Step 3: Commit**

```bash
git add tests/unit/test_naming_conventions.py && git commit -m "test: add comprehensive naming conventions tests"
```

---

### Task 10: Test Exceptions Module

**Files:**
- Create: `tests/unit/test_exceptions.py`
- Test: `exceptions.py`

**Step 1: Write the tests**

```python
"""Tests for exceptions module."""

import unittest
from exceptions import (
    GolfDataAppError,
    DatabaseError,
    ModelNotTrainedError,
    ValidationError,
    ConfigurationError,
    RateLimitError,
    AuthenticationError,
)


class TestGolfDataAppError(unittest.TestCase):
    """Tests for the base exception class."""

    def test_basic_message(self):
        e = GolfDataAppError("something went wrong")
        self.assertEqual(str(e), "something went wrong")
        self.assertEqual(e.message, "something went wrong")

    def test_with_details(self):
        e = GolfDataAppError("error", details={"key": "value"})
        self.assertEqual(e.details, {"key": "value"})
        self.assertIn("key=value", str(e))

    def test_empty_details(self):
        e = GolfDataAppError("error")
        self.assertEqual(e.details, {})

    def test_is_exception(self):
        self.assertTrue(issubclass(GolfDataAppError, Exception))


class TestDatabaseError(unittest.TestCase):
    def test_with_operation_and_table(self):
        e = DatabaseError("failed", operation="insert", table="shots")
        self.assertIn("operation=insert", str(e))
        self.assertIn("table=shots", str(e))

    def test_inherits_base(self):
        self.assertTrue(issubclass(DatabaseError, GolfDataAppError))


class TestModelNotTrainedError(unittest.TestCase):
    def test_default_message(self):
        e = ModelNotTrainedError("DistancePredictor")
        self.assertIn("DistancePredictor", str(e))
        self.assertEqual(e.details["model"], "DistancePredictor")

    def test_custom_message(self):
        e = ModelNotTrainedError("X", message="custom msg")
        self.assertEqual(e.message, "custom msg")


class TestValidationError(unittest.TestCase):
    def test_with_field_and_value(self):
        e = ValidationError("bad data", field="carry", value=-5)
        self.assertIn("field=carry", str(e))
        self.assertIn("value=-5", str(e))


class TestConfigurationError(unittest.TestCase):
    def test_with_config_key(self):
        e = ConfigurationError("missing", config_key="GEMINI_API_KEY")
        self.assertIn("config_key=GEMINI_API_KEY", str(e))


class TestRateLimitError(unittest.TestCase):
    def test_with_retry_after(self):
        e = RateLimitError("too fast", retry_after=30.0)
        self.assertEqual(e.details["retry_after_seconds"], 30.0)


class TestAuthenticationError(unittest.TestCase):
    def test_with_provider(self):
        e = AuthenticationError("login failed", provider="uneekor")
        self.assertIn("provider=uneekor", str(e))


class TestExceptionHierarchy(unittest.TestCase):
    """Verify all exceptions inherit from GolfDataAppError."""

    def test_all_subclass_base(self):
        for exc_cls in [
            DatabaseError,
            ModelNotTrainedError,
            ValidationError,
            ConfigurationError,
            RateLimitError,
            AuthenticationError,
        ]:
            self.assertTrue(
                issubclass(exc_cls, GolfDataAppError),
                f"{exc_cls.__name__} should inherit GolfDataAppError"
            )

    def test_catchable_as_base(self):
        try:
            raise DatabaseError("test")
        except GolfDataAppError:
            pass  # Should be caught


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the tests**

```bash
python -m unittest tests.unit.test_exceptions -v
```

Expected: All pass.

**Step 3: Commit**

```bash
git add tests/unit/test_exceptions.py && git commit -m "test: add exception hierarchy tests"
```

---

### Task 11: Test Observability Module

**Files:**
- Create: `tests/unit/test_observability.py`
- Test: `observability.py`

**Step 1: Write the tests**

```python
"""Tests for observability module."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import observability


class TestObservability(unittest.TestCase):
    """Tests for JSONL event logging."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self._orig_log_dir = observability.LOG_DIR
        observability.LOG_DIR = Path(self.temp_dir)

    def tearDown(self):
        observability.LOG_DIR = self._orig_log_dir
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_append_event_creates_file(self):
        result = observability.append_event("test.jsonl", {"action": "test"})
        self.assertTrue((Path(self.temp_dir) / "test.jsonl").exists())
        self.assertEqual(result["action"], "test")
        self.assertIn("timestamp", result)

    def test_append_event_jsonl_format(self):
        observability.append_event("test.jsonl", {"a": 1})
        observability.append_event("test.jsonl", {"b": 2})
        lines = (Path(self.temp_dir) / "test.jsonl").read_text().strip().split("\n")
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["a"], 1)
        self.assertEqual(json.loads(lines[1])["b"], 2)

    def test_read_latest_event(self):
        observability.append_event("test.jsonl", {"seq": 1})
        observability.append_event("test.jsonl", {"seq": 2})
        latest = observability.read_latest_event("test.jsonl")
        self.assertEqual(latest["seq"], 2)

    def test_read_latest_event_missing_file(self):
        result = observability.read_latest_event("nonexistent.jsonl")
        self.assertIsNone(result)

    def test_read_recent_events(self):
        for i in range(10):
            observability.append_event("test.jsonl", {"seq": i})
        recent = observability.read_recent_events("test.jsonl", limit=3)
        self.assertEqual(len(recent), 3)
        # Most recent first (reversed)
        self.assertEqual(recent[0]["seq"], 9)
        self.assertEqual(recent[2]["seq"], 7)

    def test_read_recent_events_missing_file(self):
        result = observability.read_recent_events("nonexistent.jsonl")
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the tests**

```bash
python -m unittest tests.unit.test_observability -v
```

Expected: All pass.

**Step 3: Commit**

```bash
git add tests/unit/test_observability.py && git commit -m "test: add observability JSONL logging tests"
```

---

### Task 12: Test Credential Manager Module

**Files:**
- Create: `tests/unit/test_credential_manager.py`
- Test: `automation/credential_manager.py`

**Step 1: Write the tests**

```python
"""Tests for automation.credential_manager module."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

from automation.credential_manager import CredentialManager, StoredCredentials


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography not installed")
class TestCredentialManager(unittest.TestCase):
    """Tests for CredentialManager with encryption."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Clear env vars that could interfere
        self.env_patcher = patch.dict(os.environ, {
            "K_SERVICE": "",
            "UNEEKOR_COOKIE_KEY": "",
        }, clear=False)
        self.env_patcher.start()
        # Remove K_SERVICE so is_cloud_run is False
        os.environ.pop("K_SERVICE", None)
        os.environ.pop("UNEEKOR_COOKIE_KEY", None)

        self.cm = CredentialManager(base_dir=self.temp_dir)

    def tearDown(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generates_key_file(self):
        self.assertTrue(Path(self.temp_dir, ".uneekor_key").exists())

    def test_save_and_load_roundtrip(self):
        storage_state = {
            "cookies": [{"name": "session", "value": "abc123"}],
            "origins": [],
        }
        self.assertTrue(self.cm.save_storage_state(storage_state, username="test"))
        loaded = self.cm.load_storage_state()
        self.assertEqual(loaded["cookies"][0]["value"], "abc123")

    def test_has_valid_credentials_after_save(self):
        storage_state = {"cookies": [], "origins": []}
        self.cm.save_storage_state(storage_state)
        self.assertTrue(self.cm.has_valid_credentials())

    def test_no_credentials_initially(self):
        self.assertFalse(self.cm.has_valid_credentials())

    def test_clear_credentials(self):
        storage_state = {"cookies": [], "origins": []}
        self.cm.save_storage_state(storage_state)
        self.assertTrue(self.cm.clear_credentials())
        self.assertFalse(self.cm.has_valid_credentials())

    def test_clear_nonexistent(self):
        self.assertFalse(self.cm.clear_credentials())

    def test_get_credential_info(self):
        info = self.cm.get_credential_info()
        self.assertIn("has_env_credentials", info)
        self.assertIn("has_stored_cookies", info)
        self.assertFalse(info["is_cloud_run"])

    def test_get_auth_method_interactive(self):
        self.assertEqual(self.cm.get_auth_method(), "interactive")

    def test_get_auth_method_cookies(self):
        self.cm.save_storage_state({"cookies": [], "origins": []})
        self.assertEqual(self.cm.get_auth_method(), "cookies")

    @patch.dict(os.environ, {"UNEEKOR_USERNAME": "user", "UNEEKOR_PASSWORD": "pass"})
    def test_get_auth_method_credentials(self):
        cm = CredentialManager(base_dir=self.temp_dir)
        self.assertEqual(cm.get_auth_method(), "credentials")

    @patch.dict(os.environ, {"UNEEKOR_USERNAME": "user", "UNEEKOR_PASSWORD": "pass"})
    def test_has_login_credentials(self):
        cm = CredentialManager(base_dir=self.temp_dir)
        self.assertTrue(cm.has_login_credentials())

    def test_no_login_credentials(self):
        self.assertFalse(self.cm.has_login_credentials())


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography not installed")
class TestCredentialManagerCloudRun(unittest.TestCase):
    """Tests for Cloud Run behavior."""

    @patch.dict(os.environ, {"K_SERVICE": "my-service"})
    def test_cloud_run_detected(self):
        cm = CredentialManager(base_dir=tempfile.mkdtemp())
        self.assertTrue(cm.is_cloud_run)

    @patch.dict(os.environ, {"K_SERVICE": "my-service"})
    def test_cloud_run_no_cookie_persistence(self):
        cm = CredentialManager(base_dir=tempfile.mkdtemp())
        self.assertFalse(cm.save_storage_state({"cookies": [], "origins": []}))
        self.assertFalse(cm.has_valid_credentials())


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the tests**

```bash
python -m unittest tests.unit.test_credential_manager -v
```

Expected: All pass (or skip if cryptography not installed).

**Step 3: Commit**

```bash
git add tests/unit/test_credential_manager.py && git commit -m "test: add credential manager encryption and auth tests"
```

---

### Task 13: Verify Phase 2 — Run Full Suite

**Step 1: Run all tests**

```bash
python -m unittest discover -s tests -v 2>&1
```

Expected: All tests pass or skip cleanly. No ERRORs.

**Step 2: Count results**

Note the total number of tests run, passed, skipped.

---

## Phase 3: Tighten Architecture

### Task 14: Update CI Pipeline

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: Remove deleted file references and add new test files to compile check**

The CI currently compiles:
```
python -m py_compile app.py golf_db.py local_coach.py exceptions.py
python -m py_compile automation/*.py
python -m py_compile ml/*.py
python -m py_compile utils/*.py
python -m py_compile services/ai/*.py services/ai/providers/*.py
```

This still works because we didn't delete any of these files. But verify that `automation/*.py` glob still works (it should — we only deleted files from `scripts/` and `legacy/`, not `automation/`).

No changes needed to `ci.yml` — the existing globs still resolve correctly. The deleted files were never in the compile list.

**Step 2: Verify CI would pass locally**

```bash
python -m py_compile app.py golf_db.py local_coach.py exceptions.py
python -m py_compile automation/*.py
python -m py_compile ml/*.py
python -m py_compile utils/*.py
python -m py_compile services/ai/*.py services/ai/providers/*.py
```

Expected: All pass.

---

### Task 15: Consolidate Root Markdown

**Files:**
- Read and merge: `CLAUDE_SETUP.md` content into `SETUP_GUIDE.md`
- Read and merge: `AGENTS.md` content into `CLAUDE.md`
- Delete after merge: `CLAUDE_SETUP.md`, `AGENTS.md`

**Step 1: Read both files to understand what to merge**

Read `CLAUDE_SETUP.md` and `SETUP_GUIDE.md`. Merge Claude Desktop MCP configuration content into the setup guide as a new section.

Read `AGENTS.md` and `CLAUDE.md`. Merge code style/conventions from AGENTS.md into CLAUDE.md's Key Conventions section.

**Step 2: Edit the target files and delete the source files**

```bash
git rm CLAUDE_SETUP.md AGENTS.md
```

**Step 3: Commit**

```bash
git add SETUP_GUIDE.md CLAUDE.md && git commit -m "docs: consolidate CLAUDE_SETUP and AGENTS into existing docs"
```

---

### Task 16: Update CLAUDE.md to Remove Cloud References

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update these sections:**

- **Common Commands**: Remove `docker build`, `docker compose`, `scripts/supabase_to_bigquery.py` commands
- **Architecture Overview → Data Flow**: Remove BigQuery/Vertex AI from diagram
- **Core Modules table**: Remove entries for deleted scripts
- **Environment Variables table**: Remove `GCP_PROJECT_ID`, `BQ_DATASET_ID`, etc. (if listed)
- **Database Schema table**: Keep all (none were cloud-only)
- **CI/CD section**: Keep as-is (still accurate)

**Step 2: Commit**

```bash
git add CLAUDE.md && git commit -m "docs: update CLAUDE.md to remove cloud infrastructure references"
```

---

### Task 17: Update README.md

**Files:**
- Modify: `README.md`

**Step 1: Read current README and simplify**

Remove any Cloud Run deployment sections, BigQuery references, and Vertex AI mentions. Ensure it describes the app as local-first + optional Supabase sync.

**Step 2: Commit**

```bash
git add README.md && git commit -m "docs: simplify README to reflect local-first architecture"
```

---

### Task 18: Final Verification

**Step 1: Run the full test suite one final time**

```bash
python -m unittest discover -s tests -v 2>&1
```

**Step 2: Run py_compile on everything**

```bash
python -m py_compile app.py golf_db.py local_coach.py exceptions.py
python -m py_compile automation/*.py
python -m py_compile ml/*.py
python -m py_compile utils/*.py
python -m py_compile services/ai/*.py services/ai/providers/*.py
```

**Step 3: Count remaining root markdown files**

```bash
ls *.md | wc -l
```

Expected: ~7 files (README, CLAUDE, QUICKSTART, SETUP_GUIDE, AUTOMATION_GUIDE, IMPROVEMENT_ROADMAP, changelog)

**Step 4: Verify git status is clean**

```bash
git status
```
