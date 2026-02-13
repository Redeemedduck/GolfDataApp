# Phase 1: Data Model Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the core data model problem where 82% of `club` column values are session names instead of actual club names, by adding an `original_club_value` column, enhancing the normalizer, wiring in `SessionContextParser`, migrating existing data, and normalizing at import time.

**Architecture:** Add `original_club_value` column to preserve raw values. Enhance `ClubNameNormalizer` with 3 new pattern categories. Create a two-tier normalization pipeline: `ClubNameNormalizer` first, `SessionContextParser` fallback for low-confidence results. Normalize inside `save_shot()` so all import paths are covered.

**Tech Stack:** Python 3.10+, SQLite, unittest, existing `automation/naming_conventions.py` classes

---

### Task 1: Add `original_club_value` Column (Schema Migration)

**Files:**
- Modify: `golf_db.py:154-164` (add to `required_columns` dict)
- Modify: `supabase_schema.sql:25` (add column to CREATE TABLE)
- Test: `tests/test_golf_db.py` (verify migration)

**Step 1: Add to SQLite migration dict**

In `golf_db.py`, add `original_club_value` to the `required_columns` dict at line ~164:

```python
    required_columns = {
        'optix_x': 'REAL',
        'optix_y': 'REAL',
        'club_lie': 'REAL',
        'lie_angle': 'TEXT',
        'shot_tag': 'TEXT',
        'session_type': 'TEXT',
        'session_date': 'TIMESTAMP',
        'face_to_path': 'REAL',
        'strike_distance': 'REAL',
        'original_club_value': 'TEXT',  # Raw club/session name from Uneekor
    }
```

**Step 2: Add to Supabase schema**

In `supabase_schema.sql`, add after line 52 (`shot_tag TEXT`):

```sql
    shot_tag TEXT,
    original_club_value TEXT
```

**Step 3: Add to `save_shot()` payload**

In `golf_db.py`, modify the payload dict at line ~548 to include:

```python
        'shot_tag': data.get('shot_tag'),
        'original_club_value': data.get('original_club_value'),
    }
```

**Step 4: Run existing tests to verify no breakage**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: `Ran 243 tests ... OK`

**Step 5: Commit**

```bash
git add golf_db.py supabase_schema.sql
git commit -m "feat: add original_club_value column to shots table

Preserves raw Uneekor session/club name before normalization.
Added to SQLite migration dict and Supabase schema."
```

---

### Task 2: Add Uneekor Default Format Patterns to ClubNameNormalizer

**Files:**
- Modify: `automation/naming_conventions.py:75-118` (add patterns to CLUB_PATTERNS)
- Test: `tests/unit/test_naming_conventions.py`

**Step 1: Write the failing tests**

Add to `tests/unit/test_naming_conventions.py` inside `TestClubNameNormalizer`:

```python
    # --- Uneekor default format (IRON7 | MEDIUM) ---

    def test_uneekor_format_iron7_medium(self):
        result = self.normalizer.normalize("Iron7 | Medium")
        self.assertEqual(result.normalized, "7 Iron")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_uneekor_format_iron6_medium(self):
        result = self.normalizer.normalize("Iron6 | Medium")
        self.assertEqual(result.normalized, "6 Iron")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_uneekor_format_uppercase(self):
        result = self.normalizer.normalize("IRON7 | MEDIUM")
        self.assertEqual(result.normalized, "7 Iron")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_uneekor_format_driver(self):
        result = self.normalizer.normalize("DRIVER | MEDIUM")
        self.assertEqual(result.normalized, "Driver")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_uneekor_format_wood3_premium(self):
        result = self.normalizer.normalize("WOOD3 | PREMIUM")
        self.assertEqual(result.normalized, "3 Wood")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_uneekor_format_hybrid4(self):
        result = self.normalizer.normalize("HYBRID4 | MEDIUM")
        self.assertEqual(result.normalized, "4 Hybrid")
        self.assertGreaterEqual(result.confidence, 0.9)
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_naming_conventions.TestClubNameNormalizer.test_uneekor_format_iron7_medium -v`
Expected: FAIL — normalizer returns `"Iron7 | Medium"` with confidence 0.3

**Step 3: Add patterns to CLUB_PATTERNS**

