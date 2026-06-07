"""New Project Command."""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from io import BytesIO

import requests
from cryptography.fernet import Fernet

from ..exceptions import (
    ProjectLimitReached,
    ProjectProviderHttpError,
    ProjectProviderTimeout,
    ProjectTargetNotEmpty,
)
from ..utils.console import MUTED, VIOLET, VIOLET_DEEP, VIOLET_LIT, paint, supports_ansi
from ..utils.filesystem import get_module_dir, render_stub_file
from ..utils.str import random_string
from .Command import Command


class WizardCancelled(Exception):
    """Raised when the user cancels the wizard (Ctrl+C on a prompt)."""


class DownloadProjectMixin:
    """Legacy flow used to craft a project from a custom GitHub/GitLab repository
    when the --repo option is given. The default flow uses the skeleton bundled
    with the framework instead (no network required)."""

    providers = ["github", "gitlab"]
    # timeout in seconds for requests made to providers
    TIMEOUT = 20

    def _download_flow(self, target, to_dir):
        branch = self.option("branch")
        version = self.option("release")
        repo = self.option("repo")
        provider = self.option("provider")

        try:
            if repo and provider not in self.providers:
                return self.error(
                    "'provider' option must be in {}".format(",".join(self.providers))
                )

            self.set_api_provider_url_for_repo(provider, repo)

            if branch != "False":
                branch_data = self.get_branch_provider_data(provider, branch)
                if "name" not in branch_data:
                    return self.error("Branch {0} does not exist.".format(branch))

                zipball = self.get_branch_archive_url(provider, repo, branch)
            elif version != "False":
                releases_data = self.get_releases_provider_data(provider)
                zipball = False
                for release in releases_data:
                    if "tag_name" in release and release["tag_name"].startswith(
                        "v{0}".format(version)
                    ):
                        self.info("Installing version {0}".format(release["tag_name"]))
                        self.line("")
                        zipball = self.get_release_archive_url_from_release_data(
                            provider, release
                        )
                        break
                if zipball is False:
                    return self.error("Version {0} could not be found".format(version))
            else:
                tags_data = self.get_releases_provider_data(provider)

                # try to find all releases which are not prereleases
                tags = []
                for release in tags_data:
                    if release["prerelease"] is False:
                        tag_key = "tag_name" if provider == "github" else "name"
                        tags.append(release[tag_key].replace("v", ""))

                tags = sorted(
                    tags, key=lambda v: [int(i) for i in v.split(".")], reverse=True
                )
                # get url from latest tagged version
                if not tags:
                    self.comment(
                        "No tags has been found, using latest commit on master."
                    )
                    zipball = self.get_branch_archive_url(provider, repo, "master")
                else:
                    zipball = self.get_tag_archive_url(provider, repo, tags[0])
        except ProjectLimitReached:
            raise ProjectLimitReached(
                "You have reached your hourly limit of creating new projects with {0}. Try again in 1 hour.".format(
                    provider
                )
            )
        except requests.Timeout:
            raise ProjectProviderTimeout(
                "{0} provider is not reachable, request timed out after {1} seconds".format(
                    provider, self.TIMEOUT
                )
            )
        except Exception as e:
            self.error(
                "The following error happened when crafting your project. Verify options are correct else open an issue at https://github.com/masonitedev/masonite."
            )
            raise e

        success = False

        zipurl = zipball

        self.info("Crafting Application ...")

        # create a tmp directory to extract project template
        tmp_dir = tempfile.TemporaryDirectory()
        try:
            request = requests.get(zipurl)
            with zipfile.ZipFile(BytesIO(request.content)) as zfile:
                zfile.extractall(tmp_dir.name)
                extracted_path = os.path.join(
                    tmp_dir.name, zfile.infolist()[0].filename
                )
            success = True
        except Exception as e:
            self.error("An error occured when downloading {0}".format(zipurl))
            raise e

        if success:
            if target == ".":
                shutil.move(extracted_path, os.getcwd())
            else:
                shutil.move(extracted_path, to_dir)

            # remove tmp directory
            tmp_dir.cleanup()

            if target == ".":
                from_dir = os.path.join(os.getcwd(), zfile.infolist()[0].filename)

                for file in os.listdir(zfile.infolist()[0].filename):
                    shutil.move(os.path.join(from_dir, file), os.getcwd())
                os.rmdir(from_dir)

            self.info("Application Created Successfully!")
            if target == ".":
                self.info("Installing Dependencies...")
                self.call("install")
                self.info(
                    "Installed Successfully. Just Run `python craft serve` To Start Your Application."
                )
            else:
                self.info(
                    f"You now will have to go into your new {target} directory and run `project install` to complete the installation"
                )

            return

        else:
            self.comment("Could Not Create Application :(")

    def set_api_provider_url_for_repo(self, provider, repo):
        if provider == "github":
            self.api_base_url = "https://api.github.com/repos/{0}".format(repo)
        elif provider == "gitlab":
            import urllib.parse

            repo_encoded_url = urllib.parse.quote(repo, safe="")
            self.api_base_url = "https://gitlab.com/api/v4/projects/{0}".format(
                repo_encoded_url
            )

    def get_branch_provider_data(self, provider, branch):
        if provider == "github":
            branch_data = self._get(
                "{0}/branches/{1}".format(self.api_base_url, branch)
            )
        elif provider == "gitlab":
            branch_data = self._get(
                "{0}/repository/branches/{1}".format(self.api_base_url, branch)
            )
        return branch_data.json()

    def get_branch_archive_url(self, provider, repo, branch):
        if provider == "github":
            return "https://github.com/{0}/archive/{1}.zip".format(repo, branch)
        elif provider == "gitlab":
            # here we can provide commit, branch name or tag
            return "{0}/repository/archive.zip?sha={1}".format(
                self.api_base_url, branch
            )

    def get_tag_archive_url(self, provider, repo, version):
        if provider == "github":
            tag_data = self._get(
                "{0}/releases/tags/v{1}".format(self.api_base_url, version)
            )
            return tag_data.json()["zipball_url"]
        elif provider == "gitlab":
            return self.get_branch_archive_url("gitlab", repo, "v" + version)

    def get_releases_provider_data(self, provider):
        if provider == "github":
            releases_data = self._get("{0}/releases".format(self.api_base_url))
        elif provider == "gitlab":
            releases_data = self._get("{0}/releases".format(self.api_base_url))
        return releases_data.json()

    def get_release_archive_url_from_release_data(self, provider, release):
        if provider == "github":
            return release["zipball_url"]
        elif provider == "gitlab":
            return [x for x in release["assets"]["sources"] if x["format"] == "zip"][0][
                "url"
            ]

    def get_tags_provider_data(self, provider):
        if provider == "github":
            releases_data = self._get("{0}/releases".format(self.api_base_url))
        elif provider == "gitlab":
            releases_data = self._get("{0}/repository/tags".format(self.api_base_url))
        return releases_data.json()

    def _get(self, request):
        data = requests.get(request, timeout=self.TIMEOUT)
        if data.status_code != 200:
            if data.reason == "rate limit exceeded":
                raise ProjectLimitReached()
            else:
                raise ProjectProviderHttpError(
                    "{0}({1}) at {2}".format(data.reason, data.status_code, data.url)
                )
        return data


