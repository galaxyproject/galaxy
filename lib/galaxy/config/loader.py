import logging
import os

from galaxy.config.schema import AppSchema
from galaxy.exceptions import ConfigurationError
from galaxy.util import string_as_bool

GALAXY_APP_NAME = 'galaxy'
GALAXY_CONFIG_SCHEMA_PATH = 'lib/galaxy/webapps/galaxy/config_schema.yml'

log = logging.getLogger(__name__)


class ConfigurationLoader():
    # {key: config option, value: deprecated directory name}
    # If value == first dir in a user path that resolves to key, it will be stripped from the path
    deprecated_dirs = {'config_dir': 'config', 'data_dir': 'database'}

    def load(self, appconfig, kwargs):
        self._load_schema()  # Load schema from schema definition file
        self._load_config_from_schema()  # Load default propery values from schema
        self._validate_schema_paths()  # check that paths can be resolved
        self._update_raw_config_from_kwargs(kwargs)  # Overwrite default values passed as kwargs
        self._create_attributes_from_raw_config(appconfig)  # Create attributes for LOADED properties
        self._resolve_paths(appconfig, kwargs)  # Overwrite attributes (not _raw_config) w/resolved paths

    def _load_schema(self):
        self.schema = AppSchema(GALAXY_CONFIG_SCHEMA_PATH, GALAXY_APP_NAME)
        self.appschema = self.schema.app_schema

    def _load_config_from_schema(self):
        self._raw_config = {}  # keeps track of startup values (kwargs or schema default)
        self.reloadable_options = set()  # config options we can reload at runtime
        self._paths_to_resolve = {}  # {config option: referenced config option}
        for key, data in self.appschema.items():
            self._raw_config[key] = data.get('default')
            if data.get('reloadable'):
                self.reloadable_options.add(key)
            if data.get('path_resolves_to'):
                self._paths_to_resolve[key] = data.get('path_resolves_to')

    def _validate_schema_paths(self):

        def check_exists(option, key):
            if not option:
                message = "Invalid schema: property '{}' listed as path resolution target " \
                    "for '{}' does not exist".format(resolves_to, key)
                raise_error(message)

        def check_type_is_str(option, key):
            if option.get('type') != 'str':
                message = "Invalid schema: property '{}' should have type 'str'".format(key)
                raise_error(message)

        def check_is_dag():
            visited = set()
            for key in self._paths_to_resolve:
                visited.clear()
                while key:
                    visited.add(key)
                    key = self.appschema[key].get('path_resolves_to')
                    if key and key in visited:
                        raise_error('Invalid schema: cycle detected')

        def raise_error(message):
            log.error(message)
            raise ConfigurationError(message)

        for key, resolves_to in self._paths_to_resolve.items():
            parent = self.appschema.get(resolves_to)
            check_exists(parent, key)
            check_type_is_str(parent, key)
            check_type_is_str(self.appschema[key], key)
        check_is_dag()  # must be called last: walks entire graph

    def _update_raw_config_from_kwargs(self, kwargs):

        def convert_datatype(key, value):
            datatype = self.appschema[key].get('type')
            # check for `not None` explicitly (value can be falsy)
            if value is not None and datatype in type_converters:
                return type_converters[datatype](value)
            return value

        def strip_deprecated_dir(key, value):
            resolves_to = self.appschema[key].get('path_resolves_to')
            if resolves_to:  # value is a path that will be resolved
                first_dir = value.split(os.sep)[0]  # get first directory component
                if first_dir == self.deprecated_dirs[resolves_to]:  # first_dir is deprecated for this option
                    ignore = first_dir + os.sep
                    log.warning(
                        "Paths for the '%s' option are now relative to '%s', remove the leading '%s' "
                        "to suppress this warning: %s", key, resolves_to, ignore, value
                    )
                    return value[len(ignore):]
            return value

        type_converters = {'bool': string_as_bool, 'int': int, 'float': float, 'str': str}

        for key, value in kwargs.items():
            if key in self.appschema:
                value = convert_datatype(key, value)
                if value:
                    value = strip_deprecated_dir(key, value)
                self._raw_config[key] = value

    def _create_attributes_from_raw_config(self, appconfig):
        for key, value in self._raw_config.items():
            if not hasattr(appconfig, key):
                setattr(appconfig, key, value)
            else:
                log.debug("Attribute '%s' is set and cannot be overwritten with value '%s'" % (key, value))

    def _resolve_paths(self, appconfig, kwargs):

        def resolve(key):
            if key in _cache:  # resolve each path only once
                return _cache[key]

            path = getattr(appconfig, key)  # path prior to being resolved
            parent = self.appschema[key].get('path_resolves_to')
            if not parent:  # base case: nothing else needs resolving
                return path
            parent_path = resolve(parent)  # recursively resolve parent path
            if path is not None:
                path = os.path.join(parent_path, path)  # resolve path
            else:
                path = parent_path  # or use parent path

            setattr(appconfig, key, path)  # update property
            _cache[key] = path  # cache it!
            return path

        _cache = {}
        for key in self._paths_to_resolve:
            resolve(key)
