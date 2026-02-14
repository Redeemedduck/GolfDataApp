"""Tests for bag configuration loader."""

import unittest
from utils.bag_config import (
    get_bag_order, get_club_sort_key, is_in_bag,
    get_smash_target, get_all_smash_targets,
)


class TestBagConfig(unittest.TestCase):
    """Verify bag config loads correctly."""

    def test_bag_order_returns_list(self):
        order = get_bag_order()
        self.assertIsInstance(order, list)
        self.assertIn("Driver", order)

    def test_club_sort_key_driver_first(self):
        self.assertEqual(get_club_sort_key("Driver"), 0)

    def test_is_in_bag_true(self):
        self.assertTrue(is_in_bag("Driver"))
        self.assertTrue(is_in_bag("7 Iron"))

    def test_is_in_bag_false(self):
        self.assertFalse(is_in_bag("Putter"))
        self.assertFalse(is_in_bag("Nonexistent"))


class TestSmashTargets(unittest.TestCase):
    """Verify smash factor target accessors."""

    def test_get_smash_target_driver(self):
        target = get_smash_target("Driver")
        self.assertIsNotNone(target)
        self.assertAlmostEqual(target, 1.49, places=1)

    def test_get_smash_target_iron(self):
        target = get_smash_target("7 Iron")
        self.assertIsNotNone(target)
        self.assertGreater(target, 1.0)
        self.assertLess(target, 1.5)

    def test_get_smash_target_unknown_returns_none(self):
        target = get_smash_target("Putter")
        self.assertIsNone(target)

    def test_get_all_smash_targets_returns_dict(self):
        targets = get_all_smash_targets()
        self.assertIsInstance(targets, dict)
        self.assertIn("Driver", targets)
        self.assertIn("7 Iron", targets)

    def test_all_bag_clubs_have_targets(self):
        order = get_bag_order()
        targets = get_all_smash_targets()
        for club in order:
            self.assertIn(club, targets, f"Missing smash target for {club}")


if __name__ == "__main__":
    unittest.main()
