# Scraper Fix + Clean Re-import Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the scraper to use correct API fields (`club_name`, `client_created_date`) and re-import all 126 sessions with accurate club and date data.

**Architecture:** Add a `map_uneekor_club()` function to `naming_conventions.py` that maps Uneekor internal names (IRON1, DRIVER, etc.) to canonical club names. Fix `golf_scraper.py` to read `club_name` and `client_created_date` from the API response. Add a `reimport-all` CLI command that wipes shots and re-imports everything from the API.

**Tech Stack:** Python 3.10+, SQLite, unittest, requests (Uneekor API)

**Design Doc:** `docs/plans/2026-02-13-scraper-fix-reimport-design.md`

---

### Task 1: Add Uneekor-to-Canonical Club Mapping

**Files:**
- Modify: `automation/naming_conventions.py` (add at bottom, before convenience functions ~line 920)
- Test: `tests/unit/test_naming_conventions.py` (add new test class)

**Step 1: Write the failing tests**

Add to `tests/unit/test_naming_conventions.py`:

```python
from automation.naming_conventions import map_uneekor_club

class TestMapUneekorClub(unittest.TestCase):
    """Tests for Uneekor API club_name -> canonical mapping."""

    def test_driver(self):
        self.assertEqual(map_uneekor_club('DRIVER'), 'Driver')

    def test_iron3_is_driving_iron(self):
        self.assertEqual(map_uneekor_club('IRON3'), '3 Iron')

    def test_iron1_is_sim_round(self):
        self.assertEqual(map_uneekor_club('IRON1'), 'Sim Round')

    def test_wedge_pitching(self):
        self.assertEqual(map_uneekor_club('WEDGE_PITCHING'), 'PW')

    def test_wedge_50(self):
        self.assertEqual(map_uneekor_club('WEDGE_50'), 'GW')

    def test_wedge_56(self):
        self.assertEqual(map_uneekor_club('WEDGE_56'), 'SW')

    def test_wedge_60(self):
        self.assertEqual(map_uneekor_club('WEDGE_60'), 'LW')

    def test_wood2_cobra(self):
        self.assertEqual(map_uneekor_club('WOOD2'), '3 Wood (Cobra)')

    def test_wood3_tm(self):
        self.assertEqual(map_uneekor_club('WOOD3'), '3 Wood (TM)')

    def test_wood7(self):
        self.assertEqual(map_uneekor_club('WOOD7'), '7 Wood')

    def test_irons(self):
        self.assertEqual(map_uneekor_club('IRON4'), '4 Iron')
        self.assertEqual(map_uneekor_club('IRON5'), '5 Iron')
        self.assertEqual(map_uneekor_club('IRON6'), '6 Iron')
        self.assertEqual(map_uneekor_club('IRON7'), '7 Iron')
        self.assertEqual(map_uneekor_club('IRON8'), '8 Iron')
        self.assertEqual(map_uneekor_club('IRON9'), '9 Iron')

    def test_putter(self):
        self.assertEqual(map_uneekor_club('PUTTER'), 'Putter')

    def test_testing_clubs_map_to_other(self):
        self.assertEqual(map_uneekor_club('HYBRID1'), 'Other')
        self.assertEqual(map_uneekor_club('HYBRID3'), 'Other')
        self.assertEqual(map_uneekor_club('WEDGE_54'), 'Other')

    def test_unknown_returns_unknown(self):
        self.assertEqual(map_uneekor_club('FOOBAR'), 'Unknown')
        self.assertEqual(map_uneekor_club(''), 'Unknown')

    def test_none_returns_unknown(self):
        self.assertEqual(map_uneekor_club(None), 'Unknown')
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_naming_conventions.TestMapUneekorClub -v`
Expected: ImportError — `map_uneekor_club` doesn't exist yet

**Step 3: Implement the mapping**

Add to `automation/naming_conventions.py` before the `normalize_club()` function (~line 926):