In `automation/naming_conventions.py`, add after the Putter pattern (line 117) and before the closing `]`:

```python
        # Putter
        (r'^(putter|putt|putting)$', 'Putter'),

        # Uneekor default format: "IRON7 | MEDIUM", "DRIVER | PREMIUM"
        (r'^driver\s*\|.*$', 'Driver'),
        (r'^iron(\d)\s*\|.*$', '_UNEEKOR_IRON'),
        (r'^wood(\d)\s*\|.*$', '_UNEEKOR_WOOD'),
        (r'^hybrid(\d)\s*\|.*$', '_UNEEKOR_HYBRID'),
        (r'^wedge(\d{2})\s*\|.*$', '_UNEEKOR_WEDGE'),
    ]
```

**Step 4: Add handler logic in `normalize()` method**

In the `normalize()` method at line ~191, add handling for the new special names after the `_DEGREE_WEDGE` block:

```python
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
                    # Uneekor default format: IRON7 | MEDIUM -> 7 Iron
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
                            normalized = self.DEGREE_TO_WEDGE.get(degree, f'{degree} Wedge')
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
                else:
```

**Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_naming_conventions.TestClubNameNormalizer -v 2>&1 | tail -10`
Expected: All Uneekor format tests PASS

**Step 6: Commit**

```bash
git add automation/naming_conventions.py tests/unit/test_naming_conventions.py
git commit -m "feat: add Uneekor default format patterns to ClubNameNormalizer

Handles IRON7 | MEDIUM, DRIVER | PREMIUM, WOOD3 | MEDIUM, etc.
Fixes 20 shots in existing database."
```

---

### Task 3: Add Reversed and No-Space Patterns

**Files:**
- Modify: `automation/naming_conventions.py:75-118` (add patterns)
- Test: `tests/unit/test_naming_conventions.py`

**Step 1: Write the failing tests**

```python
    # --- Reversed forms ---

    def test_wedge_pitching_reversed(self):
        result = self.normalizer.normalize("Wedge Pitching")
        self.assertEqual(result.normalized, "PW")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_wedge_sand_reversed(self):
        result = self.normalizer.normalize("Wedge Sand")
        self.assertEqual(result.normalized, "SW")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_wedge_50_degree_number(self):
        result = self.normalizer.normalize("Wedge 50")
        self.assertEqual(result.normalized, "GW")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_wedge_56_degree_number(self):
        result = self.normalizer.normalize("Wedge 56")
        self.assertEqual(result.normalized, "SW")
        self.assertGreaterEqual(result.confidence, 0.9)

    # --- No-space iron ---

    def test_iron7_no_space(self):
        result = self.normalizer.normalize("Iron7")
        self.assertEqual(result.normalized, "7 Iron")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_iron6_no_space(self):
        result = self.normalizer.normalize("Iron6")
        self.assertEqual(result.normalized, "6 Iron")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_iron9_no_space(self):
        result = self.normalizer.normalize("Iron9")
        self.assertEqual(result.normalized, "9 Iron")
        self.assertGreaterEqual(result.confidence, 0.9)
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_naming_conventions.TestClubNameNormalizer.test_wedge_pitching_reversed -v`
Expected: FAIL

**Step 3: Add patterns to CLUB_PATTERNS**

Add before the Uneekor format patterns (after Putter):

```python
        # Putter
        (r'^(putter|putt|putting)$', 'Putter'),

        # Reversed forms: "Wedge Pitching" -> PW, "Wedge 50" -> GW
        (r'^wedge\s*(pitching|p)$', 'PW'),
        (r'^wedge\s*(gap|g)$', 'GW'),
        (r'^wedge\s*(sand|s)$', 'SW'),
        (r'^wedge\s*(lob|l)$', 'LW'),
        (r'^wedge\s*(approach|a)$', 'AW'),
        (r'^wedge\s*(\d{2})$', '_WEDGE_DEGREE_NUM'),

        # No-space iron: "Iron7" -> "7 Iron"
        (r'^iron(\d)$', '_IRON_NOSPACE'),
        (r'^wood(\d)$', '_WOOD_NOSPACE'),
        (r'^hybrid(\d)$', '_HYBRID_NOSPACE'),
