"""React Preset"""
import shutil
import os

from .Preset import Preset
from ..utils.filesystem import make_directory
from ..utils.location import resources_path, views_path


class React(Preset):
    """
    Configure the front-end scaffolding for the application to use ReactJS

    Will also remove Vue as Vue and React are a bit mutally exclusive
    """

    key = "react"
    packages = {
        "react": "^19.0.0",
        "react-dom": "^19.0.0",
        "@vitejs/plugin-react": "^5.0.0",
    }
    removed_packages = ["vue", "vue-loader", "@vitejs/plugin-vue", "@babel/preset-react"]

    def install(self):
        """Install the preset"""
        self.update_packages(dev=True)
        self.update_vite_config()
        self.update_js()
        self.add_components()
        self.update_css()
        self.create_view()
        self.remove_node_modules()

    def add_components(self):
        """Copy example React component into application (delete example Vue component
        if it exists)"""
        # make components directory if does not exists
        make_directory(resources_path("js/components/Example.jsx"))

        # delete Vue components and the legacy React component if they exist
        old_files = [
            resources_path("js/components/HelloWorld.vue"),
            resources_path("js/App.vue"),
            resources_path("js/components/Example.js"),
        ]
        for old_file in old_files:
            if os.path.exists(old_file):
                os.remove(old_file)

        # add React component
        shutil.copyfile(
            self.get_template_path("Example.jsx"),
            resources_path("js/components/Example.jsx"),
        )

    def create_view(self):
        """Copy an example app view with assets included."""
        shutil.copyfile(
            self.get_template_path("app.html"), views_path("app_react.html")
        )
