import logging

from galaxy.exceptions import ConfigurationError
from galaxy.util.yaml_util import ordered_load

log = logging.getLogger(__name__)

OPTION_DEFAULTS = {
    "type": "str",
    "unknown_option": False,
    "default": None,
    "desc": None,
}

UNKNOWN_OPTION = {
    "type": "str",
    "required": False,
    "unknown_option": True,
    "desc": "Unknown option, may want to remove or report to Galaxy team.",
}


class Schema:
    def __init__(self, mapping):
        self.app_schema = mapping

    def get_app_option(self, name):
        try:
            raw_option = self.app_schema[name]
        except KeyError:
            raw_option = UNKNOWN_OPTION
        option = OPTION_DEFAULTS.copy()
        option.update(raw_option)
        return option


class AppSchema(Schema):
    def __init__(self, schema_path, app_name):
        self.raw_schema = self._read_schema(schema_path)
        self.description = self.raw_schema.get("desc", None)
        app_schema = self.raw_schema["mapping"][app_name]["mapping"]
        self._preprocess(app_schema)
        super().__init__(app_schema)

    def _read_schema(self, path):
        with open(path) as f:
            return ordered_load(f)

    def _preprocess(self, app_schema):
        """Populate schema collections used for app configuration."""
        self._defaults = {}  # {config option: default value or null}
        self._reloadable_options = set()  # config options we can reload at runtime
        self._paths_to_resolve = {}  # {config option: referenced config option}
        self._per_host_options = set()  # config options that can be set using a per_host config parameter
        self._deprecated_aliases = {}
        for key, data in app_schema.items():
            self._defaults[key] = data.get("default")
            if data.get("deprecated_alias"):
                self._deprecated_aliases[data.get("deprecated_alias")] = key
            if data.get("reloadable"):
                self._reloadable_options.add(key)
            if data.get("per_host"):
                resolves_to = data.get("resolves_to")
                if resolves_to:
                    self._per_host_options.add(resolves_to)
                else:
                    self._per_host_options.add(key)
            if data.get("path_resolves_to"):
                self._paths_to_resolve[key] = data.get("path_resolves_to")

    @property
    def defaults(self):
        return self._defaults

    @property
    def paths_to_resolve(self):
        return self._paths_to_resolve

    @property
    def reloadable_options(self):
        return self._reloadable_options

    @property
    def per_host_options(self):
        return self._per_host_options

    def validate_path_resolution_graph(self):
        """This method is for tests only: we SHOULD validate the schema's path resolution graph
        as part of automated testing; but we should NOT validate it at runtime.
        """

        def check_exists(option, key):
            if not option:
                message = (
                    "Invalid schema: property '{}' listed as path resolution target "
                    "for '{}' does not exist".format(resolves_to, key)
                )
                raise_error(message)

        def check_type_is_str_or_any(option, key):
            if option.get("type") not in ("str", "any"):
                message = f"Invalid schema: property '{key}' should have type 'str'"
                raise_error(message)

        def check_is_dag():
            visited = set()
            for key in self.paths_to_resolve:
                visited.clear()
                while key:
                    visited.add(key)
                    key = self.app_schema[key].get("path_resolves_to")
                    if key and key in visited:
                        raise_error("Invalid schema: cycle detected")

        def raise_error(message):
            log.error(message)
            raise ConfigurationError(message)

        for key, resolves_to in self.paths_to_resolve.items():
            print(key)
            parent = self.app_schema.get(resolves_to)
            check_exists(parent, key)
            check_type_is_str_or_any(parent, key)
            check_type_is_str_or_any(self.app_schema[key], key)
        check_is_dag()  # must be called last: walks entire graph
