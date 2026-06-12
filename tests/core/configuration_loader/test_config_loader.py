import unittest

from src.masonite.configuration import Configuration
from src.masonite.foundation.Application import Application
from src.masonite.utils.location import base_path
from src.masonite.foundation.CoreKernel import CoreKernel

class TestConfigLoader(unittest.TestCase):

    def setUp(self):
        custom_application = Application(base_path("tests/integrations"), False)
        custom_application.register_providers(CoreKernel)
        self.application = custom_application

    def tearDown(self):
        self.application = None  # already done — good

    def test_load_ignores_config_subfolders(self):
        self.application.bind("config.location", "tests/integrations/config")
        configuration = Configuration(self.application)
        configuration.load()

        self.assertEqual(len(configuration._config.keys()), 17)

    def test_can_merge_configs_from_other_paths(self):
        config_root = "tests/integrations/config"
        self.application.bind("config.location", f"{config_root}")
        configuration = Configuration(self.application)
        configuration.load([
            "tests.integrations.config.base",
            "tests.integrations.config.environment.prod",
            f"{config_root}/deployed",
        ])

        self.assertEqual(len(configuration._config.keys()), 18)
        config = configuration.all()
        self.assertEqual(config["database"]["databases"]["default"], "postgres")
        self.assertEqual(config["database"]["databases"]["postgres"]["driver"], "postgres")
        self.assertEqual(config["database"]["databases"]["postgres"]["password"], "deployed_password")
        self.assertEqual(config["cache"]["stores"]["redis"]["host"], "deployed.host.org")
        self.assertEqual(config["external"]["services"]["stripe"]["api_key"], "not set")
