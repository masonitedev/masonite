import importlib
import os

from masoniteorm.factories import Factory

from tests import TestCase
from tests.integrations.app.User import User
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
            self.assertIn(
                "from tests.integrations.app.FakeGenerated import FakeGenerated",
                content,
            )
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
            self.assertIn(
                "from tests.integrations.app.Article import Article", content
            )
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

    def test_generated_factory_can_make_and_create_real_records(self):
        """End-to-end: generate a factory, import it for real, and confirm it
        actually produces (and persists) model instances via masoniteorm's
        Factory engine -- not just that the file's text looks right."""
        init_file = factories_path("__init__.py")
        original_init = ""
        if os.path.exists(init_file):
            with open(init_file) as f:
                original_init = f.read()

        target = factories_path("UserFactory.py")
        created_id = None
        try:
            self.craft("factory", "User").assertSuccess()

            with open(target) as f:
                content = f.read()
            content = content.replace(
                "return {}",
                "return {\n"
                '            "name": faker.name(),\n'
                '            "email": faker.unique.email(),\n'
                '            "password": "secret",\n'
                "        }",
            )
            with open(target, "w") as f:
                f.write(content)

            module = importlib.import_module(
                "tests.integrations.databases.factories.UserFactory"
            )
            importlib.reload(module)
            module.UserFactory.register()

            made = Factory(User).make()
            self.assertIsInstance(made, User)
            self.assertTrue(made.name)
            # make() only builds the in-memory model, it never touches the
            # database, so no primary key has been assigned yet.
            self.assertNotIn("id", made.__attributes__)

            created = Factory(User).create()
            created_id = created.id
            self.assertIsNotNone(created.id)

            found = User.where("id", created.id).first()
            self.assertIsNotNone(found)
            self.assertEqual(found.email, created.email)
        finally:
            if created_id is not None:
                User.where("id", created_id).delete()
            self._cleanup(target, init_file, original_init)
