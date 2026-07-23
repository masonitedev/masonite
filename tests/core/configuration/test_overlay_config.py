from tests import TestCase

from src.masonite.configuration import Configuration


class TestOverlayConfiguration(TestCase):
    """Stacked / overlay configuration loading.

    These tests reuse the shared application from ``wsgi`` (via Masonite's
    ``TestCase``) and only swap the bound ``config.location`` to point at isolated
    fixtures, restoring it after each test. A throwaway local ``Configuration`` is
    loaded and asserted on, so the globally bound ``config`` is never mutated.
    """

    FIXTURES = "tests/core/configuration/fixtures"

    def setUp(self):
        super().setUp()
        self._original_location = self.application.make("config.location")

    def tearDown(self):
        # always restore the real config location, even if an assertion failed
        self.application.bind("config.location", self._original_location)
        super().tearDown()

    def _load(self, base, overlays=None):
        self.application.bind("config.location", f"{self.FIXTURES}/{base}")
        configuration = Configuration(self.application)
        configuration.load(overlays)
        return configuration

    def test_explicit_overlay_overrides_only_targeted_keys(self):
        config = self._load("base", overlays=[f"{self.FIXTURES}/overlay"])
        # the targeted leaf is overridden...
        self.assertEqual(config.get("cache.stores.redis.port"), 6380)
        # ...while its siblings and untouched keys in the same module survive
        self.assertEqual(config.get("cache.stores.redis.host"), "127.0.0.1")
        self.assertEqual(config.get("cache.stores.default"), "local")
        self.assertEqual(config.get("cache.stores.local.driver"), "file")

    def test_partial_overlay_leaves_unmentioned_modules_intact(self):
        # the overlay never declares application.py, so it must be left as the base
        config = self._load("base", overlays=[f"{self.FIXTURES}/overlay"])
        self.assertEqual(config.get("application.key"), "base-key")

    def test_overlay_lists_are_replaced_not_appended(self):
        config = self._load("base", overlays=[f"{self.FIXTURES}/overlay"])
        self.assertEqual(config.get("sample_list.items"), [9])

    def test_environment_overlay_is_applied_automatically(self):
        # environment() is "testing" under pytest, and base_with_env ships an
        # environment/testing overlay, so load() with no explicit overlays applies it
        config = self._load("base_with_env")
        self.assertEqual(config.get("cache.stores.default"), "redis")
        # values outside the environment overlay are preserved
        self.assertEqual(config.get("cache.stores.local.driver"), "file")

    def test_missing_environment_overlay_is_a_no_op(self):
        # base has no environment/ folder, so a plain load() equals the base config
        config = self._load("base")
        self.assertEqual(config.get("cache.stores.default"), "local")
        self.assertEqual(config.get("sample_list.items"), [1, 2, 3])
        self.assertEqual(config.get("application.key"), "base-key")