```python
# Uneekor API club_name -> canonical club name mapping.
# The Uneekor API returns a 'club_name' field (e.g., 'IRON1', 'DRIVER')
# alongside the user-friendly 'name' field (e.g., 'warmup', 'dpc scottsdale').
# This mapping converts the API club_name to our canonical names.
UNEEKOR_TO_CANONICAL = {
    # In bag
    'DRIVER': 'Driver',
    'WOOD2': '3 Wood (Cobra)',
    'WOOD3': '3 Wood (TM)',
    'WOOD7': '7 Wood',
    'IRON3': '3 Iron',
    'IRON4': '4 Iron',
    'IRON5': '5 Iron',
    'IRON6': '6 Iron',
    'IRON7': '7 Iron',
    'IRON8': '8 Iron',
    'IRON9': '9 Iron',
    'WEDGE_PITCHING': 'PW',
    'WEDGE_50': 'GW',
    'WEDGE_56': 'SW',
    'WEDGE_60': 'LW',
    'PUTTER': 'Putter',
    # Sim round default (mixed clubs — user selects "1 Iron" during sim rounds)
    'IRON1': 'Sim Round',
    # Testing/fitting (not in bag)
    'HYBRID1': 'Other',
    'HYBRID3': 'Other',
    'WEDGE_54': 'Other',
}


def map_uneekor_club(uneekor_club_name: Optional[str]) -> str:
    """
    Map a Uneekor API club_name to a canonical club name.

    Args:
        uneekor_club_name: The club_name field from the Uneekor API
                           (e.g., 'IRON1', 'DRIVER', 'WEDGE_PITCHING')

    Returns:
        Canonical club name (e.g., '3 Iron', 'Driver', 'PW').
        Returns 'Unknown' for unrecognized names.
    """
    if not uneekor_club_name:
        return 'Unknown'
    return UNEEKOR_TO_CANONICAL.get(uneekor_club_name, 'Unknown')
```

Also add `map_uneekor_club` to the module's imports/exports and add the import in the test file's import line.

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_naming_conventions.TestMapUneekorClub -v`
Expected: All 13 tests PASS

**Step 5: Commit**

```bash
git add automation/naming_conventions.py tests/unit/test_naming_conventions.py
git commit -m "feat: add Uneekor API club_name to canonical mapping"
```

---

### Task 2: Update my_bag.json and bag_config

**Files:**
- Modify: `my_bag.json`
- Modify: `utils/bag_config.py` (add `get_uneekor_mapping()`, `get_special_categories()`)
- Test: `tests/unit/test_bag_config.py` (update existing tests + add new ones)

**Step 1: Write failing tests**

Add/update in `tests/unit/test_bag_config.py`:

```python
from utils.bag_config import (
    get_bag_order, get_club_sort_key, is_in_bag,
    get_smash_target, get_all_smash_targets,
    get_uneekor_mapping, get_special_categories, reload,
)


class TestBagConfig(unittest.TestCase):
    """Verify bag config loads correctly."""

    def test_bag_order_returns_list(self):
        order = get_bag_order()
        self.assertIsInstance(order, list)
        self.assertIn("Driver", order)

    def test_bag_order_includes_new_clubs(self):
        order = get_bag_order()
        self.assertIn("3 Iron", order)
        self.assertIn("4 Iron", order)
        self.assertIn("5 Iron", order)
        self.assertIn("7 Wood", order)
        self.assertIn("Putter", order)

    def test_bag_order_no_1_iron(self):
        """1 Iron was renamed to 3 Iron."""
        order = get_bag_order()
        self.assertNotIn("1 Iron", order)

    def test_club_sort_key_driver_first(self):
        self.assertEqual(get_club_sort_key("Driver"), 0)

    def test_is_in_bag_true(self):
        self.assertTrue(is_in_bag("Driver"))
        self.assertTrue(is_in_bag("7 Iron"))
        self.assertTrue(is_in_bag("3 Iron"))

    def test_is_in_bag_false_for_special(self):
        """Sim Round and Other are NOT in the bag."""
        self.assertFalse(is_in_bag("Sim Round"))
        self.assertFalse(is_in_bag("Other"))
        self.assertFalse(is_in_bag("Nonexistent"))

    def test_putter_in_bag(self):
        self.assertTrue(is_in_bag("Putter"))


class TestSmashTargets(unittest.TestCase):

    def test_get_smash_target_driver(self):
        target = get_smash_target("Driver")
        self.assertIsNotNone(target)
        self.assertAlmostEqual(target, 1.49, places=1)

    def test_get_smash_target_3_iron(self):
        target = get_smash_target("3 Iron")
        self.assertIsNotNone(target)


