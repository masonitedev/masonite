import os

from ..facades import Loader
from ..utils.str import as_filepath
from ..utils.structures import data
from ..exceptions import InvalidConfigurationLocation, InvalidConfigurationSetup


def deep_merge(base, override):
    """Deep-merge ``override`` on top of ``base`` and return a new value.

    - dicts are merged recursively: ``override`` wins on conflicting keys while keys
      only present in ``base`` are preserved;
    - lists, scalars and mismatched types are replaced by ``override``.

    Neither argument is mutated (the returned value never aliases a mutated input),
    which matters because the loader reads the live stored dict before merging. The
    list branch is the extension point for any future append/prepend strategy.
    """
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, override_value in override.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], override_value)
            else:
                merged[key] = override_value
        return merged
    # lists, scalars and type mismatches: the overlay value replaces the base value.
    return override


class Configuration:
    # Foundation configuration keys
    reserved_keys = [
        "application",
        "auth",
        "broadcast",
        "cache",
        "database",
        "filesystem",
        "mail",
        "notification",
        "providers",
        "queue",
        "session",
    ]

    def __init__(self, application):
        self.application = application
        self._config = data()

    def load(self, overlays: "list[str] | None" = None):
        """At boot load configuration from all files and store them in here.

        Configuration can be "stacked": additional overlay locations are merged on
        top of the base location so an environment only has to declare the values it
        changes. Overlays are partial — they only need to contain the modules and
        keys they want to override. Dict values are deep-merged into the base while
        lists and scalars are replaced.

        The base location is loaded first, then each location in ``overlays`` in
        order, then — if it exists — the overlay for the current environment at
        ``{config.location}/environment/{APP_ENV}``. The environment overlay is
        applied automatically and is a no-op when that directory is absent, so
        existing applications are unaffected.
        """
        config_root = self.application.make("config.location")
        for module_name, module in Loader.get_modules(
            config_root, raise_exception=True
        ).items():
            params = Loader.get_parameters(module)
            for name, value in params.items():
                self._config[f"{module_name}.{name.lower()}"] = value

        # stack any explicitly requested overlay locations on top of the base.
        for overlay_location in overlays or []:
            self._apply_overlay(overlay_location)

        # automatically stack the overlay for the current environment when present.
        environment = self.application.environment()
        if environment:
            environment_overlay = f"{config_root}/environment/{environment}"
            if os.path.isdir(as_filepath(environment_overlay)):
                self._apply_overlay(environment_overlay)

        # check loaded configuration
        if not self._config.get("application"):
            raise InvalidConfigurationLocation(
                f"Config directory {config_root} does not contain required configuration files."
            )

    def _apply_overlay(self, location):
        """Deep-merge a single overlay location on top of the already loaded config.

        Modules absent from the overlay are left untouched; a module present in the
        overlay is merged into the matching base module (dict keys deep-merge, lists
        and scalars are replaced). A broken overlay module raises, exactly like the
        base load — overlays are trusted first-party configuration, so unlike
        ``merge_with`` they may override reserved keys such as 'application'.
        """
        for module_name, module in Loader.get_modules(
            location, raise_exception=True
        ).items():
            params = Loader.get_parameters(module)
            override = {name.lower(): value for name, value in params.items()}
            base = self._config.get(module_name) or {}
            self._config[module_name] = deep_merge(base, override)

    def merge_with(self, path, external_config):
        """Merge external config at key with project config at same key. It's especially
        useful in Masonite packages in order to merge the configuration default package with
        the package configuration which can be published in project.

        This functions disallow merging configuration using foundation configuration keys
        (such as 'application').
        """
        if path in self.reserved_keys:
            raise InvalidConfigurationSetup(
                f"{path} is a reserved configuration key name. Please use an other key."
            )
        if isinstance(external_config, str):
            # config is a path and should be loaded
            params = Loader.get_parameters(external_config)
        else:
            params = external_config
        base_config = {name.lower(): value for name, value in params.items()}
        merged_config = {**base_config, **self.get(path, {})}
        self.set(path, merged_config)

    def set(self, path, value):
        self._config[path] = value

    def has(self, path):
        return path in self._config

    def all(self):
        return self._config

    def get(self, path, default=None):
        try:
            config_at_path = self._config[path]
            if isinstance(config_at_path, dict):
                return data(config_at_path)
            else:
                return config_at_path
        except KeyError:
            return default
