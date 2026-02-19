"""Regression tests for shim modules backed by golf-data-core."""

from __future__ import annotations

import importlib
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


if __name__ == "__main__":
    unittest.main()
