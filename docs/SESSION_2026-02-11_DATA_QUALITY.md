# Session Report: Data Quality Framework & Club Normalization

**Date:** February 11, 2026
**Scope:** Data profiling → Quality validation system → Club normalization → Warmup tagging → Supabase sync prep
**Database:** `golf_stats.db` — 2,141 shots across 46 sessions, 70 distinct club names

---

## 1. Context & Motivation

This session built on earlier work (Feb 9–10) that profiled the golf shot database, explored the
Uneekor portal (125 sessions across 5 pages), and identified data reliability blind spots. The
database contains launch monitor data imported from the Uneekor portal via a Playwright scraper.
Several data quality concerns had been identified but not yet addressed systematically:

- Sentinel values (99999) possibly leaking through the import pipeline
- Club names stored as raw session names ("Sgt Rd1", "Warmup 50", "9 Iron Magnolia") rather than actual club names
- No way to distinguish warmup shots from real practice data
- Potential multi-user contamination (unknown)
- Physics-impossible values in a small number of shots

The goal was to build a reusable, configurable data quality validation system and then act on its
findings to produce clean analytics views.

---

## 2. What Was Built

### 2.1 Data Quality Validator Skill

**Location:** `.claude/skills/golf-data-quality/`

A full data quality validation skill with three components:

| File | Lines | Purpose |
|------|-------|---------|
| `SKILL.md` | 103 | Trigger definitions, usage guide, severity explanations, customization advice |
| `references/validation_rules.md` | ~250 | Physics-based rule definitions, per-club threshold tables, customization guide |
| `scripts/validate_golf_data.py` | 961 | Main validation engine: 12 check categories, CSV/JSON output, console summary |

The validator connects to the SQLite database, runs 12 categories of checks, and produces:
1. A console summary with counts by severity and category
2. `data_quality_report.csv` — every flagged shot with full metrics
3. `data_quality_summary.json` — machine-readable counts

### 2.2 Twelve Validation Categories

| # | Category | Severity | What It Checks |
|---|----------|----------|----------------|
| 1 | Sentinel Values | CRITICAL | Uneekor 99999 sentinel or zeros in key fields |
| 2 | Physics Violations | CRITICAL/HIGH | Carry > 400 yards, club_speed > 150 mph, negative distances |
| 3 | Smash Factor Bounds | HIGH/MEDIUM | Per-club-type COR limits (e.g., driver max 1.55, irons 1.45) |
| 4 | Total vs Carry | HIGH | Total distance should always ≥ carry distance |
| 5 | Duplicate Detection | HIGH | Same session + club + carry + ball_speed = possible duplicate |
| 6 | Club Normalization | MEDIUM/LOW | Shots where club name didn't normalize with high confidence |
| 7 | Warmup Detection | MEDIUM | Sessions/clubs tagged with warmup keywords |
| 8 | Mishit Detection | HIGH/MEDIUM | Very short carry relative to club type |
| 9 | Multi-Club Sessions | LOW | Sessions with 3+ distinct clubs (sim rounds, bag mapping) |
| 10 | Fatigue Detection | LOW | Last 20% of long sessions (40+ shots) |
| 11 | Extreme Spin Rates | MEDIUM | Backspin > 10,000 or side spin magnitude > 3,000 |
| 12 | Launch Angle Outliers | HIGH/MEDIUM | Per-club launch angle outside expected range |

### 2.3 SQLite Infrastructure

| Object | Type | Row Count | Purpose |
|--------|------|-----------|---------|
| `shot_quality_flags` | Table | 3,506 | All quality flags with shot_id, category, severity, reason |
| `shots_clean` | View | 1,920 | Excludes CRITICAL/HIGH flags (89.7% of data) |
| `shots_strict` | View | 726 | Excludes CRITICAL/HIGH/MEDIUM (33.9% of data) |
| `is_warmup` (column) | Column on `shots` | 468 tagged | INTEGER 0/1 for dashboard warmup toggle |

### 2.4 Supabase Migration

| File | Purpose |
|------|---------|
| `supabase_quality_migration.sql` | DDL: adds `is_warmup` column, creates `shot_quality_flags` table with RLS, creates clean views |
| `sync_quality_flags.py` | Python CLI to push flags and warmup tags to Supabase |

