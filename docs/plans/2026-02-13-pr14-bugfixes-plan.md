# PR #14 Bug Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 4 bugs found during code review of the session classification engine in PR #14.

**Architecture:** Four targeted edits across 3 files plus 1 test file adjustment. No new dependencies or structural changes.

**Tech Stack:** Python, unittest, SQLite

---

### Task 1: Fix fitting classification unreachable

**Files:**
- Modify: `automation/naming_conventions.py:1014-1043`
- Modify: `tests/unit/test_session_classifier.py:290-293`

**Step 1: Move fitting check before drill check**

In `automation/naming_conventions.py`, swap the order so fitting is checked first. Replace lines 1014-1021:

```python
        # --- Fitting detection: 1 club, very high volume ---
        if num_unique == 1 and total >= 50:
            return ClassificationResult(
                category='fitting',
                confidence=0.8,
                signals={'reason': 'single_club_high_volume', 'club': list(unique_clubs)[0], 'total': total},
            )

        # --- Drill: 1-2 clubs with significant repetition ---
        if num_unique <= 2 and total >= 20:
            return ClassificationResult(
                category='drill',
                confidence=0.9,
                signals={'reason': 'repetitive_clubs', 'unique_clubs': num_unique, 'total': total},
            )
```

And remove the old fitting block at lines 1037-1043.

**Step 2: Tighten test assertions**

In `tests/unit/test_session_classifier.py`, update line 293:

```python
        self.assertEqual(result.category, 'fitting')
```

And update line 237 (the 50-driver test) similarly -- with fitting check first, 50 drivers should now be fitting:

```python
        self.assertIn(result.category, ('drill', 'fitting'))
```

Actually, 50 drivers: `num_unique == 1` and `total >= 50`, so it hits fitting. Update line 237:

```python
        self.assertEqual(result.category, 'fitting')
```

**Step 3: Run tests**

Run: `python -m unittest tests.unit.test_session_classifier -v`
Expected: All pass

---

### Task 2: Filter NULL session_category in get_shots_by_category

**Files:**
- Modify: `golf_db.py:678-679`

**Step 1: Add notna filter**

In `golf_db.py`, replace lines 678-679:

```python
    if exclude_categories:
        df = df[~df['session_category'].isin(exclude_categories)]
```

With:

```python
    if exclude_categories:
        df = df[
            df['session_category'].notna() &
            ~df['session_category'].isin(exclude_categories)
        ]
```

**Step 2: Run tests**

Run: `python -m unittest tests.unit.test_session_classifier -v`
Expected: All pass

---

### Task 3: Wrap classify_all_sessions in try/finally

**Files:**
- Modify: `golf_db.py:724-778`

**Step 1: Add try/finally around connection**

In `golf_db.py`, wrap the connection block. Replace the section starting at line 725:

```python
    conn = sqlite3.connect(SQLITE_DB_PATH)
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT session_id FROM shots")
        session_ids = [row[0] for row in cursor.fetchall()]

        categories = {}
        classified = 0

        for sid in session_ids:
            # ... existing loop body unchanged ...
```

And at the end (after the change_log insert and final `conn.commit()`), add:

```python
    finally:
        conn.close()
```

Remove the old standalone `conn.close()` at line 778.

**Step 2: Run tests**

Run: `python -m unittest tests.unit.test_session_classifier -v`
Expected: All pass

---

### Task 4: Reorder intent patterns in local_coach.py

**Files:**
- Modify: `local_coach.py:81-82`

**Step 1: Move session_breakdown before session_analysis**

In `local_coach.py`, swap lines 81-82 so the more specific pattern is checked first:

```python
        'session_breakdown': r'\b(round|sim\s*round|practice\s*round|indoor\s*round)\b|\bsession\s*type\b|\bcategor\b',
        'session_analysis': r'\bsession\b|\btoday\b|\blast\b.*\bpractice\b',
```

**Step 2: Run tests**

Run: `python -m unittest tests.unit.test_local_coach -v`
Expected: All pass

---

### Task 5: Final verification and commit

**Step 1: Run full test suite**

Run: `python -m unittest discover -s tests -v`
Expected: All pass

**Step 2: Syntax check modified files**

Run: `python -m py_compile automation/naming_conventions.py && python -m py_compile golf_db.py && python -m py_compile local_coach.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add automation/naming_conventions.py golf_db.py local_coach.py tests/unit/test_session_classifier.py
git commit -m "fix: address code review bugs in session classification engine

- Move fitting check before drill to fix unreachable fitting category
- Filter NULL session_category to prevent unclassified data leaking
- Wrap classify_all_sessions in try/finally for connection safety
- Reorder intent patterns so session_breakdown is reachable

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```
