# Fix Test-Ordering Conflicts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make all tests pass when run together (`python -m unittest discover -s tests`), not just in isolation.

**Architecture:** Replace fragile `sys.modules` mocking with `unittest.mock.patch` context managers that properly set up and tear down mocks per test class. Each test file must leave `sys.modules` exactly as it found it.

**Tech Stack:** Python unittest, unittest.mock.patch

---

## Background

Three test files inject mocks into `sys.modules` at module-load time. When unittest discovers and runs all tests in a single process, the load order is non-deterministic. If a test file that imports the *real* module loads first, `sys.modules.setdefault()` becomes a no-op for later files that try to inject mocks — and vice versa, mock injections break later files that expect the real module.

### Root Causes

| Test File | Problem | Effect |
|-----------|---------|--------|
| `test_agent_tools.py` | Uses `sys.modules.setdefault("golf_db", mock)` at module level | No-op if real `golf_db` already loaded by another test |
| `test_claude_provider.py` | Sets `sys.modules["services"] = MagicMock()` at module level | Breaks `test_sync_service.py` which does `from services.sync_service import ...` |
| `test_local_coach.py` | Imports real providers which register in the global registry | Provider ordering/state leaks into other tests |

### The Fix Pattern

Instead of permanently injecting mocks into `sys.modules` at module level, use `setUpModule()`/`tearDownModule()` (or `setUpClass`/`tearDownClass`) to:
1. Save original `sys.modules` entries
2. Inject mocks
3. Import the module under test
4. Restore originals on teardown

This ensures each test file cleans up after itself.

---

### Task 1: Fix `test_agent_tools.py` mock isolation

**Files:**
- Modify: `tests/unit/test_agent_tools.py:26-40`

**Step 1: Read the current mock setup**

The current code at the top of the file:
```python
_golf_db_mock = MagicMock(name="golf_db")
sys.modules.setdefault("golf_db", _golf_db_mock)

for _dep in ("dotenv", "supabase", "automation", "automation.naming_conventions", "exceptions"):
    sys.modules.setdefault(_dep, MagicMock(name=_dep))

import agent.tools as tools_module
```

**Step 2: Replace with `setUpModule`/`tearDownModule`**

Replace lines 26–40 with:
```python
# ---------------------------------------------------------------------------
# Module-level mock setup/teardown — ensures sys.modules is restored after
# this test file runs so other test files aren't affected.
# ---------------------------------------------------------------------------
_MOCKED_MODULES = {}
_ORIGINAL_MODULES = {}

def setUpModule():
    """Inject golf_db mock before importing agent.tools."""
    global tools_module
    _deps = ["golf_db", "dotenv", "supabase", "automation",
             "automation.naming_conventions", "exceptions"]
    for dep in _deps:
        _ORIGINAL_MODULES[dep] = sys.modules.get(dep, None)
        mock = MagicMock(name=dep)
        sys.modules[dep] = mock
        _MOCKED_MODULES[dep] = mock

    # Force re-import of agent.tools with our mocked deps
    for key in list(sys.modules):
        if key.startswith("agent."):
            del sys.modules[key]

    import agent.tools as _tools
    globals()["tools_module"] = _tools

def tearDownModule():
    """Restore original sys.modules entries."""
    for dep, original in _ORIGINAL_MODULES.items():
        if original is None:
            sys.modules.pop(dep, None)
        else:
            sys.modules[dep] = original
    # Clean up agent.tools so other tests get a fresh import
    for key in list(sys.modules):
        if key.startswith("agent."):
            del sys.modules[key]

tools_module = None  # Will be set by setUpModule
```

**Step 3: Run the test file in isolation**

Run: `venv/bin/python3 -m unittest tests.unit.test_agent_tools -v 2>&1 | tail -5`
Expected: `Ran 40 tests ... OK`

**Step 4: Run with conflicting file to verify no pollution**

Run: `venv/bin/python3 -m unittest tests.unit.test_local_coach tests.unit.test_agent_tools -v 2>&1 | tail -5`
Expected: `Ran 54 tests ... OK` (previously FAILED with 12 failures)

**Step 5: Commit**

```bash
git add tests/unit/test_agent_tools.py
git commit -m "fix(tests): isolate sys.modules mocks in test_agent_tools

Use setUpModule/tearDownModule to save and restore sys.modules
entries, preventing mock pollution when tests run in different orders."
```

---

### Task 2: Fix `test_claude_provider.py` mock isolation

**Files:**
- Modify: `tests/unit/test_claude_provider.py:15-27`

**Step 1: Read the current mock setup**

