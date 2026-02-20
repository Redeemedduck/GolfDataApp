"""Regression tests for shim modules backed by golf-data-core."""

from __future__ import annotations

import ast
import asyncio
import concurrent.futures
import importlib
import inspect
import threading
import unittest


class TestShimImports(unittest.TestCase):
    """Verify shim modules import and expose expected symbols."""

    def test_core_shims_import(self):
        modules = (
            "exceptions",
            "services.data_quality",
            "services.time_window",
            "utils.bag_config",
            "utils.big3_constants",
            "utils.date_helpers",
            "services.analytics.executive_summary",
            "services.analytics.practice_planner",
            "services.analytics.progress_tracker",
            "services.analytics.session_grades",
        )

        for module_name in modules:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertIsNotNone(module)

    def test_shims_expose_representative_symbols(self):
        import exceptions
        from services import data_quality, time_window
        from services.analytics import (
            executive_summary,
            practice_planner,
            progress_tracker,
            session_grades,
        )
        from utils import bag_config, big3_constants, date_helpers

        self.assertTrue(hasattr(exceptions, "GolfDataAppError"))
        self.assertTrue(hasattr(data_quality, "filter_outliers"))
        self.assertTrue(hasattr(time_window, "filter_by_window"))
        self.assertTrue(hasattr(bag_config, "get_bag_order"))
        self.assertTrue(hasattr(big3_constants, "face_label"))
        self.assertTrue(hasattr(date_helpers, "parse_session_date"))
        self.assertTrue(hasattr(executive_summary, "compute_executive_summary"))
        self.assertTrue(hasattr(practice_planner, "generate_practice_plan"))
        self.assertTrue(hasattr(progress_tracker, "compute_progress_trends"))
        self.assertTrue(hasattr(session_grades, "compute_session_grades"))

    def test_golf_db_proxy_attribute_passthrough(self):
        import golf_db

        original_path = golf_db.SQLITE_DB_PATH
        temp_path = "/tmp/golf-data-shim-test.db"

        try:
            golf_db.SQLITE_DB_PATH = temp_path
            self.assertEqual(golf_db.SQLITE_DB_PATH, temp_path)
        finally:
            golf_db.SQLITE_DB_PATH = original_path


class TestProxyThreadSafety(unittest.TestCase):
    """Regression tests for golf_db proxy under threaded contexts.

    The _GolfDBProxy pattern (sys.modules replacement + __getattr__ delegation)
    breaks under Streamlit's hot-reloader + background thread combination.
    These tests verify that attribute access works from threads — the exact
    scenario that caused the SQLITE_DB_PATH AttributeError (fix: ebc15463b).
    """

    def test_proxy_attribute_access_from_thread(self):
        """golf_db.SQLITE_DB_PATH must be accessible from a background thread."""
        import golf_db

        result = {}

        def access_proxy():
            try:
                result["path"] = golf_db.SQLITE_DB_PATH
                result["has_init_db"] = hasattr(golf_db, "init_db")
            except AttributeError as e:
                result["error"] = str(e)

        thread = threading.Thread(target=access_proxy)
        thread.start()
        thread.join(timeout=5)

        self.assertNotIn("error", result, f"Proxy failed in thread: {result.get('error')}")
        self.assertIn("path", result)
        self.assertTrue(result["has_init_db"])

    def test_proxy_attribute_access_from_thread_with_event_loop(self):
        """golf_db proxy must work from a thread running its own event loop.

        This reproduces the exact Streamlit sync bug: a daemon thread calls
        asyncio.run() which creates an event loop, and code inside that loop
        accesses golf_db attributes through the proxy.
        """
        import golf_db

        results = {}
        errors = []

        async def access_in_async():
            return golf_db.SQLITE_DB_PATH

        def thread_with_loop():
            try:
                path = asyncio.run(access_in_async())
                results["path"] = path
            except AttributeError as e:
                errors.append(str(e))

        thread = threading.Thread(target=thread_with_loop, daemon=True)
        thread.start()
        thread.join(timeout=5)

        self.assertEqual(errors, [], f"Proxy failed in threaded event loop: {errors}")
        self.assertIn("path", results)

    def test_proxy_concurrent_access(self):
        """Proxy must handle concurrent attribute access from multiple threads."""
        import golf_db

        attrs = ["SQLITE_DB_PATH", "init_db", "get_all_shots", "save_shot"]
        errors = []

        def access_attr(attr_name):
            try:
                val = getattr(golf_db, attr_name)
                return (attr_name, val is not None)
            except AttributeError as e:
                errors.append(f"{attr_name}: {e}")
                return (attr_name, False)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(access_attr, a) for a in attrs * 3]
            results = [f.result(timeout=5) for f in futures]

        self.assertEqual(errors, [], f"Concurrent proxy access failed: {errors}")
        self.assertTrue(all(ok for _, ok in results))

    def test_direct_import_matches_proxy(self):
        """golf_data.db attributes must match golf_db proxy attributes."""
        import golf_db
        import golf_data.db as direct

        for attr in ["SQLITE_DB_PATH", "init_db", "get_all_shots"]:
            with self.subTest(attr=attr):
                proxy_val = getattr(golf_db, attr)
                direct_val = getattr(direct, attr)
                self.assertIs(proxy_val, direct_val,
                              f"{attr}: proxy and direct import diverge")