class NewCommand(DownloadProjectMixin, Command):
    """
    Creates a new Masonite project

    new
        {target? : Path of your Masonite project}
        {--api : Scaffold an API-ready project}
        {--preset= : Frontend preset to use (tailwind, bootstrap, vue, react, none)}
        {--db= : Database driver to configure (sqlite, mysql, postgres)}
        {--no-venv : Do not create a virtual environment or install dependencies}
        {--no-git : Do not initialize a git repository}
        {--no-serve : Do not offer to start the development server}
        {--no-input : Do not ask any interactive question and use defaults}
        {--f|--force : Craft the project even if the target directory is not empty}
        {--repo= : Craft the project from a custom repository instead of the bundled skeleton}
        {--b|--branch=False : Specify which branch you would like to install when using --repo}
        {--r|--release=False : Specify which version you would like to install when using --repo}
        {--p|--provider=github : Repository provider to use with --repo (github, gitlab)}
    """

    PRESETS = ["tailwind", "bootstrap", "vue", "react", "none"]
    DATABASES = ["sqlite", "mysql", "postgres"]
    DB_DRIVER_PACKAGES = {"mysql": "pymysql", "postgres": "psycopg2-binary"}

    _interactive = False

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.api_base_url = None

    def handle(self):
        self._interactive = (
            self.io.is_interactive()
            and sys.stdin.isatty()
            and not self.option("no-input")
        )
        interactive = self._interactive

        try:
            return self._craft(interactive)
        except WizardCancelled:
            self.line("")
            self.comment("Cancelled. No project was created.")
            return 1

    def _craft(self, interactive):
        if interactive:
            self._banner()

        # resolve the target directory
        target = self.argument("target")
        if not target and interactive:
            target = self._prompt_text("What is the name of your project?", "my-app")
        target = (target or ".").strip()

        if target == ".":
            to_dir = os.path.abspath(os.path.expanduser(target))
        else:
            to_dir = os.path.join(os.getcwd(), target)

        try:
            self.check_target_does_not_exist(to_dir)
        except ProjectTargetNotEmpty as e:
            self.error(str(e))
            return 1

        # a custom repository was requested: use the legacy download flow
        if self.option("repo"):
            return self._download_flow(target, to_dir)

        project_name = os.path.basename(to_dir.rstrip(os.sep)) or "masonite"

        # gather the wizard choices
        api = self._resolve_stack(interactive)
        preset = self._resolve_preset(interactive, api)
        database = self._resolve_database(interactive)
        with_venv = self._resolve_bool(
            interactive,
            "no-venv",
            "Create a virtual environment and install dependencies?",
            True,
        )
        with_git = self._resolve_bool(
            interactive, "no-git", "Initialize a git repository?", True
        )

        self.line("")
        self._title(f"Crafting your application in {target}")
        self.line("")

        self._copy_skeleton(target, to_dir)
        self._done("Application files created")

        self._patch_requirements(to_dir, database)
        self._create_env(to_dir, project_name, database)
        self._done(f"Environment file created (.env, {database})")

        self._generate_key(to_dir)
        self._done("Application key set")

        if api:
            self._enable_api(to_dir)
            self._done("API scaffolding enabled (config/api.py)")

        venv_python = None
        if with_venv:
            self._working(
                "Creating .venv and installing dependencies (this may take a minute)"
            )
            venv_python = self._create_venv_and_install(to_dir)
            if venv_python:
                self._done("Dependencies installed (.venv)")

        if not api and preset not in ("tailwind", "none"):
            self._apply_preset(to_dir, preset, venv_python)
        elif preset == "none":
            self._remove_frontend(to_dir)
            self._done("Frontend scaffolding removed")

        if with_git:
            self._git_init(to_dir)

        self._print_next_steps(target, with_venv)

        if interactive and not self.option("no-serve"):
            if self._prompt_confirm("Start the development server now?", True):
                self._serve(to_dir, venv_python)

    def check_target_does_not_exist(self, target):
        """To avoid overwriting the target directory and to avoid raw errors
        check that the target directory does not exist or is empty."""
        if self.option("force"):
            return False

        if target == os.getcwd():
            if os.listdir(target):
                raise ProjectTargetNotEmpty(
                    "The current directory is not empty. You must craft a project in an empty directory."
                )
            return False

        if os.path.isdir(target):
            raise ProjectTargetNotEmpty(
                "{} already exists. You must craft a project in a new directory.".format(
                    target
                )
            )

    # wizard UI
    def _banner(self):
        from .. import __version__

        pyramid = []
        for row in range(3):
            pad = " " * (4 - row)
            left = "▟" + "█" * row
            right = "█" * row + "▙"
            visible = len(pad) + len(left) + len(right)
            pyramid.append(
                pad
                + paint(left, VIOLET_LIT)
                + paint(right, VIOLET_DEEP)
                + " " * (12 - visible)
            )

        print()
        print(pyramid[0])
        print(
            pyramid[1]
            + paint("Masonite", VIOLET, bold=True)
            + paint(f"  v{__version__}", MUTED)
        )
        print(pyramid[2] + paint("The modern Python web framework", MUTED))
        print()

    def _title(self, message):
        if self._interactive and supports_ansi():
            print(paint(f"  {message}", bold=True))
        else:
            self.info(message)

    def _done(self, message):
        if self._interactive and supports_ansi():
            print(f"  {paint('✓', VIOLET, bold=True)} {message}")
        else:
            self.line(f"  ✓ {message}")

    def _working(self, message):
        if self._interactive and supports_ansi():
            print(paint(f"  … {message}", MUTED))
        else:
            self.line(f"  … {message}")

    # wizard prompts (questionary with arrow keys, cleo as fallback)
    def _questionary(self):
        try:
            import questionary

            return questionary
        except ImportError:  # pragma: no cover
            return None

    def _prompt_style(self, questionary):
        return questionary.Style(
            [
                ("qmark", "fg:#6d4fe3 bold"),
                ("question", "bold"),
                ("answer", "fg:#9c82f2 bold"),
                ("pointer", "fg:#6d4fe3 bold"),
                ("highlighted", "fg:#6d4fe3 bold"),
                ("selected", "fg:#6d4fe3"),
                ("instruction", "fg:#5e626a"),
            ]
        )

    def _prompt_text(self, message, default):
        questionary = self._questionary()
        if questionary is None:  # pragma: no cover
            return self.ask(message, default)
        answer = questionary.text(
            message,
            qmark="▲",
            instruction=f"({default}) ",
            style=self._prompt_style(questionary),
        ).ask()
        if answer is None:
            raise WizardCancelled()
        return answer.strip() or default

    def _prompt_select(self, message, options):
        """Display an arrow-key list. `options` is a list of (label, value)."""
        questionary = self._questionary()
        if questionary is None:  # pragma: no cover
            labels = [label for label, _ in options]
            answer = self.choice(message, labels, 0)
            return dict(options).get(answer, options[0][1])
        answer = questionary.select(
            message,
            choices=[
                questionary.Choice(label, value=value) for label, value in options
            ],
            qmark="▲",
            pointer="❯",
            style=self._prompt_style(questionary),
        ).ask()
        if answer is None:
            raise WizardCancelled()
        return answer

    def _prompt_confirm(self, message, default=True):
        questionary = self._questionary()
        if questionary is None:  # pragma: no cover
            return self.confirm(message, default)
        answer = questionary.confirm(
            message, default=default, qmark="▲", style=self._prompt_style(questionary)
        ).ask()
        if answer is None:
            raise WizardCancelled()
        return answer

    # wizard questions
    def _resolve_stack(self, interactive):
        if self.option("api"):
            return True
        if not interactive:
            return False
        return self._prompt_select(
            "Which application stack do you want?",
            [
                ("Full-stack — server rendered views with Jinja2", False),
                ("API only — JSON endpoints with JWT authentication", True),
            ],
        )

    def _resolve_preset(self, interactive, api):
        if api:
            return "none"
        preset = (self.option("preset") or "").lower()
        if preset in self.PRESETS:
            return preset
        if not interactive:
            return "tailwind"
        return self._prompt_select(
            "Which frontend preset do you want?",
            [
                ("Tailwind CSS (default)", "tailwind"),
                ("Bootstrap", "bootstrap"),
                ("Vue 3", "vue"),
                ("React", "react"),
                ("None — skip the frontend scaffolding", "none"),
            ],
        )

    def _resolve_database(self, interactive):
        database = (self.option("db") or "").lower()
        if database in self.DATABASES:
            return database
        if not interactive:
            return "sqlite"
        return self._prompt_select(
            "Which database will your application use?",
            [
                ("SQLite (default — zero configuration)", "sqlite"),
                ("MySQL", "mysql"),
                ("Postgres", "postgres"),
            ],
        )

    def _resolve_bool(self, interactive, negative_flag, question, default):
        if self.option(negative_flag):
            return False
        if not interactive:
            return default
        return self._prompt_confirm(question, default)

    # crafting steps
    def _skeleton_directory(self):
        return os.path.join(get_module_dir(__file__), "..", "skeleton")

    def _copy_skeleton(self, target, to_dir):
        skeleton = self._skeleton_directory()
        force = bool(self.option("force"))
        # the installed skeleton .py files may have been byte-compiled by pip
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc")

        if target == ".":
            for entry in os.listdir(skeleton):
                if entry == "__pycache__":
                    continue
                source = os.path.join(skeleton, entry)
                destination = os.path.join(to_dir, entry)
                if os.path.isdir(source):
                    shutil.copytree(
                        source, destination, dirs_exist_ok=force, ignore=ignore
                    )
                else:
                    shutil.copy2(source, destination)
        else:
            shutil.copytree(skeleton, to_dir, dirs_exist_ok=force, ignore=ignore)

        # ensure the craft entry point is executable
        craft_path = os.path.join(to_dir, "craft")
        if os.path.isfile(craft_path):
            os.chmod(craft_path, 0o755)

    def _patch_requirements(self, to_dir, database):
        driver_package = self.DB_DRIVER_PACKAGES.get(database)
        if not driver_package:
            return
        requirements_path = os.path.join(to_dir, "requirements.txt")
        with open(requirements_path, "a") as f:
            f.write(f"{driver_package}\n")

    def _create_env(self, to_dir, project_name, database):
        env_example = os.path.join(to_dir, ".env-example")
        env_path = os.path.join(to_dir, ".env")
        if not os.path.isfile(env_path):
            shutil.copy(env_example, env_path)

        self._set_env(to_dir, "APP_NAME", project_name)
        self._set_env(to_dir, "DB_CONNECTION", database)
        if database == "postgres":
            self._set_env(to_dir, "DB_PORT", "5432")
            self._set_env(to_dir, "DB_USERNAME", "postgres")

    def _generate_key(self, to_dir):
        key = Fernet.generate_key().decode("utf-8")
        self._set_env(to_dir, "APP_KEY", key)

    def _set_env(self, to_dir, key, value):
        """Set (or uncomment and set) an environment variable in the project
        .env file, appending it if it does not exist yet."""
        env_path = os.path.join(to_dir, ".env")
        with open(env_path) as f:
            lines = f.readlines()

        replaced = False
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f"# {key}="):
                lines[index] = f"{key}={value}\n"
                replaced = True
                break

        if not replaced:
            lines.append(f"{key}={value}\n")

        with open(env_path, "w") as f:
            f.writelines(lines)

    def _enable_api(self, to_dir):
        # publish the api configuration from the framework stub
        stub_path = os.path.join(
            get_module_dir(__file__), "..", "api", "stubs", "api.py"
        )
        content = render_stub_file(stub_path, "api")
        with open(os.path.join(to_dir, "config", "api.py"), "w") as f:
            f.write(content)

        # enable the ApiProvider in config/providers.py
        providers_path = os.path.join(to_dir, "config", "providers.py")
        with open(providers_path) as f:
            content = f.read()
        content = content.replace(
            "# from masonite.api.providers import ApiProvider",
            "from masonite.api.providers import ApiProvider",
        )
        content = content.replace("    # ApiProvider,", "    ApiProvider,")
        with open(providers_path, "w") as f:
            f.write(content)

        self._set_env(to_dir, "JWT_SECRET", random_string(25))

    def _venv_python(self, to_dir):
        if os.name == "nt":
            return os.path.join(to_dir, ".venv", "Scripts", "python.exe")
        return os.path.join(to_dir, ".venv", "bin", "python")

    def _create_venv_and_install(self, to_dir):
        result = subprocess.run([sys.executable, "-m", "venv", ".venv"], cwd=to_dir)
        if result.returncode != 0:
            self.error(
                "Could not create a virtual environment. "
                "Create one manually and run: pip install -r requirements.txt"
            )
            return None

        venv_python = self._venv_python(to_dir)
        result = subprocess.run(
            [
                venv_python,
                "-m",
                "pip",
                "install",
                "-q",
                "--disable-pip-version-check",
                "-r",
                "requirements.txt",
            ],
            cwd=to_dir,
        )
        if result.returncode != 0:
            self.error(
                "Dependency installation failed. The project was created: "
                "activate the virtual environment and run `pip install -r requirements.txt` manually."
            )
            return None
        return venv_python

    def _apply_preset(self, to_dir, preset, venv_python):
        if venv_python and os.path.exists(venv_python):
            self._working(f"Scaffolding the {preset} frontend preset")
            subprocess.run(
                [venv_python, "craft", "preset", preset], cwd=to_dir, check=False
            )
            self._done(f"{preset} frontend preset scaffolded")
        else:
            self.comment(
                f"Run `python craft preset {preset}` inside your project after installing "
                "the dependencies to scaffold the frontend preset."
            )

    def _remove_frontend(self, to_dir):
        for file in (
            "package.json",
            "vite.config.js",
            "webpack.mix.js",
            "tailwind.config.js",
        ):
            path = os.path.join(to_dir, file)
            if os.path.isfile(path):
                os.remove(path)
        shutil.rmtree(os.path.join(to_dir, "resources"), ignore_errors=True)

    def _git_init(self, to_dir):
        if shutil.which("git") is None:
            self.comment(
                "git was not found on your PATH: skipping repository initialization."
            )
            return

        result = subprocess.run(
            ["git", "init", "-q", "-b", "main"], cwd=to_dir, capture_output=True
        )
        if result.returncode != 0:
            # older git versions do not support the -b option
            result = subprocess.run(
                ["git", "init", "-q"], cwd=to_dir, capture_output=True
            )
        if result.returncode != 0:
            self.comment("Could not initialize a git repository.")
            return

        subprocess.run(["git", "add", "-A"], cwd=to_dir, capture_output=True)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "Initial commit"],
            cwd=to_dir,
            capture_output=True,
        )
        if commit.returncode != 0:
            self.comment(
                "Repository created but the initial commit failed: "
                "configure git user.name/user.email and commit manually."
            )
            return
        self._done("Git repository initialized")

    def _print_next_steps(self, target, with_venv):
        commands = []
        if target != ".":
            commands.append(f"cd {target}")
        if with_venv:
            commands.append(
                ".venv\\Scripts\\activate"
                if os.name == "nt"
                else "source .venv/bin/activate"
            )
        commands.append("python craft migrate")
        commands.append("python craft serve")
        docs = "Documentation: https://docs.masonite.dev"

        fancy = (
            self._interactive
            and supports_ansi()
            and "utf" in (sys.stdout.encoding or "").lower()
        )
        if not fancy:
            self.line("")
            self.info("Your Masonite application is ready! Next steps:")
            self.line("")
            for command in commands:
                self.line(f"    {command}")
            self.line("")
            self.line(docs)
            self.line("")
            return

        title = "Your application is ready!  Next steps:"
        lines = [title, ""] + commands + ["", docs]
        width = max(len(line) for line in lines) + 4

        print()
        print("  " + paint("╭" + "─" * width + "╮", VIOLET))
        for index, line in enumerate(lines):
            body = line.ljust(width - 4)
            if index == 0:
                body = paint(body, bold=True)
            elif line == docs:
                body = paint(body, MUTED)
            elif line:
                body = paint(body, VIOLET_LIT)
            print("  " + paint("│", VIOLET) + "  " + body + "  " + paint("│", VIOLET))
        print("  " + paint("╰" + "─" * width + "╯", VIOLET))
        print()

    def _serve(self, to_dir, venv_python):
        executable = (
            venv_python
            if venv_python and os.path.exists(venv_python)
            else sys.executable
        )
        self.line("")
        if self._interactive and supports_ansi():
            print(
                f"  {paint('➜', VIOLET, bold=True)} Server running at "
                + paint("http://127.0.0.1:8000", VIOLET_LIT, bold=True)
                + paint("  (Ctrl+C to stop)", MUTED)
            )
        else:
            self.info(
                "Starting the development server at http://127.0.0.1:8000 (Ctrl+C to stop)"
            )
        self.line("")
        try:
            subprocess.run([executable, "craft", "serve"], cwd=to_dir)
        except KeyboardInterrupt:
            self.line("")