The current code at the top of the file:
```python
_mock_registry = MagicMock()
_mock_registry.register_provider = lambda cls: cls
sys.modules["services"] = MagicMock()
sys.modules["services.ai"] = MagicMock()
sys.modules["services.ai.registry"] = _mock_registry

_provider_path = Path(__file__).resolve().parent.parent.parent / "services" / "ai" / "providers" / "claude_provider.py"
_spec = importlib.util.spec_from_file_location("claude_provider", _provider_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
ClaudeProvider = _mod.ClaudeProvider
```

**Step 2: Replace with `setUpModule`/`tearDownModule`**

Replace lines 15–27 with:
```python
# ---------------------------------------------------------------------------
# Module-level mock setup/teardown — loads claude_provider.py by file path
# to avoid the services.ai.providers package auto-import chain, while
# ensuring sys.modules is restored after this file runs.
# ---------------------------------------------------------------------------
_ORIGINAL_MODULES = {}
ClaudeProvider = None

def setUpModule():
    global ClaudeProvider
    _deps = ["services", "services.ai", "services.ai.registry"]
    for dep in _deps:
        _ORIGINAL_MODULES[dep] = sys.modules.get(dep, None)

    _mock_registry = MagicMock()
    _mock_registry.register_provider = lambda cls: cls
    sys.modules["services"] = MagicMock()
    sys.modules["services.ai"] = MagicMock()
    sys.modules["services.ai.registry"] = _mock_registry

    _provider_path = (
        Path(__file__).resolve().parent.parent.parent
        / "services" / "ai" / "providers" / "claude_provider.py"
    )
    _spec = importlib.util.spec_from_file_location("claude_provider", _provider_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    ClaudeProvider = _mod.ClaudeProvider

def tearDownModule():
    for dep, original in _ORIGINAL_MODULES.items():
        if original is None:
            sys.modules.pop(dep, None)
        else:
            sys.modules[dep] = original
```

**Step 3: Run the test file in isolation**

Run: `venv/bin/python3 -m unittest tests.unit.test_claude_provider -v 2>&1 | tail -5`
Expected: `Ran 9 tests ... OK`

**Step 4: Run with sync_service to verify no pollution**

Run: `venv/bin/python3 -m unittest tests.unit.test_claude_provider tests.unit.test_sync_service -v 2>&1 | tail -5`
Expected: `Ran 50 tests ... OK` (previously FAILED with 1 import error)

**Step 5: Commit**

```bash
git add tests/unit/test_claude_provider.py
git commit -m "fix(tests): isolate sys.modules mocks in test_claude_provider

Use setUpModule/tearDownModule to save and restore services.*
entries, preventing test_sync_service import failure."
```

---

### Task 3: Verify full suite passes

**Files:**
- None (verification only)

**Step 1: Run the complete test suite**

Run: `venv/bin/python3 -m unittest discover -s tests -v 2>&1 | tail -10`
Expected: `Ran 320 tests ... OK` (possibly with skips, but 0 failures, 0 errors)

**Step 2: Run in reverse alphabetical order to stress-test ordering**

Run: `venv/bin/python3 -m unittest tests.unit.test_sync_service tests.unit.test_local_coach tests.unit.test_claude_provider tests.unit.test_agent_tools tests.unit.test_agent_core -v 2>&1 | tail -5`
Expected: All pass

**Step 3: Run CI lint check**

Run: `venv/bin/python3 -m py_compile tests/unit/test_agent_tools.py tests/unit/test_claude_provider.py`
Expected: No output (clean compile)

**Step 4: If any failures remain, diagnose and fix**

If there are remaining ordering issues, check:
- Does `test_agent_core.py` have any `sys.modules` manipulation? (It should be clean — it only mocks via `unittest.mock.patch`)
- Are there other test files that set `sys.modules` globally?

Run: `grep -rn "sys.modules\[" tests/ --include="*.py"` to find any remaining global mock injections.

**Step 5: Commit verification**

```bash
git commit --allow-empty -m "test: verify full test suite passes with fixed isolation"
```

(Only if fixes were needed in this task. If Step 1 passes cleanly, skip the commit.)

---

### Task 4: Update CLAUDE.md testing docs

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add a note about test isolation**

In the Testing section (after the fixtures table), add:

```markdown
### Test Isolation

Tests that mock `sys.modules` (e.g., `test_agent_tools.py`, `test_claude_provider.py`) use `setUpModule()`/`tearDownModule()` to save and restore entries. This prevents test-ordering conflicts when running the full suite. **Never use `sys.modules["foo"] = mock` at module level** — always wrap in setup/teardown.
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add test isolation guidance to CLAUDE.md"
```
