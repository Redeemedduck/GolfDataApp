# Backfill Pipeline Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Run validated backfill of 12 sessions with automated proceed/abort logic, then research and implement improved session naming.

**Architecture:** Five-stage sequential pipeline with parallel research phase. Validation gate between dry run and actual backfill. Research agents investigate naming patterns before implementation.

**Tech Stack:** Python, Playwright, Codex CLI, SQLite, Supabase

---

## Pipeline Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Stage 1    │────▶│  Stage 2    │────▶│  Stage 3    │────▶│  Stage 4    │────▶│  Stage 4.5  │────▶│  Stage 5    │
│  Dry Run    │     │  Validate   │     │  Backfill   │     │  Research   │     │  Synthesis  │     │  Naming     │
│  (3 sess)   │     │  (Codex)    │     │  (12 sess)  │     │  (Parallel) │     │  (Codex)    │     │  (Codex)    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │                   │                   │                   │
      ▼                   ▼                   ▼                   ▼                   ▼                   ▼
   Output:             Gate:              Output:             Output:             Output:             Output:
   - Preview          PASS/FAIL           - New shots         - 4 research        - SYNTHESIS.md      - Names
   - Metrics          - Errors?           - Dates             - docs              - Schema            - Tags
   - Dates            - Dates?            - Sync status                           - Priorities        - Updated DB
```

**Stage transitions:**
- Stage 1 → 2: Always (dry run output feeds validation)
- Stage 2 → 3: Only if all criteria pass
- Stage 3 → 4: Always (research runs on whatever was imported)
- Stage 4 → 4.5: After all 4 research agents complete
- Stage 4.5 → 5: Always (implementation uses synthesis)

**Failure handling:**
- Stage 2 fails → Pipeline stops, report generated, human reviews
- Stage 3 fails mid-run → Checkpoint saved, resumable later

---

## Stage 1: Dry Run

**Executor:** Claude CLI (browser automation)

**Command:**
```bash
python automation_runner.py backfill --start 2025-01-01 --max-sessions 3 --dry-run --headless
```

**Output captured:**
- Session IDs that would be imported
- Dates extracted for each session
- Any warnings or errors
- Rate limiter status

---

## Stage 2: Validation Gate

**Executor:** Codex agent

**Criterion 1: Zero Errors**
```
Check for:
- No Python exceptions in output
- No HTTP 4xx/5xx responses
- No "failed" or "error" in logs
- Rate limiter not triggered (no 429s)

Pass: 0 errors detected
Fail: Any error present
```

**Criterion 2: Date Consistency**
```
For each session:
- session_date is present (not null)
- Date is not in future
- Date is after 2020-01-01
- Date source = "listing_page" preferred

Pass: All dates valid
Fail: Any missing or invalid date
```

**Gate Decision:**
- Both pass → Proceed to Stage 3 automatically
- Either fail → Stop, generate report, await human review

---

## Stage 3: Backfill Execution

**Executor:** Claude CLI (browser automation, rate-limited)

**Command:**
```bash
python automation_runner.py backfill --start 2025-01-01 --max-sessions 12 --headless
```

**Duration:** ~1-2 hours (6 sessions/hour rate limit)

**Output:**
- Imported shots added to SQLite
- Synced to Supabase
- Checkpoint updated in backfill_runs table

---

## Stage 4: Research Phase (Parallel)

**Executor:** 4 Codex agents in parallel

### Agent A: Portal Naming Patterns
```
Investigate:
- How Uneekor portal names reports in the UI
- URL structure patterns (report IDs, API keys)
- Any patterns in portal_name field from scraping
- Relationship between report_id and display name

Sources to analyze:
- sessions_discovered table (portal_name column)
- Sample URLs from source_url column
- automation/uneekor_portal.py (existing parsing)

Output: docs/research/portal-naming-patterns.md
```

### Agent B: Date & Time Inconsistencies
```
Investigate:
- Date formats seen across the portal (YYYY.MM.DD, Jan 15, etc.)
- Timezone handling (UTC vs local)
- Cases where dates are missing or ambiguous
- Gaps between session dates and import dates