The migration SQL must be run manually in the Supabase SQL Editor first, then
`python sync_quality_flags.py` pushes the data.

### 2.5 Club Normalization Expansion (naming_conventions.py)

The `ClubNameNormalizer` was significantly expanded with 341 lines of diff:

| Pattern Group | Examples | Resolution |
|---------------|----------|------------|
| Uneekor system format | `Iron7 \| Medium`, `Wedge Pitching \| Premium` | `7 Iron`, `PW` |
| M-prefixed | `M 7`, `M 56`, `M 7 Iron` | `7 Iron`, `SW`, `7 Iron` |
| Iron + context | `9 Iron Magnolia`, `7 Iron Shoulders Right` | `9 Iron`, `7 Iron` |
| Reversed format | `Iron 7`, `Wood 3`, `Hybrid 4` | `7 Iron`, `3 Wood`, `4 Hybrid` |
| Bare digits | `7`, `9`, `6` | `7 Iron`, `9 Iron`, `6 Iron` |
| Bare degrees | `56`, `50` | `SW`, `GW` |
| Reversed warmup | `50 Warmup` | GW warmup context |
| Driving iron | `3 Driving Iron` | `3 Wood` |

The `SessionContextParser` CLUB_EXTRACTION_PATTERNS was also expanded with a reversed
number+warmup pattern to handle "50 Warmup" → GW.

---

## 3. Key Findings

### 3.1 Validation Results

```
SEVERITY SUMMARY:
  CRITICAL:    2 flags  (1 sentinel-value shot with 109,359.9 yard carry)
  HIGH:      237 flags  (smash factor, total < carry, mishits, physics)
  MEDIUM:  1,464 flags  (warmup, spin, club normalization, launch angle)
  LOW:     1,803 flags  (multi-club sessions, fatigue, informational)
  TOTAL:   3,506 flags across 1,971 unique shots
  CLEAN:     170 shots (7.9%) have zero flags
```

### 3.2 Single-Player Confirmation

Driver `club_speed` was checked across all sessions and consistently fell in the 107–115 mph
range with no bimodal distribution, confirming all 2,141 shots are Duck's data. No multi-user
contamination was found.

### 3.3 False-Positive Duplicate Detection

Two shots were flagged as duplicates (same session + club + carry + ball_speed). On examination,
they had 20+ different column values — genuinely different shots that coincidentally shared
carry and ball_speed. The flags were removed from the database.

### 3.4 Club Normalization Coverage

| Category | Shots | Percentage |
|----------|-------|------------|
| Club identified (normalizer or context parser) | 944 | 44.1% |
| Session type known, club ambiguous (sim rounds, warmups, drills) | 1,172 | 54.7% |
| Fully unresolved ("Multi") | 25 | 1.2% |

The 1,172 "type known, club ambiguous" shots are genuinely multi-club sessions where the
club field contains a round name or session label, not a specific club. Resolving these
would require inference from shot metrics (ball speed, carry, launch angle, spin).

### 3.5 Impact of Clean Views

| Club | All Data (avg carry) | Clean View (avg carry) | Change |
|------|---------------------|----------------------|--------|
| Sgt Rd1 | 1,414 yards | 156 yards | −1,258 (sentinel removed) |
| 1 Iron | 188.6 yards | 165.0 yards | −23.6 |
| 7 Iron | 180.4 yards | 176.3 yards | −4.1 |
| 8 Iron | 159.2 yards | 155.1 yards | −4.1 |

### 3.6 Analytics-Ready Dataset

The canonical "analytics-ready" dataset uses:

```sql
SELECT * FROM shots_clean WHERE is_warmup = 0
```

This returns 1,468 shots (68.6%) — clean data with no warmup contamination.

Per-club carry averages from this dataset:

| Club | Avg Carry | Shot Count |
|------|-----------|------------|
| Driver | 285.0 | 53 |
| 6 Iron | 190.5 | 67 |
| 7 Iron | 176.3 | 55 |
| 1 Iron | 165.0 | 31 |
| 8 Iron | 155.1 | 59 |
| 9 Iron | 155.0 | 14 |
| GW | 132.6 | 8 |
| PW | 125.1 | 16 |

---

## 4. Files Changed

### Modified Files

