"""Remove Preset"""
import os

from ..utils.location import base_path, resources_path
from .Preset import Preset


class Remove(Preset):
    """Removes any defined Preset"""

    key = "base"
    removed_packages = [
        "bootstrap",
        "resolve-url-loader",
        "sass",
        "sass-loader",
        "vue",
        "vue-loader",
        "@vitejs/plugin-vue",
        "react",
        "react-dom",
        "@babel/preset-react",
        "@vitejs/plugin-react",
        "tailwindcss",
        "@tailwindcss/vite",
        "autoprefixer",
        "postcss",
        "laravel-mix",
    ]

    def install(self):
        """Install the preset"""
        self.update_packages(dev=True)
        self.update_css()
        self.update_js()
        self.update_vite_config()
        self.remove_node_modules()
        self.remove_all_presets_file()

    def remove_all_presets_file(self):
        presets_resources_files = [
            "css/_variables.scss",
            "css/app.scss",
            "js/components/HelloWorld.vue",
            "js/components/Example.js",
            "js/components/Example.jsx",
            "js/App.vue",
        ]
        for f in presets_resources_files:
            filepath = resources_path(f)
            if os.path.exists(filepath):
                os.remove(filepath)

        for legacy_file in ("tailwind.config.js", "webpack.mix.js"):
            filepath = base_path(legacy_file)
            if os.path.exists(filepath):
                os.remove(filepath)
