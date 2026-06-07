import os
import shutil
import tempfile

from cleo import Application as CommandApplication

from src.masonite.commands import CommandCapsule
from src.masonite.commands.NewCommand import NewCommand
from src.masonite.commands.ProjectCommand import ProjectCommand
from tests import TestCase

NO_WIZARD = "--no-input --no-venv --no-git --no-serve"


class TestNewCommand(TestCase):
    def setUp(self):
        super().setUp()
        self.original_commands = self.application.make("commands")
        command_app = CommandCapsule(CommandApplication("Masonite Version:", "tests"))
        self.application.bind("commands", command_app)
        self.application.make("commands").add(NewCommand())
        self.application.make("commands").add(ProjectCommand())
        self.directory = tempfile.mkdtemp()
        self.cwd = os.getcwd()

    def tearDown(self):
        super().tearDown()
        os.chdir(self.cwd)
        self.application.bind("commands", self.original_commands)
        shutil.rmtree(self.directory, ignore_errors=True)

    def project_path(self, name="project"):
        return os.path.join(self.directory, name)

    def read(self, project, file):
        with open(os.path.join(project, file)) as f:
            return f.read()

    def test_creates_skeleton_files(self):
        project = self.project_path()
        self.craft("new", f"{project} {NO_WIZARD}").assertSuccess()
        for file in [
            "wsgi.py",
            "craft",
            ".env",
            ".env-example",
            ".env.testing",
            ".gitignore",
            "requirements.txt",
            "app/Kernel.py",
            "app/controllers/WelcomeController.py",
            "app/models/User.py",
            "config/providers.py",
            "config/logging.py",
            "routes/web.py",
            "routes/api.py",
            "templates/welcome.html",
            "templates/errors/404.html",
            "storage/public/favicon.ico",
            "databases/migrations/2021_01_09_043202_create_users_table.py",
        ]:
            assert os.path.isfile(os.path.join(project, file)), f"missing {file}"

    def test_requirements_pin_masonite_5(self):
        project = self.project_path()
        self.craft("new", f"{project} {NO_WIZARD}").assertSuccess()
        requirements = self.read(project, "requirements.txt")
        assert "masonite-framework>=5.0,<6" in requirements
        assert "masonite-framework-orm>=3.0,<4" in requirements

    def test_app_key_and_name_are_set(self):
        project = self.project_path("my-blog")
        self.craft("new", f"{project} {NO_WIZARD}").assertSuccess()
        env = self.read(project, ".env")
        assert "APP_NAME=my-blog" in env
        key_line = [line for line in env.splitlines() if line.startswith("APP_KEY=")][0]
        # a Fernet key is a 44 characters url-safe base64 string
        assert len(key_line.replace("APP_KEY=", "")) == 44

    def test_database_option_patches_env_and_requirements(self):
        project = self.project_path()
        self.craft("new", f"{project} --db=postgres {NO_WIZARD}").assertSuccess()
        env = self.read(project, ".env")
        assert "DB_CONNECTION=postgres" in env
        assert "DB_PORT=5432" in env
        assert "psycopg2-binary" in self.read(project, "requirements.txt")

    def test_api_mode(self):
        project = self.project_path()
        self.craft("new", f"{project} --api {NO_WIZARD}").assertSuccess()
        assert os.path.isfile(os.path.join(project, "config", "api.py"))
        assert "JWT_SECRET=" in self.read(project, ".env")
        providers = self.read(project, "config/providers.py")
        assert "# ApiProvider," not in providers
        assert "    ApiProvider," in providers
        # api projects do not need the frontend scaffolding
        assert not os.path.isfile(os.path.join(project, "package.json"))

    def test_preset_none_removes_frontend(self):
        project = self.project_path()
        self.craft("new", f"{project} --preset=none {NO_WIZARD}").assertSuccess()
        assert not os.path.isfile(os.path.join(project, "package.json"))
        assert not os.path.isfile(os.path.join(project, "vite.config.js"))
        assert not os.path.isdir(os.path.join(project, "resources"))

    def test_default_preset_is_tailwind(self):
        project = self.project_path()
        self.craft("new", f"{project} {NO_WIZARD}").assertSuccess()
        assert os.path.isfile(os.path.join(project, "vite.config.js"))
        assert '@import "tailwindcss"' in self.read(project, "resources/css/app.css")

    def test_craft_into_current_directory(self):
        os.chdir(self.directory)
        self.craft("new", f". {NO_WIZARD}").assertSuccess()
        assert os.path.isfile(os.path.join(self.directory, "wsgi.py"))
        env = self.read(self.directory, ".env")
        assert f"APP_NAME={os.path.basename(self.directory)}" in env

    def test_existing_directory_errors(self):
        project = self.project_path()
        os.makedirs(project)
        with open(os.path.join(project, "somefile.txt"), "w") as f:
            f.write("not empty")
        self.craft("new", f"{project} {NO_WIZARD}").assertOutputContains(
            "already exists"
        )
        assert not os.path.isfile(os.path.join(project, "wsgi.py"))

    def test_start_alias_behaves_like_new(self):
        project = self.project_path()
        self.craft("start", f"{project} {NO_WIZARD}").assertSuccess()
        assert os.path.isfile(os.path.join(project, "wsgi.py"))
        assert os.path.isfile(os.path.join(project, "templates", "welcome.html"))

    def test_no_pycache_is_copied(self):
        # pip byte-compiles the installed skeleton: __pycache__ folders must
        # never end up in a freshly crafted project
        import src.masonite.commands.NewCommand as new_command_module

        skeleton = os.path.join(
            os.path.dirname(new_command_module.__file__), "..", "skeleton"
        )
        os.makedirs(os.path.join(skeleton, "config", "__pycache__"), exist_ok=True)
        try:
            project = self.project_path()
            self.craft("new", f"{project} {NO_WIZARD}").assertSuccess()
            for root, dirs, _ in os.walk(project):
                assert "__pycache__" not in dirs, f"__pycache__ found in {root}"
        finally:
            shutil.rmtree(
                os.path.join(skeleton, "config", "__pycache__"), ignore_errors=True
            )

    def test_welcome_template_links_to_new_docs(self):
        project = self.project_path()
        self.craft("new", f"{project} {NO_WIZARD}").assertSuccess()
        welcome = self.read(project, "templates/welcome.html")
        assert "https://docs.masonite.dev" in welcome
        assert "https://github.com/masonitedev/masonite" in welcome