class TestUneekorMapping(unittest.TestCase):
    """Verify Uneekor mapping from bag config."""

    def test_get_uneekor_mapping(self):
        mapping = get_uneekor_mapping()
        self.assertIsInstance(mapping, dict)
        self.assertEqual(mapping['DRIVER'], 'Driver')
        self.assertEqual(mapping['IRON3'], '3 Iron')

    def test_get_special_categories(self):
        cats = get_special_categories()
        self.assertIsInstance(cats, list)
        names = [c['canonical'] for c in cats]
        self.assertIn('Sim Round', names)
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_bag_config -v`
Expected: Multiple failures (missing clubs, missing functions)

**Step 3: Update my_bag.json**

Replace contents of `my_bag.json`:

```json
{
  "clubs": [
    {"canonical": "Driver", "aliases": ["DR", "1W"], "uneekor": "DRIVER"},
    {"canonical": "3 Wood (Cobra)", "aliases": ["3W Cobra"], "uneekor": "WOOD2"},
    {"canonical": "3 Wood (TM)", "aliases": ["3W TM"], "uneekor": "WOOD3"},
    {"canonical": "7 Wood", "aliases": ["7W"], "uneekor": "WOOD7"},
    {"canonical": "3 Iron", "aliases": ["3I", "Driving Iron"], "uneekor": "IRON3"},
    {"canonical": "4 Iron", "aliases": ["4I"], "uneekor": "IRON4"},
    {"canonical": "5 Iron", "aliases": ["5I"], "uneekor": "IRON5"},
    {"canonical": "6 Iron", "aliases": ["6I"], "uneekor": "IRON6"},
    {"canonical": "7 Iron", "aliases": ["7I"], "uneekor": "IRON7"},
    {"canonical": "8 Iron", "aliases": ["8I"], "uneekor": "IRON8"},
    {"canonical": "9 Iron", "aliases": ["9I"], "uneekor": "IRON9"},
    {"canonical": "PW", "aliases": ["Pitching Wedge"], "uneekor": "WEDGE_PITCHING"},
    {"canonical": "GW", "aliases": ["50", "Gap Wedge", "50 Degree"], "uneekor": "WEDGE_50"},
    {"canonical": "SW", "aliases": ["56", "Sand Wedge"], "uneekor": "WEDGE_56"},
    {"canonical": "LW", "aliases": ["60", "Lob Wedge"], "uneekor": "WEDGE_60"},
    {"canonical": "Putter", "aliases": ["PT"], "uneekor": "PUTTER"}
  ],
  "special_categories": [
    {"canonical": "Sim Round", "uneekor": "IRON1", "exclude_from_club_analytics": true},
    {"canonical": "Other", "uneekor": ["HYBRID1", "HYBRID3", "WEDGE_54"], "exclude_from_club_analytics": true}
  ],
  "bag_order": [
    "Driver", "3 Wood (Cobra)", "3 Wood (TM)", "7 Wood",
    "3 Iron", "4 Iron", "5 Iron", "6 Iron", "7 Iron", "8 Iron", "9 Iron",
    "PW", "GW", "SW", "LW", "Putter"
  ],
  "smash_targets": {
    "Driver": 1.49,
    "3 Wood (Cobra)": 1.45,
    "3 Wood (TM)": 1.45,
    "7 Wood": 1.42,
    "3 Iron": 1.36,
    "4 Iron": 1.35,
    "5 Iron": 1.34,
    "6 Iron": 1.34,
    "7 Iron": 1.33,
    "8 Iron": 1.31,
    "9 Iron": 1.29,
    "PW": 1.24,
    "GW": 1.22,
    "SW": 1.20,
    "LW": 1.18
  }
}
```

**Step 4: Add helper functions to utils/bag_config.py**

Add after `reload()`:

```python
def get_uneekor_mapping() -> Dict[str, str]:
    """Return Uneekor club_name -> canonical name mapping from bag config.

    Combines regular clubs and special categories into one lookup dict.
    """
    bag = _load()
    mapping = {}
    for club in bag.get('clubs', []):
        uneekor = club.get('uneekor')
        if uneekor:
            mapping[uneekor] = club['canonical']
    for cat in bag.get('special_categories', []):
        uneekor = cat.get('uneekor')
        if isinstance(uneekor, list):
            for u in uneekor:
                mapping[u] = cat['canonical']
        elif uneekor:
            mapping[uneekor] = cat['canonical']
    return mapping