| File | Nature of Change |
|------|------------------|
| `automation/naming_conventions.py` | Major expansion: +70 lines of patterns, section headers, M-prefix, iron+context, reversed formats, bare numbers |
| `golf_stats.db` | Added `is_warmup` column, `shot_quality_flags` table (3,506 rows), `shots_clean` view, `shots_strict` view |
| `CHANGELOG.md` | Added 2026-02-11 entry covering all changes |
| `CLAUDE.md` | Updated schema table, added data quality section, new commands, expanded naming_conventions description |
| `supabase_schema.sql` | Added `shot_quality_flags` table, `is_warmup` column, `shots_clean`/`shots_strict` views, migration step 6 |

### New Files

| File | Purpose |
|------|---------|
| `sync_quality_flags.py` | CLI to push quality flags and warmup tags to Supabase |
| `supabase_quality_migration.sql` | Supabase DDL migration for quality infrastructure |
| `data_quality_report.csv` | Full export of all 3,506 flags (generated, not git-tracked) |
| `data_quality_summary.json` | Machine-readable summary (generated, not git-tracked) |
| `.claude/skills/golf-data-quality/SKILL.md` | Skill metadata and usage instructions |
| `.claude/skills/golf-data-quality/references/validation_rules.md` | Physics-based rule reference |
| `.claude/skills/golf-data-quality/scripts/validate_golf_data.py` | Main 961-line validation engine |
| `docs/SESSION_2026-02-11_DATA_QUALITY.md` | This document |

---

## 5. Supabase Sync Status

As of end-of-session:

| Item | SQLite | Supabase | Status |
|------|--------|----------|--------|
| `shots` table | 2,141 | 2,141 | In sync |
| `is_warmup` column | Added, 468 tagged | Does not exist | **Needs migration SQL** |
| `shot_quality_flags` table | 3,506 flags | Does not exist | **Needs migration SQL** |
| `shots_clean` view | Created | Does not exist | **Needs migration SQL** |
| `shots_strict` view | Created | Does not exist | **Needs migration SQL** |

**To complete Supabase sync:**

1. Open the Supabase SQL Editor for the project
2. Paste and run the contents of `supabase_quality_migration.sql`
3. Run `python sync_quality_flags.py` from the GolfDataApp directory

---

## 6. Remaining Work / Future Opportunities

### Near-Term
- **Run the Supabase migration** — paste `supabase_quality_migration.sql` into the SQL Editor, then run `python sync_quality_flags.py`
- **Dashboard integration** — wire up the `is_warmup` toggle and `shots_clean` view in the Streamlit dashboard pages
- **Re-run validator after new imports** — any new sessions imported should be re-validated

### Future
- **ML-based club inference** — for the 1,172 shots where club is ambiguous (sim rounds, etc.), use ball_speed + carry + launch_angle + spin to predict the actual club used
- **Warmup shot detection within sessions** — currently only detects warmup-named sessions; could also flag the first N shots of any session as warmup warm-up candidates
- **Threshold evolution** — as Duck's game improves, smash factor bounds, carry bounds, and other thresholds should be revisited
- **Automated quality check on import** — integrate the validator into the import pipeline so new sessions are auto-flagged

---

## 7. Commands Reference

```bash
# Run the data quality validator
python3 .claude/skills/golf-data-quality/scripts/validate_golf_data.py

# Sync quality flags to Supabase
python sync_quality_flags.py --dry-run    # Preview
python sync_quality_flags.py              # Full sync
python sync_quality_flags.py --flags-only # Only quality flags
python sync_quality_flags.py --warmup-only # Only warmup tags

# Query clean analytics data
sqlite3 golf_stats.db "SELECT club, ROUND(AVG(carry),1), COUNT(*) FROM shots_clean WHERE is_warmup = 0 AND carry > 0 AND carry < 400 GROUP BY club ORDER BY AVG(carry) DESC"

# Check flag counts
sqlite3 golf_stats.db "SELECT severity, COUNT(*) FROM shot_quality_flags GROUP BY severity"

# View counts
sqlite3 golf_stats.db "SELECT COUNT(*) FROM shots_clean"    -- 1920
sqlite3 golf_stats.db "SELECT COUNT(*) FROM shots_strict"   -- 726

# Run naming conventions tests
python -m unittest tests.unit.test_naming_conventions
```