Sources to analyze:
- sessions_discovered (session_date, date_added, date_source)
- automation/naming_conventions.py (parse_listing_date)
- Listing page DOM structure

Output: docs/research/date-inconsistencies.md
```

### Agent C: Club Naming Variations
```
Investigate:
- All club name variations in current data
- Uneekor's native naming vs our normalization
- Edge cases: "7i" vs "7 Iron" vs "7-iron" vs "Iron 7"
- Wedge naming: "PW" vs "Pitching Wedge" vs "P Wedge"

Sources to analyze:
- shots table (club column) - unique values
- automation/naming_conventions.py (normalize_club_name)
- tag_catalog table

Output: docs/research/club-naming-variations.md
```

### Agent D: Codebase Gap Analysis
```
Investigate:
- What naming_conventions.py already handles
- What's missing or incomplete
- How sessions are currently auto-tagged
- Opportunities to improve session identification

Sources to analyze:
- automation/naming_conventions.py (full review)
- golf_db.py (session tagging logic)
- automation/session_discovery.py

Output: docs/research/codebase-gap-analysis.md
```

---

## Stage 4.5: Research Synthesis

**Executor:** Codex agent

**Inputs:**
- docs/research/portal-naming-patterns.md (Agent A)
- docs/research/date-inconsistencies.md (Agent B)
- docs/research/club-naming-variations.md (Agent C)
- docs/research/codebase-gap-analysis.md (Agent D)

**Process:**
1. Identify overlapping findings
2. Resolve conflicting recommendations
3. Prioritize issues by impact
4. Design unified naming schema

**Output:** docs/research/SYNTHESIS.md containing:
- Executive summary of findings
- Proposed naming schema
- Edge cases to handle
- Recommended implementation order

**Proposed Naming Schema:**
```
Session name format:
  "{date} {primary_club} {session_type} ({shot_count} shots)"

Examples:
  "2026-02-02 Driver Focus (25 shots)"
  "2026-01-28 Mixed Practice (45 shots)"
  "2026-01-26 Short Game (18 shots)"

Session types (auto-detected):
  - Driver Focus: >60% driver shots
  - Iron Work: >60% iron shots
  - Short Game: >60% wedge/putter
  - Mixed Practice: no dominant club
```

---

## Stage 5: Naming Implementation

**Executor:** Codex agent

**Implementation Tasks:**

1. **Update naming_conventions.py**
   - Add `generate_session_name(session)` function
   - Add `detect_session_type(shots)` function
   - Handle all edge cases from research

2. **Update golf_db.py**
   - Add `update_session_name(report_id, name)` function
   - Add `batch_update_session_names()` for existing data

3. **Update session_discovery.py**
   - Auto-generate names on new session discovery
   - Store session_type tag

4. **Backfill existing sessions**
   - Apply naming to all 118 sessions in DB
   - Verify no duplicates created

**Validation before commit:**
- All tests pass
- Sample of 10 sessions have sensible names
- No regression in existing functionality

---

## Timeline Summary

| Stage | Executor | Duration | Output |
|-------|----------|----------|--------|
| 1. Dry Run | Claude CLI | ~2 min | Preview of 3 sessions |
| 2. Validate | Codex | ~1 min | PASS/FAIL gate |
| 3. Backfill | Claude CLI | ~2 hours | 12 sessions imported |
| 4. Research | 4x Codex parallel | ~10 min | 4 research docs |
| 4.5 Synthesis | Codex | ~5 min | SYNTHESIS.md |
| 5. Naming | Codex | ~15 min | Updated naming system |

**Total estimated time:** ~2.5 hours (mostly backfill wait time)

---

## Success Criteria

- [ ] Dry run completes with zero errors
- [ ] All dates valid and consistent
- [ ] 12 sessions successfully imported
- [ ] Research documents comprehensive
- [ ] Synthesis provides clear naming schema
- [ ] Naming system implemented and tested
- [ ] Existing sessions renamed
- [ ] All tests pass