def get_special_categories() -> list:
    """Return special categories (Sim Round, Other) from bag config."""
    return _load().get('special_categories', [])
```

**Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_bag_config -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add my_bag.json utils/bag_config.py tests/unit/test_bag_config.py
git commit -m "feat: update my_bag.json with complete bag and Uneekor mappings"
```

---

### Task 3: Add Database Schema Columns

**Files:**
- Modify: `golf_db.py:155-166` (add columns to `required_columns` migration dict)
- Modify: `golf_db.py:524-562` (update `save_shot()` payload)
- Modify: `golf_db.py:1067-1074` (update `ALLOWED_UPDATE_FIELDS`)
- Test: `tests/test_golf_db.py` (add test for new columns)

**Step 1: Write failing test**

Add to `tests/test_golf_db.py`:

```python
class TestNewSchemaColumns(unittest.TestCase):
    """Test sidebar_label and uneekor_club_id columns exist and work."""

    def setUp(self):
        self.db_path = tempfile.mktemp(suffix='.db')
        golf_db.SQLITE_DB_PATH = self.db_path
        os.environ.pop('SUPABASE_URL', None)
        golf_db._supabase = None
        golf_db.init_db()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_sidebar_label_column_exists(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(shots)")
        columns = [row[1] for row in cursor.fetchall()]
        self.assertIn('sidebar_label', columns)
        self.assertIn('uneekor_club_id', columns)
        conn.close()

    def test_save_shot_with_sidebar_label(self):
        shot = {
            'id': 'test_1_1_1',
            'session': 'test_1',
            'club': 'Driver',
            'sidebar_label': 'driver practice',
            'uneekor_club_id': 0,
            'original_club_value': 'DRIVER',
            'carry_distance': 250.0,
            'ball_speed': 150.0,
        }
        golf_db.save_shot(shot)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sidebar_label, uneekor_club_id FROM shots WHERE shot_id = 'test_1_1_1'")
        row = cursor.fetchone()
        self.assertEqual(row[0], 'driver practice')
        self.assertEqual(row[1], 0)
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_golf_db.TestNewSchemaColumns -v`
Expected: FAIL — columns don't exist yet

**Step 3: Add columns to migration and save_shot**

In `golf_db.py`, add to the `required_columns` dict (~line 155):

```python
'sidebar_label': 'TEXT',       # User-friendly name from Uneekor sidebar
'uneekor_club_id': 'INTEGER',  # Numeric club ID from Uneekor API
```

In `golf_db.py` `save_shot()`, add to the payload dict (~line 560, after `original_club_value`):

```python
'sidebar_label': data.get('sidebar_label'),
'uneekor_club_id': data.get('uneekor_club_id'),
```

In `golf_db.py`, add to `ALLOWED_UPDATE_FIELDS` (~line 1067):

```python
'sidebar_label',
'uneekor_club_id',
'original_club_value',
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_golf_db.TestNewSchemaColumns -v`
Expected: PASS

**Step 5: Run full test suite to check for regressions**

Run: `python -m unittest discover -s tests`
Expected: All existing tests still pass

**Step 6: Commit**

```bash
git add golf_db.py tests/test_golf_db.py
git commit -m "feat: add sidebar_label and uneekor_club_id columns to shots schema"
```

---

### Task 4: Fix golf_scraper.py to Use Correct API Fields

**Files:**
- Modify: `golf_scraper.py:141-184` (fix club_name and date extraction)
- Test: `tests/test_scraper.py` (add/update tests)

**Step 1: Write failing test**

Add to `tests/test_scraper.py` (or create new test class):

