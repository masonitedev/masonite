from unittest import TestCase

from src.masonite.configuration import deep_merge


class TestDeepMerge(TestCase):
    """Unit tests for the pure ``deep_merge`` helper used to stack configuration."""

    def test_merges_nested_dicts_with_override_winning_and_siblings_preserved(self):
        base = {"stores": {"redis": {"host": "127.0.0.1", "port": "6379"}}}
        override = {"stores": {"redis": {"port": 6380}}}
        self.assertEqual(
            deep_merge(base, override),
            {"stores": {"redis": {"host": "127.0.0.1", "port": 6380}}},
        )

    def test_disjoint_keys_are_unioned(self):
        self.assertEqual(deep_merge({"a": 1}, {"b": 2}), {"a": 1, "b": 2})

    def test_lists_are_replaced_not_appended(self):
        self.assertEqual(
            deep_merge({"items": [1, 2, 3]}, {"items": [9]}), {"items": [9]}
        )

    def test_scalar_override_wins(self):
        self.assertEqual(deep_merge({"a": 1}, {"a": 2}), {"a": 2})

    def test_type_mismatch_is_replaced_by_override(self):
        self.assertEqual(deep_merge({"a": {"x": 1}}, {"a": [1, 2]}), {"a": [1, 2]})
        self.assertEqual(deep_merge({"a": [1]}, {"a": {"x": 1}}), {"a": {"x": 1}})

    def test_inputs_are_not_mutated(self):
        base = {"a": {"x": 1}}
        override = {"a": {"y": 2}}
        deep_merge(base, override)
        self.assertEqual(base, {"a": {"x": 1}})
        self.assertEqual(override, {"a": {"y": 2}})

    def test_empty_override_keeps_base(self):
        self.assertEqual(deep_merge({"a": 1}, {}), {"a": 1})

    def test_empty_base_takes_override(self):
        self.assertEqual(deep_merge({}, {"a": 1}), {"a": 1})
