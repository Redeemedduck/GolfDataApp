"""Tests for bag configuration loader."""

import unittest

from utils.bag_config import (
    get_all_smash_targets,
    get_bag_order,
    get_club_sort_key,
    get_smash_target,
    get_special_categories,
    get_uneekor_mapping,
    is_in_bag,
    reload,
)


class TestBagConfig(unittest.TestCase):
    """Verify bag config loads correctly."""

    def setUp(self):
        reload()

    def test_bag_order_returns_list(self):
        order = get_bag_order()
        self.assertIsInstance(order, list)
        self.assertEqual(len(order), 16)
        self.assertIn("Driver", order)
        self.assertIn("Putter", order)
        self.assertIn("3 Iron", order)
        self.assertNotIn("1 Iron", order)

    def test_club_sort_key_driver_first(self):
        self.assertEqual(get_club_sort_key("Driver"), 0)

    def test_is_in_bag_true(self):
        self.assertTrue(is_in_bag("Driver"))
        self.assertTrue(is_in_bag("7 Iron"))
        self.assertTrue(is_in_bag("3 Iron"))
        self.assertTrue(is_in_bag("Putter"))

    def test_is_in_bag_false(self):
        self.assertFalse(is_in_bag("1 Iron"))
        self.assertFalse(is_in_bag("Sim Round"))
        self.assertFalse(is_in_bag("Other"))
        self.assertFalse(is_in_bag("Nonexistent"))


class TestSmashTargets(unittest.TestCase):
    """Verify smash factor target accessors."""

    def setUp(self):
        reload()

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
        self.assertIn("3 Iron", targets)
        self.assertNotIn("Putter", targets)

    def test_all_bag_clubs_have_targets(self):
        order = get_bag_order()
        targets = get_all_smash_targets()
        for club in order:
            if club == "Putter":
                continue
            self.assertIn(club, targets, f"Missing smash target for {club}")


class TestUneekorMapping(unittest.TestCase):
    """Verify Uneekor code to canonical label mapping."""

    def setUp(self):
        reload()

    def test_get_uneekor_mapping_contains_clubs_and_special_categories(self):
        mapping = get_uneekor_mapping()
        self.assertIsInstance(mapping, dict)
        self.assertEqual(mapping.get("DRIVER"), "Driver")
        self.assertEqual(mapping.get("IRON3"), "3 Iron")
        self.assertEqual(mapping.get("IRON1"), "Sim Round")
        self.assertEqual(mapping.get("HYBRID1"), "Other")


class TestSpecialCategories(unittest.TestCase):
    """Verify special category accessors."""

    def setUp(self):
        reload()

    def test_get_special_categories_returns_expected_entries(self):
        categories = get_special_categories()
        self.assertIsInstance(categories, list)
        canonicals = {category.get("canonical") for category in categories}
        self.assertIn("Sim Round", canonicals)
        self.assertIn("Other", canonicals)


if __name__ == "__main__":
    unittest.main()