```python
import unittest
from unittest.mock import patch, MagicMock
import golf_scraper


class TestScraperClubMapping(unittest.TestCase):
    """Test that scraper uses club_name (not name) from API."""

    @patch('golf_scraper.golf_db')
    @patch('golf_scraper.request_with_retries')
    def test_scraper_uses_club_name_field(self, mock_request, mock_db):
        """Scraper should map club_name (e.g. WEDGE_PITCHING) to canonical."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            'id': 89069,
            'name': 'warmup',                    # sidebar label
            'club_name': 'WEDGE_PITCHING',        # internal Uneekor name
            'club': 28,
            'client_created_date': '2026-01-25',
            'shots': [{
                'id': 1,
                'ball_speed': 25.0,
                'club_speed': 28.0,
                'carry_distance': 52.0,
                'total_distance': 59.0,
                'club_path': 0.0,
                'club_face_angle': 0.0,
                'side_spin': 0,
                'back_spin': 2600,
                'launch_angle': 30.0,
                'side_angle': 0.0,
                'dynamic_loft': 40.0,
                'attack_angle': -5.0,
                'impact_x': 0,
                'impact_y': 0,
                'side_distance': 0,
                'decent_angle': 40,
                'apex': 15.0,
                'flight_time': 3.5,
                'type': 'straight',
                'optix_x': '0',
                'optix_y': '0',
                'club_lie': 0,
                'lie_angle': '',
            }],
        }]
        mock_request.return_value = mock_response

        result = golf_scraper.run_scraper(
            'https://my.uneekor.com/report?id=99999&key=testkey',
            lambda msg: None
        )

        # Verify save_shot was called with canonical club name, not sidebar label
        mock_db.save_shot.assert_called_once()
        shot_data = mock_db.save_shot.call_args[0][0]
        self.assertEqual(shot_data['club'], 'PW')                    # canonical
        self.assertEqual(shot_data['original_club_value'], 'WEDGE_PITCHING')  # raw
        self.assertEqual(shot_data['sidebar_label'], 'warmup')       # sidebar
        self.assertEqual(shot_data['session_date'], '2026-01-25')    # from API

    @patch('golf_scraper.golf_db')
    @patch('golf_scraper.request_with_retries')
    def test_scraper_uses_client_created_date(self, mock_request, mock_db):
        """Scraper should use client_created_date, not passed-in session_date."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            'id': 1,
            'name': 'Driver',
            'club_name': 'DRIVER',
            'club': 0,
            'client_created_date': '2026-02-01',
            'shots': [{
                'id': 1, 'ball_speed': 70, 'club_speed': 48,
                'carry_distance': 250, 'total_distance': 270,
                'club_path': 0, 'club_face_angle': 0,
                'side_spin': 0, 'back_spin': 2000,
                'launch_angle': 12, 'side_angle': 0,
                'dynamic_loft': 12, 'attack_angle': 3,
                'impact_x': 0, 'impact_y': 0,
                'side_distance': 0, 'decent_angle': 35,
                'apex': 30, 'flight_time': 6.0,
                'type': 'straight',
                'optix_x': '0', 'optix_y': '0',
                'club_lie': 0, 'lie_angle': '',
            }],
        }]
        mock_request.return_value = mock_response

        # Even though we pass session_date=2025-12-31, API date should win
        from datetime import datetime
        result = golf_scraper.run_scraper(
            'https://my.uneekor.com/report?id=99999&key=testkey',
            lambda msg: None,
            session_date=datetime(2025, 12, 31)
        )

        shot_data = mock_db.save_shot.call_args[0][0]
        self.assertEqual(shot_data['session_date'], '2026-02-01')
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_scraper.TestScraperClubMapping -v`
Expected: FAIL — scraper still uses `name` not `club_name`

**Step 3: Fix golf_scraper.py**

Add import at top of `golf_scraper.py`:

```python
from automation.naming_conventions import map_uneekor_club
```

Replace the session processing loop (lines ~141-216):

