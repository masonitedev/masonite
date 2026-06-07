"""Bootstrap Preset"""
import shutil

from ..utils.location import resources_path
from ..utils.filesystem import make_full_directory
from .Preset import Preset


class Bootstrap(Preset):
    """
    Configure the front-end scaffolding for the application to use Bootstrap
    """

    key = "bootstrap"
    packages = {
        "bootstrap": "^5.3.0",
        "sass": "^1.80.0",
    }
    removed_packages = [
        "tailwindcss",
        "@tailwindcss/vite",
        "resolve-url-loader",
        "sass-loader",
        "laravel-mix",
    ]

    def install(self):
        """Install the preset"""
        self.update_packages(dev=True)
        self.update_vite_config()
        self.update_css()
        self.update_js()
        self.remove_node_modules()

    def update_css(self):
        """Create/Override an app.scss file configured for the preset."""
        make_full_directory(resources_path("css"))
        shutil.copyfile(
            self.get_template_path("_variables.scss"),
            resources_path("css/_variables.scss"),
        )
        shutil.copyfile(
            self.get_template_path("app.scss"), resources_path("css/app.scss")
        )
