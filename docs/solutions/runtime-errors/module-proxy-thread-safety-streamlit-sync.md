---
title: "Module Proxy Shim Fails in Streamlit Threading Context"
date: 2026-02-19
category: runtime-errors
tags:
  - streamlit
  - threading
  - module-proxy
  - automation
  - golf-data-core
severity: high
modules_affected:
  - automation/session_discovery.py
  - golf_db.py
symptoms:
  - "AttributeError: module 'golf_db' has no attribute 'SQLITE_DB_PATH'"
  - "Error when clicking 'Sync New Sessions' in Streamlit UI"
  - "CLI and script usage unaffected"
root_cause_type: module-proxy-thread-safety
fix_commit: ebc15463b
related_commits:
  - 4fb0b8868  # refactor: replace 11 modules with thin shims
  - cf6bc83cb  # fix: harden shim imports
  - 172d364b1  # test: add shim import regression tests
  - c45cce7c8  # fix: add timeout to sync pipeline thread
  - f0caefbf1  # refactor: harden sync pipeline with review findings
---

# Module Proxy Shim Fails in Streamlit Threading Context

## Problem

The Streamlit UI fails with `module 'golf_db' has no attribute 'SQLITE_DB_PATH'` when clicking the "Sync New Sessions" button. The same import works fine from CLI and simple scripts.

The error occurs in `automation/session_discovery.py:172` during `SessionDiscovery.__init__`, which accesses `golf_db.SQLITE_DB_PATH` from a background thread spawned by Streamlit's sync pipeline.

## Investigation

1. **CLI verification:** `python3 -c "import golf_db; print(golf_db.SQLITE_DB_PATH)"` returned the correct path — proxy works outside Streamlit.

2. **Isolated thread test:** Simulated the thread + event loop context in a standalone script — proxy delegation worked without issues.

3. **Live reproduction:** Used Playwright browser automation to trigger the bug in the running Streamlit app — confirmed consistent `AttributeError` on every sync attempt.

4. **Proxy pattern analysis:** `golf_db.py` implements `_GolfDBProxy(types.ModuleType)` that replaces itself in `sys.modules[__name__]` and delegates `__getattr__` to `golf_data.db`.

5. **Root cause identification:** Streamlit's hot-reloader + background thread combination breaks the proxy's attribute delegation chain.

## Root Cause

The `_GolfDBProxy` module-replacement pattern (`sys.modules[__name__] = proxy`) is fragile under Streamlit's runtime. Streamlit's script runner can re-execute module bodies while background threads hold references, causing `__getattr__` delegation to fail with `AttributeError`.

The sync pipeline runs in a background daemon thread (to avoid blocking Streamlit's event loop). When this thread accesses `golf_db.SQLITE_DB_PATH`, the proxy's delegation to `golf_data.db` breaks — likely because Streamlit's hot-reloader has re-executed the module body, replacing the proxy while the thread still holds a stale reference.

Key architectural context: The proxy exists because `golf_db.py` was migrated from a 2,400-line monolith to a thin shim delegating to the `golf-data-core` package (`golf_data.db`). The proxy pattern maintains backward compatibility for 36+ files that `import golf_db`.

## Solution

Bypass the proxy entirely — import `golf_data.db` directly in code that runs in thread contexts.

**Before (`automation/session_discovery.py`):**
```python
try:
    import golf_db
    HAS_GOLF_DB = True
except ImportError:
    HAS_GOLF_DB = False

# In SessionDiscovery.__init__:
elif HAS_GOLF_DB:
    self.db_path = golf_db.SQLITE_DB_PATH
```

**After:**
```python
try:
    import golf_data.db as _golf_data_db
    HAS_GOLF_DATA = True
except ImportError:
    HAS_GOLF_DATA = False

# In SessionDiscovery.__init__:
elif HAS_GOLF_DATA:
    self.db_path = _golf_data_db.SQLITE_DB_PATH
```

4 lines changed. The `golf_db.py` proxy shim remains in place for all other backward-compatible usage.

## Verification

- **Unit tests:** 436 tests passing (full suite)
- **Live app:** Streamlit "Sync New Sessions" button enters discovery phase successfully (previously failed instantly with AttributeError)
- **CLI:** `python3 automation_runner.py discover --headless` still works unchanged

## Prevention Strategies

### For this codebase

1. **Any code running in background threads should import `golf_data.db` directly**, not through the `golf_db` proxy shim.

2. **Other shim modules to watch:** The star-import shims (`exceptions.py`, `services/data_quality.py`, `services/time_window.py`, `services/analytics/*.py`) use a safer pattern (`from golf_data.X import *`) and don't do `sys.modules` replacement. They are unlikely to hit this issue.

### General best practices for module proxy patterns

- Prefer explicit re-exports (`from pkg import func1, func2`) over `sys.modules` replacement with `__getattr__` delegation
- `sys.modules[__name__] = proxy` is inherently fragile in environments with hot-reloading (Streamlit, Django autoreload, Jupyter)
- If you must use a proxy, test it under threaded conditions with the actual runtime (not just standalone scripts)
- Document which imports go through the proxy and which bypass it

## Cross-References

- **Shim import tests:** `tests/unit/test_shim_imports.py` — tests proxy attribute passthrough (added in `172d364b1`)
- **Sync service hardening:** `services/sync_service.py` — thread timeout, double-start guard, safe callbacks (commits `c45cce7c8`, `f0caefbf1`)
- **Core package extraction:** commit `4fb0b8868` — the refactor that created the proxy pattern
- **CLAUDE.md:** "Shared Data Layer: golf-data-core Package" section documents the shim architecture