```python
    # 3. Process each session (club group)
    for session in sessions_data:
        # Use club_name (internal Uneekor name) for accurate club identification
        uneekor_club_name = session.get('club_name', '')
        sidebar_label = session.get('name', 'Unknown')
        canonical_club = map_uneekor_club(uneekor_club_name)
        uneekor_club_id = session.get('club')

        # Use client_created_date from API as the authoritative session date
        api_date = session.get('client_created_date')
        effective_date = api_date if api_date else (
            session_date.strftime('%Y-%m-%d') if session_date else None
        )

        session_id = session.get('id')
        shots = session.get('shots', [])

        if not shots:
            progress_callback(f"Skipping {sidebar_label} ({uneekor_club_name}) - no shots")
            continue

        progress_callback(f"Processing {sidebar_label} -> {canonical_club} ({len(shots)} shots)...")

        # 4. Process each shot in the session
        for shot in shots:
            try:
                # Unit Conversions (same as before)
                M_S_TO_MPH = 2.23694
                M_TO_YARDS = 1.09361

                ball_speed_ms = shot.get('ball_speed', 0)
                club_speed_ms = shot.get('club_speed', 0)

                ball_speed = round(ball_speed_ms * M_S_TO_MPH, 1)
                club_speed = round(club_speed_ms * M_S_TO_MPH, 1) if club_speed_ms else 0

                carry = shot.get('carry_distance', 0)
                total = shot.get('total_distance', 0)
                carry_yards = round(carry * M_TO_YARDS, 1) if carry else 0
                total_yards = round(total * M_TO_YARDS, 1) if total else 0

                smash = calculate_smash(ball_speed, club_speed)

                images = upload_shot_images(report_id, key, session_id, shot.get('id'))

                shot_data = {
                    'id': f"{report_id}_{session_id}_{shot.get('id')}",
                    'session': report_id,
                    'session_date': effective_date,
                    'club': canonical_club,
                    'original_club_value': uneekor_club_name,
                    'sidebar_label': sidebar_label,
                    'uneekor_club_id': uneekor_club_id,
                    'carry_distance': carry_yards,
                    'total_distance': total_yards,
                    'smash': smash,
                    'club_path': shot.get('club_path'),
                    'club_face_angle': shot.get('club_face_angle'),
                    'ball_speed': ball_speed,
                    'club_speed': club_speed,
                    'side_spin': shot.get('side_spin'),
                    'back_spin': shot.get('back_spin'),
                    'launch_angle': shot.get('launch_angle'),
                    'side_angle': shot.get('side_angle'),
                    'dynamic_loft': shot.get('dynamic_loft'),
                    'attack_angle': shot.get('attack_angle'),
                    'impact_x': shot.get('impact_x'),
                    'impact_y': shot.get('impact_y'),
                    'side_distance': shot.get('side_distance'),
                    'decent_angle': shot.get('decent_angle'),
                    'apex': shot.get('apex'),
                    'flight_time': shot.get('flight_time'),
                    'type': shot.get('type'),
                    'impact_img': images.get('impact_img'),
                    'swing_img': images.get('swing_img'),
                    'optix_x': shot.get('optix_x'),
                    'optix_y': shot.get('optix_y'),
                    'club_lie': shot.get('club_lie'),
                    'lie_angle': shot.get('lie_angle')
                }

                golf_db.save_shot(shot_data)
                total_shots_imported += 1

            except Exception as e:
                error_count += 1
                print(f"Error processing shot {shot.get('id')}: {e}")
                continue
```

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_scraper.TestScraperClubMapping -v`
Expected: Both tests PASS

**Step 5: Run py_compile to check syntax**

Run: `python -m py_compile golf_scraper.py`
Expected: No output (clean compile)

**Step 6: Commit**

```bash
git add golf_scraper.py tests/test_scraper.py
git commit -m "fix: use club_name and client_created_date from Uneekor API"
```

---

### Task 5: Add `reimport-all` CLI Command

**Files:**
- Modify: `automation_runner.py` (add parser + handler)
- Test: `tests/integration/test_reimport.py` (new file)

**Step 1: Write failing test**

Create `tests/integration/test_reimport.py`:

```python
"""Tests for reimport-all command."""

import unittest
import sqlite3
import tempfile
import os
from unittest.mock import patch, MagicMock

import golf_db