```

**Step 4: Add handler logic in `normalize()`**

Add after the `_UNEEKOR_` block:

```python
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
```

**Step 5: Run tests**

Run: `python -m unittest tests.unit.test_naming_conventions.TestClubNameNormalizer -v 2>&1 | tail -10`
Expected: All PASS

**Step 6: Commit**

```bash
git add automation/naming_conventions.py tests/unit/test_naming_conventions.py
git commit -m "feat: add reversed wedge and no-space iron patterns

Handles 'Wedge Pitching' -> PW, 'Wedge 50' -> GW, 'Iron7' -> '7 Iron'.
Fixes ~30 additional shots."
```

---

### Task 4: Wire SessionContextParser into Normalization Pipeline

**Files:**
- Modify: `automation/naming_conventions.py` (add `normalize_with_context()` function)
- Test: `tests/unit/test_naming_conventions.py`

**Step 1: Write the failing tests**

Add a new test class:

```python
class TestNormalizationPipeline(unittest.TestCase):
    """Tests for the two-tier normalization pipeline."""

    def setUp(self):
        self.normalizer = ClubNameNormalizer()
        self.parser = SessionContextParser()

    def _normalize_with_context(self, raw_value):
        """Two-tier normalization: ClubNameNormalizer first, SessionContextParser fallback."""
        from automation.naming_conventions import normalize_with_context
        return normalize_with_context(raw_value)

    # Standard clubs pass through normalizer
    def test_standard_club_uses_normalizer(self):
        result = self._normalize_with_context("7 Iron")
        self.assertEqual(result['club'], "7 Iron")
        self.assertEqual(result['session_type'], None)

    def test_driver_uses_normalizer(self):
        result = self._normalize_with_context("Driver")
        self.assertEqual(result['club'], "Driver")

    # Session names with embedded clubs use parser
    def test_warmup_pw_extracts_club(self):
        result = self._normalize_with_context("Warmup Pw")
        self.assertEqual(result['club'], "PW")
        self.assertEqual(result['session_type'], "warmup")

    def test_dst_compressor_8_extracts_club(self):
        result = self._normalize_with_context("Dst Compressor 8")
        self.assertEqual(result['club'], "8 Iron")
        self.assertEqual(result['session_type'], "drill")

    def test_warmup_50_extracts_club(self):
        result = self._normalize_with_context("Warmup 50")
        self.assertEqual(result['club'], "GW")
        self.assertEqual(result['session_type'], "warmup")

    def test_wedge_50_extracts_club(self):
        result = self._normalize_with_context("Wedge 50")
        self.assertEqual(result['club'], "GW")

    def test_8_iron_dst_trainer_extracts_club(self):
        result = self._normalize_with_context("8 Iron Dst Trainer")
        self.assertEqual(result['club'], "8 Iron")
        self.assertEqual(result['session_type'], "drill")

    def test_forward_impact_pw_extracts_club(self):
        result = self._normalize_with_context("Forward Impact Pw")
        self.assertEqual(result['club'], "PW")

    # Pure session names with no club info
    def test_sgt_rd1_no_club(self):
        result = self._normalize_with_context("Sgt Rd1")
        self.assertIsNone(result['club'])
        self.assertEqual(result['session_type'], "sim_round")

    def test_bag_mapping_no_club(self):
        result = self._normalize_with_context("Bag Mapping")
        self.assertIsNone(result['club'])
        self.assertEqual(result['session_type'], "bag_mapping")

    def test_warmup_no_club(self):
        result = self._normalize_with_context("Warmup")
        self.assertIsNone(result['club'])
        self.assertEqual(result['session_type'], "warmup")

    def test_3_4_speed_towel_drill_no_club(self):
        result = self._normalize_with_context("3/4 Speed Towel Drill")
        self.assertIsNone(result['club'])
        self.assertEqual(result['session_type'], "drill")
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_naming_conventions.TestNormalizationPipeline -v`
Expected: FAIL — `normalize_with_context` does not exist

**Step 3: Implement `normalize_with_context()`**

Add to `automation/naming_conventions.py` as a module-level function (after the classes, near the existing `normalize_club()` convenience function):

```python
def normalize_with_context(raw_value: str) -> Dict[str, Optional[str]]:
    """
    Two-tier normalization: ClubNameNormalizer first, SessionContextParser fallback.

    Args:
        raw_value: Raw club/session name from Uneekor

    Returns:
        Dict with keys:
            'club': Normalized club name or None if unresolvable
            'session_type': Detected session type or None
            'original': The original raw value
            'confidence': Normalization confidence (0.0-1.0)
    """
    if not raw_value:
        return {'club': None, 'session_type': None, 'original': raw_value, 'confidence': 0.0}

    normalizer = ClubNameNormalizer()
    result = normalizer.normalize(raw_value)

    # High confidence = it's a real club name
    if result.confidence >= 0.9:
        return {
            'club': result.normalized,
            'session_type': None,
            'original': raw_value,
            'confidence': result.confidence,
        }

    # Low confidence = try SessionContextParser
    parser = SessionContextParser()
    context = parser.parse(raw_value)

    return {
        'club': context.get('club'),
        'session_type': context.get('session_type'),
        'original': raw_value,
        'confidence': 0.8 if context.get('club') else 0.1,
    }
