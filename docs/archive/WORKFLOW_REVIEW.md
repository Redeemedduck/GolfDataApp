# Workflow Review & Recommendations

## Context
This document tracks the high-level review of the GolfDataApp data workflow, including Uneekor ingestion, database behavior, and editing/cleaning requirements.

## Current Observations (Initial)
- The system is local-first (SQLite) with optional Supabase mirroring.
- Data can feel “missing” when SQLite is empty or volume mounts are misaligned.
- Editing workflows for warmups, simulator rounds, and club normalization need clearer, hands-on tooling.

## Step 1: Data Flow & Mismatch Points
### Data Flow (Today)
1. **Uneekor report URL** → parsed for `report_id` and `key`.
2. **Uneekor API** returns **club sessions** with shot arrays.
3. **Scraper**:
   - Converts units (m/s → mph, meters → yards).
   - Builds a normalized shot record with `shot_id`, `session_id` (report_id), and metrics.
   - Saves to **SQLite** and (if configured) **Supabase**.
4. **UI/AI reads** from SQLite by default, with optional Supabase fallback.

### Where Data “Disappears”
- **SQLite empty**: happens on new container or wrong volume mount; UI shows no data.
- **Supabase not configured**: cloud backup disabled; only SQLite is used.
- **Read source mismatch**: SQLite has data but UI is configured to read Supabase (or vice versa).

### Report Realities That Cause “Messy” Data
- Warmup shots mixed into full sessions.
- Simulator rounds mix clubs under the same club label.
- Some shots have missing Optix fields or images.
- Uneekor software behavior differs by device: VIEW stores shots locally; Ignite requires manual export per session.

## Field Research Notes (Uneekor + GSPro)
- Uneekor VIEW (EYE XO/EYE MINI) stores shot data in a local `VIEW.bytes` file (no manual CSV export required).
- Uneekor Ignite (QED) does not persist sessions; export must happen immediately after each session.
- Typical simulator practice flow includes warmup → gapping → focused drills → GSPro round play; a single “session” can mix these.
- A GSPro round often mixes clubs under one label (e.g., “7 Iron” across different on-course situations), which makes raw session data look inconsistent.

## Step 2: Desired Editing Workflow (Draft)
### Goals
- Remove warmups without deleting full sessions.
- Split a single report into meaningful sub-sessions (warmup, practice, simulator round).
- Normalize club names when a report uses the same label for different clubs.
- Label sessions with a high-level context (Practice vs Round vs Gapping).

### Proposed Hands-On Workflow
1. **Import** a report once (all raw shots).
2. **Review Session Summary** (shots count, clubs, date).
3. **Tag Shots**:
   - Warmup vs Practice vs Round.
   - Optional: notes (e.g., “new shaft”, “range balls”).
4. **Split Session** by tag into new session IDs:
   - `2025-01-03_warmup`
   - `2025-01-03_round`
5. **Normalize Clubs**:
   - Rename within session to disambiguate: `7 Iron (SIM)` vs `7 Iron (Range)`.
6. **Cleanup**:
   - Delete warmup shots if they are no longer needed.

### Required Database Operations
- Tagging: add `shot_tag` or `session_type` field.
- Split session by tag into new session IDs.
- Bulk rename clubs within a session.
- Soft delete + restore (already present via archive).
 - Session metadata: `session_type` for filtering and reporting.

### Gaps vs Current UI
- There is no tagging UI today.
- Session split exists but is manual (select shot IDs).
- No guided workflow for warmup/round cleanup.

### Tag Strategy (Revised)
- Maintain a **shared tag catalog** (e.g., Warmup, Practice, Round, Fitting, On-Course).
- Tags are **applied per session**, not globally enforced, so each session can be unique.
- Allow custom tags while keeping a baseline list for consistency in reporting.

## Step 3: Data-Source Policy & Roadmap
### Policy (What “Just Works” Should Mean)
- **Auto-prefer SQLite** when it has data.
- **Auto-fallback to Supabase** if SQLite is empty or missing.
- **Visible UI toggle** to override (power users only).
- **Consistency checks**: show SQLite vs Supabase shot counts in UI.

### Roadmap (Workflow-Driven)
1. **Add tagging** (`shot_tag` or `session_type`) and a UI for tagging ranges.
2. **Guided split**: split session by tag into new session IDs.
3. **Club normalization**: bulk rename with presets (e.g., SIM vs Range).
4. **Validation**: show warnings for missing metrics and outliers.
5. **Reconciliation**: compare SQLite ↔ Supabase counts and flag drift.

### Why This Fixes the Sloppiness
- The system becomes deterministic: data is always visible without manual env toggles.
- Cleanup becomes a normal workflow step instead of ad-hoc deletes.
- Reports stay usable even when Uneekor labels are inconsistent.

## Open Questions
- What is the expected behavior when SQLite is empty but Supabase has data?
- How should sessions be segmented when a report includes warmups or full simulator rounds?
- What are the preferred rules for club naming normalization across mixed sessions?

## Recommendations (Pending)
- Map the current data flow end-to-end and identify where data loss or mismatch occurs.
- Design explicit edit workflows: delete warmups, split sessions, rename clubs, and tag shots.
- Implement an auto-fallback read policy with a visible UI toggle for power users.

## Next Actions
- Step 1: Document the data flow and failure/mismatch points.
- Step 2: Define the desired editing workflow and required UI/database operations.
- Step 3: Produce a concrete improvement roadmap tied to those workflows.