class TestReimportAll(unittest.TestCase):
    """Test the reimport-all command logic."""

    def setUp(self):
        self.db_path = tempfile.mktemp(suffix='.db')
        golf_db.SQLITE_DB_PATH = self.db_path
        os.environ.pop('SUPABASE_URL', None)
        golf_db._supabase = None
        golf_db.init_db()

        # Seed sessions_discovered with test data
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""INSERT INTO sessions_discovered
                     (report_id, api_key, import_status)
                     VALUES ('99999', 'testkey', 'imported')""")
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    @patch('golf_scraper.request_with_retries')
    @patch('golf_scraper.upload_shot_images', return_value={})
    def test_reimport_clears_and_rebuilds(self, mock_images, mock_request):
        """reimport_all should clear shots and re-import from API."""
        from automation_runner import reimport_all

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            'id': 1,
            'name': 'test',
            'club_name': 'DRIVER',
            'club': 0,
            'client_created_date': '2026-01-01',
            'shots': [{
                'id': 1, 'ball_speed': 70, 'club_speed': 48,
                'carry_distance': 250, 'total_distance': 270,
                'club_path': 0, 'club_face_angle': 0,
                'side_spin': 0, 'back_spin': 2000,
                'launch_angle': 12, 'side_angle': 0,
                'dynamic_loft': 12, 'attack_angle': 3,
                'impact_x': 0, 'impact_y': 0,
                'side_distance': 0, 'decent_angle': 35,
                'apex': 30, 'flight_time': 6.0,
                'type': 'straight',
                'optix_x': '0', 'optix_y': '0',
                'club_lie': 0, 'lie_angle': '',
            }],
        }]
        mock_request.return_value = mock_response

        result = reimport_all(db_path=self.db_path, dry_run=False)

        self.assertTrue(result['success'])
        self.assertEqual(result['sessions_processed'], 1)
        self.assertEqual(result['shots_imported'], 1)

        # Verify shot has correct club
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT club, original_club_value, sidebar_label FROM shots")
        row = c.fetchone()
        self.assertEqual(row[0], 'Driver')
        self.assertEqual(row[1], 'DRIVER')
        self.assertEqual(row[2], 'test')
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.integration.test_reimport -v`
Expected: ImportError — `reimport_all` doesn't exist yet

**Step 3: Implement reimport_all function and CLI command**

Add to `automation_runner.py` before `main()`:

```python
def reimport_all(db_path=None, dry_run=False):
    """
    Re-import all sessions from the Uneekor API with correct club mappings.

    Backs up the database, clears shots/archive/stats, then re-imports
    every session in sessions_discovered by calling the Uneekor API directly.

    Args:
        db_path: Override database path (for testing)
        dry_run: If True, don't make changes

    Returns:
        Dict with success, sessions_processed, shots_imported, errors
    """
    import shutil
    from datetime import datetime

    if db_path:
        golf_db.SQLITE_DB_PATH = db_path

    # Ensure tables exist
    golf_db.init_db()

    conn = sqlite3.connect(golf_db.SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Get all discovered sessions
    cursor.execute("SELECT report_id, api_key FROM sessions_discovered")
    sessions = cursor.fetchall()

    if not sessions:
        print("No sessions found in sessions_discovered.")
        conn.close()
        return {'success': True, 'sessions_processed': 0, 'shots_imported': 0, 'errors': []}

    print(f"Found {len(sessions)} sessions to reimport.")

    if dry_run:
        print("[DRY RUN] Would clear shots, shots_archive, change_log, session_stats")
        print(f"[DRY RUN] Would reimport {len(sessions)} sessions from Uneekor API")
        conn.close()
        return {'success': True, 'sessions_processed': len(sessions), 'shots_imported': 0, 'errors': []}

    # Backup database
    backup_path = f"{golf_db.SQLITE_DB_PATH}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(golf_db.SQLITE_DB_PATH, backup_path)
    print(f"Database backed up to {backup_path}")

    # Clear tables
    for table in ['shots', 'shots_archive', 'change_log', 'session_stats']:
        try:
            cursor.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass  # Table might not exist
    conn.commit()
    print("Cleared shots, shots_archive, change_log, session_stats")

    # Re-import each session
    total_shots = 0
    sessions_ok = 0
    errors = []
    API_BASE = "https://api-v2.golfsvc.com/v2/oldmyuneekor/report"

    for report_id, api_key in sessions:
        try:
            api_url = f"{API_BASE}/{report_id}/{api_key}"
            result = golf_scraper.run_scraper(
                f"https://my.uneekor.com/report?id={report_id}&key={api_key}",
                lambda msg: None,  # quiet callback
            )

            if result and result.get('status') == 'success':
                shots = result.get('total_shots_imported', 0)
                total_shots += shots
                sessions_ok += 1
                print(f"  [{sessions_ok}/{len(sessions)}] {report_id}: {shots} shots")
            else:
                err = result.get('message', 'Unknown error') if result else 'No result'
                errors.append(f"{report_id}: {err}")
                print(f"  [{sessions_ok}/{len(sessions)}] {report_id}: FAILED - {err}")

        except Exception as e:
            errors.append(f"{report_id}: {str(e)}")
            print(f"  {report_id}: ERROR - {e}")

        # Check failure threshold (>5% = abort)
        total_attempted = sessions_ok + len(errors)
        if total_attempted >= 5 and len(errors) / total_attempted > 0.05:
            print(f"ABORT: Failure rate {len(errors)}/{total_attempted} exceeds 5% threshold")
            break

    # Update sessions_discovered statuses
    cursor.execute("UPDATE sessions_discovered SET import_status = 'reimported'")
    conn.commit()
    conn.close()

    print(f"\nReimport complete: {sessions_ok} sessions, {total_shots} shots, {len(errors)} errors")
    if errors:
        print("Errors:")
        for e in errors[:10]:
            print(f"  {e}")

    return {
        'success': len(errors) == 0,
        'sessions_processed': sessions_ok,
        'shots_imported': total_shots,
        'errors': errors,
    }


def cmd_reimport_all(args):
    """Handle reimport-all command."""
    result = reimport_all(dry_run=args.dry_run)
    return 0 if result['success'] else 1
```

Add to the CLI parser in `main()` (before `args = parser.parse_args()`):

```python
    # Reimport-all command
    reimport_parser = subparsers.add_parser('reimport-all',
        help='Clear shots and reimport all sessions from Uneekor API')
    reimport_parser.add_argument('--dry-run', action='store_true',
        help='Preview without making changes')
```

Add to the handlers dict:

```python
'reimport-all': cmd_reimport_all,
```

Add imports at top of `automation_runner.py` if not already present:

```python
import sqlite3
import golf_scraper
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.integration.test_reimport -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `python -m unittest discover -s tests`
Expected: All tests pass

**Step 6: Commit**

```bash
git add automation_runner.py tests/integration/test_reimport.py
git commit -m "feat: add reimport-all CLI command for clean data re-import"
```

---

### Task 6: Run the Clean Re-import

**This task is manual execution — no code changes.**

**Step 1: Verify database backup**

Run: `ls -la golf_stats.db`
Note the size and modification time.

**Step 2: Dry run first**

Run: `python automation_runner.py reimport-all --dry-run`
Expected: Shows count of sessions that would be reimported, no changes made.

**Step 3: Execute the reimport**

Run: `python automation_runner.py reimport-all`
Expected: ~126 sessions imported, ~5,500 shots, 0 errors.
Watch for: failure rate threshold, any API errors.

**Step 4: Verify results**

Run:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('golf_stats.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM shots')
total = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM shots WHERE club IS NULL OR club = \"\"')
null_club = c.fetchone()[0]
c.execute('SELECT DISTINCT club, COUNT(*) FROM shots GROUP BY club ORDER BY COUNT(*) DESC')
print(f'Total shots: {total}')
print(f'NULL club: {null_club}')
print('Clubs:')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')
c.execute('SELECT COUNT(DISTINCT session_id) FROM shots')
print(f'Sessions: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM shots WHERE session_date IS NOT NULL')
print(f'With date: {c.fetchone()[0]}')
conn.close()
"
```

Expected:
- Total shots: ~5,500+
- NULL club: 0
- All canonical club names present
- All shots have session_date

**Step 5: Commit the backup note (optional)**

No code to commit — just verify the reimport worked.

---

## Success Criteria Checklist

After all tasks complete, verify:

- [ ] `map_uneekor_club()` correctly maps all 20 Uneekor club names
- [ ] `my_bag.json` has 16 clubs + 2 special categories
- [ ] `golf_db.py` schema has `sidebar_label` and `uneekor_club_id` columns
- [ ] `golf_scraper.py` reads `club_name` and `client_created_date` from API
- [ ] `automation_runner.py reimport-all` command works
- [ ] All ~5,500 shots have non-NULL `club` values
- [ ] All shots have `session_date` from `client_created_date`
- [ ] All shots have `sidebar_label` and `original_club_value` populated
- [ ] All existing tests still pass
- [ ] New tests pass

## Estimated Time

| Task | Estimate |
|------|----------|
| Task 1: Club mapping | 5 min |
| Task 2: my_bag.json + bag_config | 5 min |
| Task 3: Schema columns | 5 min |
| Task 4: Fix scraper | 10 min |
| Task 5: reimport-all command | 10 min |
| Task 6: Run reimport | 5 min |
| **Total** | **~40 min** |
