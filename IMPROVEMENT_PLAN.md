# Planned Improvements & Implementation Plan

## Current Status (Completed)
- Data-source toggle + auto-fallback between SQLite and Supabase.
- `shot_tag` support in SQLite + Supabase schema.
- Tagging + split workflow UI (basic) in Database Manager.
- Session search, cached reads, and basic shot counts in sidebars.

## Planned Phases (Next 5)

### Phase 1: Tag Catalog + Session-Scoped Usage
**Steps**
1. Add a shared tag catalog (defaults: Warmup, Practice, Round, Fitting).
2. Allow per-session tag selection without enforcing global sameness.
3. Save tag presets (e.g., “Warmup → first 15 shots”).
**Benefits**: Consistent labeling across sessions while preserving session uniqueness.

### Phase 2: One-Click Split + Cleanup
**Steps**
1. “Tag + Split” wizard to auto-create new sessions per tag.
2. Optional: delete or archive warmup shots after split.
3. Add “undo last split” log entry for safety.
**Benefits**: Fast cleanup of mixed sessions with lower error risk.

### Phase 3: Club Normalization Tooling
**Steps**
1. Bulk rename clubs inside a session (e.g., “7 Iron (SIM)”).
2. Preset mappings (SIM/RANGE, New Shaft, Practice Ball).
3. Flag mixed-club anomalies during import.
**Benefits**: Cleaner stats, more accurate per-club analysis.

### Phase 4: Simulator Context & Round Metadata
**Steps**
1. Add session metadata: activity type, GSPro round vs practice.
2. Optional hole/round markers if available in source.
3. UI filters for practice vs round analysis.
**Benefits**: Reports match how sessions actually happen in real life.

### Phase 5: Data Reliability & Reconciliation
**Steps**
1. Reconcile SQLite vs Supabase counts with a drift warning.
2. Paginated Supabase reads for large sessions.
3. Add validation for missing key metrics at import.
**Benefits**: Fewer “empty DB” surprises and higher trust in analytics.

## Implementation Notes
- Each phase is intended to be small and testable with unit checks.
- Update `README.md` and `SETUP_GUIDE.md` when behavior changes.

## Status
All five phases are implemented. Remaining follow-ups are operational:
- Apply Supabase schema updates (`session_type`, `tag_catalog`) if not already present.
- Use the Tag + Split wizard to establish warmup/practice/round workflows.
