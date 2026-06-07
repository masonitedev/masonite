"""Tailwind Preset"""
import os
import shutil

from ..utils.filesystem import make_full_directory
from ..utils.location import base_path, resources_path
from .Preset import Preset


class Tailwind(Preset):
    """
    Configure the front-end scaffolding for the application to use Tailwind
    """

    key = "tailwind"
    packages = {"tailwindcss": "^4.3.0", "@tailwindcss/vite": "^4.3.0"}
    removed_packages = ["postcss", "autoprefixer", "laravel-mix"]

    def install(self):
        """Install the preset"""
        self.update_packages(dev=True)
        self.update_vite_config()
        self.update_css()
        self.remove_legacy_config()
        self.remove_node_modules()

    def remove_legacy_config(self):
        """Tailwind 4 is configured in CSS: drop the v3 config file if present."""
        legacy_config = base_path("tailwind.config.js")
        if os.path.exists(legacy_config):
            os.remove(legacy_config)

    def update_css(self):
        """Create/Override an app.css file configured for the preset."""
        make_full_directory(resources_path("css"))
        shutil.copyfile(
            self.get_template_path("app.css"), resources_path("css/app.css")
        )