```

**Step 4: Run tests**

Run: `python -m unittest tests.unit.test_naming_conventions.TestNormalizationPipeline -v`
Expected: All PASS

**Step 5: Run full test suite**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: All 243+ tests OK

**Step 6: Commit**

```bash
git add automation/naming_conventions.py tests/unit/test_naming_conventions.py
git commit -m "feat: add two-tier normalization pipeline (normalize_with_context)

ClubNameNormalizer handles standard club names (confidence >= 0.9).
SessionContextParser extracts embedded clubs from session names like
'Warmup PW' -> PW, 'Dst Compressor 8' -> 8 Iron.
Unresolvable session names ('Sgt Rd1', 'Bag Mapping') return club=None."
```

---

### Task 5: Normalize Inside `save_shot()`

**Files:**
- Modify: `golf_db.py:485-549` (add normalization to save_shot)
- Test: `tests/test_golf_db.py`

**Step 1: Write the failing test**

Add to `tests/test_golf_db.py`:

```python
    def test_save_shot_normalizes_club(self):
        """save_shot() should normalize club names and preserve original."""
        shot_data = {
            'id': 'test_norm_001',
            'session': 'session_norm',
            'club': 'Warmup Pw',
            'carry_distance': 120,
        }
        golf_db.save_shot(shot_data)

        conn = sqlite3.connect(golf_db.SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT club, original_club_value FROM shots WHERE shot_id = ?", ('test_norm_001',))
        row = cursor.fetchone()
        conn.close()

        self.assertEqual(row[0], 'PW')  # Normalized
        self.assertEqual(row[1], 'Warmup Pw')  # Original preserved

    def test_save_shot_preserves_standard_club(self):
        """save_shot() should not alter already-standard club names."""
        shot_data = {
            'id': 'test_norm_002',
            'session': 'session_norm',
            'club': '7 Iron',
            'carry_distance': 165,
        }
        golf_db.save_shot(shot_data)

        conn = sqlite3.connect(golf_db.SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT club, original_club_value FROM shots WHERE shot_id = ?", ('test_norm_002',))
        row = cursor.fetchone()
        conn.close()

        self.assertEqual(row[0], '7 Iron')
        self.assertEqual(row[1], '7 Iron')

    def test_save_shot_unknown_session_name(self):
        """save_shot() should set club=None for unresolvable session names."""
        shot_data = {
            'id': 'test_norm_003',
            'session': 'session_norm',
            'club': 'Sgt Rd1',
            'carry_distance': 250,
        }
        golf_db.save_shot(shot_data)

        conn = sqlite3.connect(golf_db.SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT club, original_club_value FROM shots WHERE shot_id = ?", ('test_norm_003',))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNone(row[0])  # No extractable club
        self.assertEqual(row[1], 'Sgt Rd1')  # Original preserved
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_golf_db.TestGolfDB.test_save_shot_normalizes_club -v`
Expected: FAIL — club is stored raw, no `original_club_value` column

**Step 3: Add normalization to `save_shot()`**

At the top of `golf_db.py`, add import (near other imports):

```python
from automation.naming_conventions import normalize_with_context
```

In `save_shot()`, add normalization before the payload dict (between lines 509 and 511):

```python
    if not session_id:
        raise ValidationError(
            "session_id is required",
            field='session_id',
            value=session_id
        )

    # Normalize club name and preserve original
    raw_club = data.get('club')
    if raw_club and not data.get('original_club_value'):
        context = normalize_with_context(raw_club)
        normalized_club = context['club']  # May be None for unresolvable names
        original_club = raw_club
    else:
        normalized_club = data.get('club')
        original_club = data.get('original_club_value', data.get('club'))

    # Prepare unified payload
    payload = {
        'shot_id': shot_id,
        'session_id': session_id,
        'session_date': data.get('session_date'),
        'session_type': data.get('session_type'),
        'club': normalized_club,
```

And update the end of the payload to include `original_club_value`:

```python
        'shot_tag': data.get('shot_tag'),
        'original_club_value': original_club,
    }
```

**Step 4: Run tests**

Run: `python -m unittest tests.test_golf_db -v 2>&1 | tail -10`
Expected: All PASS including new normalization tests

**Step 5: Run full suite**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: All tests OK

**Step 6: Commit**

```bash
git add golf_db.py tests/test_golf_db.py
git commit -m "feat: normalize club names at import time in save_shot()

All import paths (legacy scraper, backfill runner) now automatically
normalize club names via the two-tier pipeline. Original raw values
preserved in original_club_value column."
```

---

### Task 6: Data Migration Script

**Files:**
- Create: `utils/migrate_club_data.py`
- Test: manual dry-run with `--dry-run` flag

**Step 1: Create the migration script**

Create `utils/migrate_club_data.py`:

```python
"""
One-time migration: normalize existing club column values.

Usage:
    python -m utils.migrate_club_data --dry-run    # Preview changes
    python -m utils.migrate_club_data              # Execute migration
    python -m utils.migrate_club_data --report     # Summary report only
"""

import sqlite3
import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automation.naming_conventions import normalize_with_context
import golf_db


def migrate(dry_run=True, report_only=False):
    """Run the club data migration."""
    conn = sqlite3.connect(golf_db.SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Get all distinct club values
    cursor.execute("SELECT DISTINCT club, COUNT(*) as cnt FROM shots GROUP BY club ORDER BY cnt DESC")
    club_counts = cursor.fetchall()

    print(f"\nFound {len(club_counts)} distinct club values\n")

    stats = {
        'already_correct': 0,
        'normalized': 0,
        'club_extracted': 0,
        'set_to_unknown': 0,
        'total_shots': 0,
    }

    changes = []

    for club_value, count in club_counts:
        result = normalize_with_context(club_value)
        new_club = result['club']
        session_type = result['session_type']
        confidence = result['confidence']

        stats['total_shots'] += count

        if new_club == club_value:
            stats['already_correct'] += count
            status = 'OK'
        elif new_club is not None:
            if confidence >= 0.9:
                stats['normalized'] += count
                status = 'NORMALIZE'
            else:
                stats['club_extracted'] += count
                status = 'EXTRACT'
            changes.append((club_value, new_club, session_type, count, status))
        else:
            stats['set_to_unknown'] += count
            status = 'UNKNOWN'
            changes.append((club_value, None, session_type, count, status))

        if not report_only:
            print(f"  [{status:>9}] {club_value:>35} -> {str(new_club):>10} "
                  f"(type={session_type}, conf={confidence:.1f}, {count} shots)")

    # Summary
    print(f"\n{'='*60}")
    print(f"MIGRATION SUMMARY")
    print(f"{'='*60}")
    print(f"  Total shots:        {stats['total_shots']:>6}")
    print(f"  Already correct:    {stats['already_correct']:>6}")
    print(f"  Will normalize:     {stats['normalized']:>6}")
    print(f"  Will extract club:  {stats['club_extracted']:>6}")
    print(f"  Set to NULL (unknown): {stats['set_to_unknown']:>6}")
    print(f"  Total changes:      {stats['normalized'] + stats['club_extracted'] + stats['set_to_unknown']:>6}")

    if dry_run or report_only:
        print(f"\n  DRY RUN — no changes made.")
        conn.close()
        return stats

    # Execute changes
    print(f"\nExecuting migration...")
    changed = 0
    for old_club, new_club, session_type, count, status in changes:
        # Preserve original value
        cursor.execute(
            "UPDATE shots SET original_club_value = club WHERE club = ? AND original_club_value IS NULL",
            (old_club,)
        )
        # Update club
        cursor.execute(
            "UPDATE shots SET club = ? WHERE club = ?",
            (new_club, old_club)
        )
        # Log change
        cursor.execute(
            "INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            ('club_migration', 'shot', old_club,
             f'{old_club} -> {new_club} ({count} shots, type={session_type})')
        )
        changed += count

    conn.commit()
    conn.close()
    print(f"  Done. {changed} shots updated.")
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate club column data')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without executing')
    parser.add_argument('--report', action='store_true', help='Summary report only')
    args = parser.parse_args()

    migrate(dry_run=args.dry_run or args.report, report_only=args.report)
```

**Step 2: Dry-run to preview changes**

Run: `python -m utils.migrate_club_data --dry-run`
Expected: List of all club values with their normalization results and a summary

**Step 3: Review output, then execute**

Run: `python -m utils.migrate_club_data`
Expected: Migration completes, all changes logged

**Step 4: Verify**

Run: `python -c "import golf_db; golf_db.init_db(); import sqlite3; conn=sqlite3.connect(golf_db.SQLITE_DB_PATH); print(conn.execute('SELECT DISTINCT club FROM shots ORDER BY club').fetchall())"`
Expected: Clean list of normalized club names + `None` for unresolvable sessions

**Step 5: Commit**

```bash
git add utils/migrate_club_data.py
git commit -m "feat: add club data migration script

One-time migration to normalize existing club values.
Preserves originals in original_club_value column.
Supports --dry-run and --report modes."
```

---

### Task 7: Consolidate Inline Normalizer in Settings Page

**Files:**
- Modify: `pages/4_⚙️_Settings.py:386-407`

**Step 1: Replace inline normalizer**

In `pages/4_⚙️_Settings.py`, replace the `normalize_club_name()` function and its usage:

```python
# Before (lines 386-407):
def normalize_club_name(name):
    base = (name or "").lower().strip()
    base = re.sub(r"[_-]+", " ", base)
    base = re.sub(r"\s+", " ", base)
    base = base.replace("iron", "i")
    return base

# After:
from automation.naming_conventions import ClubNameNormalizer

_normalizer = ClubNameNormalizer()

def normalize_club_name(name):
    """Normalize club name for anomaly detection using canonical normalizer."""
    if not name:
        return ""
    return _normalizer.normalize(name).normalized.lower()
```

**Step 2: Run syntax check**

Run: `python -m py_compile pages/4_⚙️_Settings.py`
Expected: No errors

**Step 3: Run full test suite**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: All tests OK

**Step 4: Commit**

```bash
git add "pages/4_⚙️_Settings.py"
git commit -m "refactor: consolidate inline normalizer in Settings page

Replace ad-hoc normalize_club_name() with ClubNameNormalizer
to prevent logic drift between normalization approaches."
```

---

### Task 8: Update CLAUDE.md and Run Final Verification

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update CLAUDE.md**

Add to the "Key Conventions" section:

```markdown
- Club names are normalized at import time via `save_shot()` using the two-tier pipeline:
  `ClubNameNormalizer` (confidence >= 0.9) then `SessionContextParser` fallback.
  Original raw values preserved in `original_club_value` column.
- The `normalize_with_context()` function in `automation/naming_conventions.py` is the
  canonical entry point for club normalization.
```

**Step 2: Run full test suite and CI lint**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: All tests OK

Run: `python -m py_compile golf_db.py && python -m py_compile automation/naming_conventions.py`
Expected: No errors

**Step 3: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with club normalization pipeline docs"
```

---

## Verification Checklist

After all tasks are complete:

- [ ] `original_club_value` column exists in SQLite and Supabase schema
- [ ] `ClubNameNormalizer` handles: Uneekor format (IRON7|MEDIUM), reversed wedges (Wedge Pitching), no-space irons (Iron7)
- [ ] `normalize_with_context()` function works: standard clubs, embedded clubs, unresolvable session names
- [ ] `save_shot()` normalizes automatically on all import paths
- [ ] Migration script ran successfully (check `change_log` table)
- [ ] Settings page uses `ClubNameNormalizer` instead of inline function
- [ ] All 243+ tests pass
- [ ] CI lint passes (`py_compile` on all Python files)
