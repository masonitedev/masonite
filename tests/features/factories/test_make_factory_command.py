import os

from tests import TestCase
from src.masonite.utils.location import factories_path


class TestMakeFactoryCommand(TestCase):
    def _cleanup(self, target, init_file, original_init):
        if os.path.exists(target):
            os.remove(target)
        with open(init_file, "w") as f:
            f.write(original_init)

    def test_command_creates_a_factory(self):
        init_file = factories_path("__init__.py")
        original_init = ""
        if os.path.exists(init_file):
            with open(init_file) as f:
                original_init = f.read()

        target = factories_path("FakeGeneratedFactory.py")
        try:
            self.craft("factory", "FakeGenerated")
            self.assertTrue(os.path.exists(target))
            with open(target) as f:
                content = f.read()
            self.assertIn("class FakeGeneratedFactory:", content)
            self.assertIn("from app.models.FakeGenerated import FakeGenerated", content)
            self.assertIn("Factory.register(FakeGenerated,", content)
        finally:
            self._cleanup(target, init_file, original_init)

    def test_model_option_overrides_inferred_model(self):
        init_file = factories_path("__init__.py")
        original_init = ""
        if os.path.exists(init_file):
            with open(init_file) as f:
                original_init = f.read()

        target = factories_path("PostFactory.py")
        try:
            self.craft("factory", "Post --model=Article")
            with open(target) as f:
                content = f.read()
            self.assertIn("from app.models.Article import Article", content)
            self.assertIn("Factory.register(Article,", content)
        finally:
            self._cleanup(target, init_file, original_init)

    def test_force_option_required_to_overwrite(self):
        init_file = factories_path("__init__.py")
        original_init = ""
        if os.path.exists(init_file):
            with open(init_file) as f:
                original_init = f.read()

        target = factories_path("FakeGeneratedFactory.py")
        try:
            self.craft("factory", "FakeGenerated")
            self.craft("factory", "FakeGenerated").assertOutputContains(
                "already exists"
            )
            self.craft("factory", "FakeGenerated --force").assertSuccess()
        finally:
            self._cleanup(target, init_file, original_init)
