"""New Factory Command."""
import inflection
import os

from ..utils.filesystem import make_directory, render_stub_file, get_module_dir
from ..utils.location import factories_path, models_path
from .Command import Command


class MakeFactoryCommand(Command):
    """
    Creates a new model factory.

    factory
        {name : Name of the factory}
        {--m|model=? : The model this factory builds, defaults to the factory name}
        {--f|force=? : Force overriding file if already exists}
    """

    def __init__(self, application):
        super().__init__()
        self.app = application

    def handle(self):
        name = inflection.camelize(self.argument("name"))
        if not name.endswith("Factory"):
            name += "Factory"

        model = inflection.camelize(self.option("model") or name[: -len("Factory")])
        model_module = (
            models_path(model, absolute=False).replace("/", ".").replace("\\", ".")
        )

        content = render_stub_file(self.get_factories_path(), name)
        content = content.replace("__model_module__", model_module)
        content = content.replace("__model__", model)

        filename = f"{name}.py"
        filepath = factories_path(filename)
        make_directory(filepath)
        if os.path.exists(filepath) and not self.option("force"):
            self.warning(
                f"{filepath} already exists! Run the command with -f (force) to override."
            )
            return -1
        with open(filepath, "w") as f:
            f.write(content)

        # add class to __init__.py
        with open(os.path.join(os.path.dirname(filepath), "__init__.py"), "a") as f:
            f.write(f"from .{name} import {name}\n")

        self.info(f"Factory Created ({factories_path(filename, absolute=False)})")

    def get_factories_path(self):
        return os.path.join(get_module_dir(__file__), "../stubs/factories/Factory.py")