class TestThreadedShimModules(unittest.TestCase):
    """Verify all shim modules work from background threads."""

    SHIM_MODULES = (
        "exceptions",
        "services.data_quality",
        "services.time_window",
        "utils.bag_config",
        "utils.big3_constants",
        "utils.date_helpers",
        "services.analytics.executive_summary",
        "services.analytics.practice_planner",
        "services.analytics.progress_tracker",
        "services.analytics.session_grades",
    )

    def test_shim_imports_from_thread(self):
        """All shim modules must import and expose symbols from a thread."""
        errors = []

        def import_in_thread(module_name):
            try:
                mod = importlib.import_module(module_name)
                # Verify the module has at least one public attribute
                public = [a for a in dir(mod) if not a.startswith("_")]
                if not public:
                    errors.append(f"{module_name}: no public attributes")
            except Exception as e:
                errors.append(f"{module_name}: {e}")

        threads = []
        for name in self.SHIM_MODULES:
            t = threading.Thread(target=import_in_thread, args=(name,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5)

        self.assertEqual(errors, [], f"Shim imports failed from threads: {errors}")


class TestAutomationBypassesProxy(unittest.TestCase):
    """Verify automation modules import golf_data.db directly, not golf_db.

    Code running in Streamlit's background threads MUST bypass the golf_db
    proxy shim. This test reads source files to ensure no proxy usage leaks
    back in. Catches the bug at the source-code level — no runtime needed.
    """

    # Modules that run in Streamlit's daemon thread and must not use golf_db
    THREAD_CONTEXT_FILES = {
        "automation/session_discovery.py": "golf_data.db",
        "automation/backfill_runner.py": "golf_data.db",
        "services/sync_service.py": "golf_data.db",
    }

    def test_no_golf_db_import_in_thread_context_modules(self):
        """Thread-context modules must not import golf_db (the proxy shim)."""
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        for rel_path, expected_import in self.THREAD_CONTEXT_FILES.items():
            filepath = os.path.join(repo_root, rel_path)
            with self.subTest(file=rel_path):
                with open(filepath) as f:
                    source = f.read()

                tree = ast.parse(source, filename=rel_path)

                for node in ast.walk(tree):
                    # Check `import golf_db` statements
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.assertNotEqual(
                                alias.name, "golf_db",
                                f"{rel_path}:{node.lineno} imports golf_db "
                                f"(the proxy shim). Use `import {expected_import}` "
                                f"instead to avoid thread-safety issues.",
                            )
                    # Check `from golf_db import ...` statements
                    if isinstance(node, ast.ImportFrom) and node.module == "golf_db":
                        self.fail(
                            f"{rel_path}:{node.lineno} imports from golf_db "
                            f"(the proxy shim). Use `from {expected_import} import ...` "
                            f"instead to avoid thread-safety issues.",
                        )


if __name__ == "__main__":
    unittest.main()
