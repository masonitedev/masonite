from ..facades import Loader
from ..utils.structures import data
from ..exceptions import InvalidConfigurationLocation, InvalidConfigurationSetup


def _deep_merge(base, override):
    """
    Recursively merge override into base, preserving the base type.

    - dicts: recursively merge matching keys; override wins on conflicts
    - lists: concatenate with override preference deduplication —
             base entries already present in override are dropped,
             then override is appended in full
    - scalars: override wins

    Arguments:
        base -- the existing value to merge into
        override -- the incoming value to merge from

    Returns:
        merged value of the same type as base, or override if types differ
    """
    if isinstance(base, list) and isinstance(override, list):
        return [v for v in base if v not in override] + override
    if isinstance(base, dict) and isinstance(override, dict):
        result = dict(base)
        for key, override_value in override.items():
            base_value = result.get(key)
            result[key] = _deep_merge(base_value, override_value) if base_value is not None else override_value
        return result
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

    def load(self, other_paths: list[str] = None):
        """
        Load configuration from files, deep-merging each location into the
        accumulated config in order. The base location is loaded first,
        followed by each additional location in the order provided.

        Overlay locations are partial by design — they only need to contain
        the modules they wish to add or override. Missing modules in an
        overlay are silently skipped. New modules introduced by an overlay
        are added to the config as-is.

        Arguments:
            other_paths {list[str]|None} -- explicit overlay locations to load after the base;
                                          each is a dot-separated module path (e.g. "environment.prod")

        Raises:
            InvalidConfigurationLocation -- if no application config is present after all
                                            locations have been loaded, indicating the base
                                            location is missing or incorrect
        """
        base_location = self.application.make("config.location")
        config_roots = [base_location]
        config_roots.extend(other_paths or [])

        for config_root in config_roots:
            for module_name, module in Loader.get_modules(
                    config_root, raise_exception=False
            ).items():
                params = Loader.get_parameters(module)
                incoming = {name.lower(): value for name, value in params.items()}
                existing = self._config.get(module_name)
                if existing is not None:
                    self._config[module_name] = _deep_merge(existing, incoming)
                else:
                    self._config[module_name] = incoming

        if not self._config.get("application"):
            raise InvalidConfigurationLocation(
                f"Config directory '{base_location}' does not contain required configuration files."
            )

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
