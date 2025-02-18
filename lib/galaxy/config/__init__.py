"""
Universe configuration builder.
"""

# absolute_import needed for tool_shed package.

import configparser
import json
import locale
import logging
import logging.config
import os
import re
import socket
import string
import sys
import tempfile
import threading
from datetime import timedelta
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    List,
    Optional,
    Set,
    SupportsInt,
    TYPE_CHECKING,
    TypeVar,
    Union,
)
from urllib.parse import urlparse

import yaml

from galaxy.config.schema import AppSchema
from galaxy.exceptions import ConfigurationError
from galaxy.util import (
    listify,
    size_to_bytes,
    string_as_bool,
    unicodify,
)
from galaxy.util.config_parsers import parse_allowlist_ips
from galaxy.util.custom_logging import LOGLV_TRACE
from galaxy.util.dynamic import HasDynamicProperties
from galaxy.util.facts import get_facts
from galaxy.util.hash_util import HashFunctionNameEnum
from galaxy.util.properties import (
    read_properties_from_file,
    running_from_source,
)
from galaxy.util.resources import (
    as_file,
    resource_path,
)
from galaxy.util.themes import flatten_theme
from ..util.logging import set_logging_levels_from_config
from ..version import (
    VERSION_MAJOR,
    VERSION_MINOR,
)

if TYPE_CHECKING:
    from galaxy.model import User

log = logging.getLogger(__name__)

DEFAULT_LOCALE_FORMAT = "%a %b %e %H:%M:%S %Y"
ISO_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

GALAXY_APP_NAME = "galaxy"
GALAXY_SCHEMAS_PATH = resource_path(__name__, "schemas")
GALAXY_CONFIG_SCHEMA_PATH = GALAXY_SCHEMAS_PATH / "config_schema.yml"
REPORTS_CONFIG_SCHEMA_PATH = GALAXY_SCHEMAS_PATH / "reports_config_schema.yml"
TOOL_SHED_CONFIG_SCHEMA_PATH = GALAXY_SCHEMAS_PATH / "tool_shed_config_schema.yml"
LOGGING_CONFIG_DEFAULT: Dict[str, Any] = {
    "disable_existing_loggers": False,
    "version": 1,
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "paste.httpserver.ThreadPool": {
            "level": "WARN",
            "qualname": "paste.httpserver.ThreadPool",
        },
        "sqlalchemy_json.track": {
            "level": "WARN",
            "qualname": "sqlalchemy_json.track",
        },
        "urllib3.connectionpool": {
            "level": "WARN",
            "qualname": "urllib3.connectionpool",
        },
        "routes.middleware": {
            "level": "WARN",
            "qualname": "routes.middleware",
        },
        "amqp": {
            "level": "INFO",
            "qualname": "amqp",
        },
        "botocore": {
            "level": "INFO",
            "qualname": "botocore",
        },
        "gunicorn.access": {
            "level": "INFO",
            "qualname": "gunicorn.access",
            "propagate": False,
            "handlers": ["console"],
        },
        "watchdog.observers.inotify_buffer": {
            "level": "INFO",
            "qualname": "watchdog.observers.inotify_buffer",
        },
        "py.warnings": {
            "level": "ERROR",
            "qualname": "py.warnings",
        },
        "celery.utils.functional": {
            "level": "INFO",
            "qualname": "celery.utils.functional",
        },
    },
    "filters": {
        "stack": {
            "()": "galaxy.web_stack.application_stack_log_filter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "stack",
            "level": "DEBUG",
            "stream": "ext://sys.stderr",
            "filters": ["stack"],
        },
    },
    "formatters": {
        "stack": {
            "()": "galaxy.web_stack.application_stack_log_formatter",
        },
    },
}
"""Default value for logging configuration, passed to :func:`logging.config.dictConfig`"""

DEPENDENT_CONFIG_DEFAULTS: Dict[str, str] = {
    "mulled_resolution_cache_url": "database_connection",
    "citation_cache_url": "database_connection",
    "biotools_service_cache_url": "database_connection",
}
"""Config parameters whose default is the value of another config parameter
This should be moved to a .yml config file.
"""

VERSION_JSON_FILE = "version.json"
DEFAULT_EMAIL_FROM_LOCAL_PART = "galaxy-no-reply"
DISABLED_FLAG = "disabled"  # Used to mark a config option as disabled


def configure_logging(config, facts=None):
    """Allow some basic logging configuration to be read from ini file.

    This should be able to consume either a galaxy.config.Configuration object
    or a simple dictionary of configuration variables.
    """
    facts = facts or get_facts(config=config)

    # PasteScript will have already configured the logger if the
    # 'loggers' section was found in the config file, otherwise we do
    # some simple setup using the 'log_*' values from the config.
    parser = getattr(config, "global_conf_parser", None)
    if parser:
        paste_configures_logging = config.global_conf_parser.has_section("loggers")
    else:
        paste_configures_logging = False
    auto_configure_logging = not paste_configures_logging and string_as_bool(
        config.get("auto_configure_logging", "True")
    )
    if auto_configure_logging:
        logging_conf = config.get("logging", None)
        if logging_conf is None:
            # if using the default logging config, honor the log_level setting
            logging_conf = LOGGING_CONFIG_DEFAULT
            if config.get("log_level", "DEBUG") != "DEBUG":
                logging_conf["handlers"]["console"]["level"] = config.get("log_level", "DEBUG")
        # configure logging with logging dict in config, template *FileHandler handler filenames with the `filename_template` option
        for name, conf in logging_conf.get("handlers", {}).items():
            if (
                conf["class"].startswith("logging.")
                and conf["class"].endswith("FileHandler")
                and "filename_template" in conf
            ):
                conf["filename"] = conf.pop("filename_template").format(**facts)
                logging_conf["handlers"][name] = conf
        logging.config.dictConfig(logging_conf)
        logging_levels = config.get("logging_levels", None)
        if logging_levels:
            set_logging_levels_from_config(logging_levels)



def find_root(kwargs) -> str:
    return os.path.abspath(kwargs.get("root_dir", "."))


def expand_pretty_datetime_format(value):
    """

    >>> expand_pretty_datetime_format("%H:%M:%S %Z")
    '%H:%M:%S %Z'
    >>> locale_format = expand_pretty_datetime_format("$locale (UTC)")
    >>> import locale
    >>> expected_format = '%s (UTC)' % locale.nl_langinfo(locale.D_T_FMT)
    >>> locale_format == expected_format
    True
    >>> expand_pretty_datetime_format("$iso8601")
    '%Y-%m-%d %H:%M:%S'
    """
    locale_format = None
    try:
        locale_format = locale.nl_langinfo(locale.D_T_FMT)
    except AttributeError:  # nl_langinfo not available
        pass
    if not locale_format:
        locale_format = DEFAULT_LOCALE_FORMAT
    stock_formats = dict(
        locale=locale_format,
        iso8601=ISO_DATETIME_FORMAT,
    )
    return string.Template(value).safe_substitute(**stock_formats)


OptStr = TypeVar("OptStr", None, str)


class BaseAppConfiguration(HasDynamicProperties):
    # Override in subclasses (optional): {KEY: config option, VALUE: deprecated directory name}
    # If VALUE == first directory in a user-supplied path that resolves to KEY, it will be stripped from that path
    renamed_options: Optional[Dict[str, str]] = None
    deprecated_dirs: Dict[str, str] = {}
    paths_to_check_against_root: Set[str] = (
        set()
    )  # backward compatibility: if resolved path doesn't exist, try resolving w.r.t root
    add_sample_file_to_defaults: Set[str] = set()  # for these options, add sample config files to their defaults
    listify_options: Set[str] = set()  # values for these options are processed as lists of values
    object_store_store_by: str
    shed_tools_dir: str

    def __init__(self, **kwargs):
        self._preprocess_kwargs(kwargs)
        self._kwargs = kwargs  # Save these as a record of explicitly set options
        self.config_dict = kwargs
        self.root = find_root(kwargs)
        self._set_config_base(kwargs)
        self.schema = self._load_schema()  # Load schema from schema definition file
        self._raw_config = self.schema.defaults.copy()  # Save schema defaults as initial config values (raw_config)
        self._update_raw_config_from_kwargs(kwargs)  # Overwrite raw_config with values passed in kwargs
        self._create_attributes_from_raw_config()  # Create attributes based on raw_config
        self._preprocess_paths_to_resolve()  # Any preprocessing steps that need to happen before paths are resolved
        self._resolve_paths()  # Overwrite attribute values with resolved paths
        self._postprocess_paths_to_resolve()  # Any steps that need to happen after paths are resolved

    def _preprocess_kwargs(self, kwargs):
        self._process_renamed_options(kwargs)
        self._fix_postgresql_dburl(kwargs)

    def _process_renamed_options(self, kwargs):
        """Update kwargs to set any unset renamed options to values of old-named options, if set.

        Does not remove the old options from kwargs so that deprecated option usage can be logged.
        """
        if self.renamed_options is not None:
            for old, new in self.renamed_options.items():
                if old in kwargs and new not in kwargs:
                    kwargs[new] = kwargs[old]

    def _fix_postgresql_dburl(self, kwargs):
        """
        Fix deprecated database URLs (postgres... >> postgresql...)
        https://docs.sqlalchemy.org/en/14/changelog/changelog_14.html#change-3687655465c25a39b968b4f5f6e9170b
        """
        old_dialect, new_dialect = "postgres", "postgresql"
        old_prefixes = (f"{old_dialect}:", f"{old_dialect}+")  # check for postgres://foo and postgres+driver//foo
        offset = len(old_dialect)
        keys = ("database_connection", "install_database_connection")
        for key in keys:
            if key in kwargs:
                value = kwargs[key]
                for prefix in old_prefixes:
                    if value.startswith(prefix):
                        value = f"{new_dialect}{value[offset:]}"
                        kwargs[key] = value
                        log.warning(
                            'PostgreSQL database URLs of the form "postgres://" have been '
                            'deprecated. Please use "postgresql://".'
                        )

    def is_set(self, key):
        """Check if a configuration option has been explicitly set."""
        # NOTE: This will check all supplied keyword arguments, including those not in the schema.
        # To check only schema options, change the line below to `if property not in self._raw_config:`
        if key not in self._raw_config:
            log.warning(f"Configuration option does not exist: '{key}'")
        return key in self._kwargs

    def resolve_path(self, path):
        """Resolve a path relative to Galaxy's root."""
        return self._in_root_dir(path)

    def _set_config_base(self, config_kwargs):
        def _set_global_conf():
            self.config_file = config_kwargs.get("__file__", None)
            self.global_conf = config_kwargs.get("global_conf")
            self.global_conf_parser = configparser.ConfigParser()
            if not self.config_file and self.global_conf and "__file__" in self.global_conf:
                self.config_file = os.path.join(self.root, self.global_conf["__file__"])

            if self.config_file is None:
                log.warning("No Galaxy config file found, running from current working directory: %s", os.getcwd())
            else:
                try:
                    self.global_conf_parser.read(self.config_file)
                except OSError:
                    raise
                except Exception:
                    pass  # Not an INI file

        def _set_config_directories():
            # Set config_dir to value from kwargs OR dirname of config_file OR None
            _config_dir = os.path.dirname(self.config_file) if self.config_file else None
            self.config_dir = config_kwargs.get("config_dir", _config_dir)
            # Make path absolute before using it as base for other paths
            if self.config_dir:
                self.config_dir = os.path.abspath(self.config_dir)

            self.data_dir = config_kwargs.get("data_dir")
            if self.data_dir:
                self.data_dir = os.path.abspath(self.data_dir)

            self.sample_config_dir = os.path.join(os.path.dirname(__file__), "sample")
            if self.sample_config_dir:
                self.sample_config_dir = os.path.abspath(self.sample_config_dir)

            self.managed_config_dir = config_kwargs.get("managed_config_dir")
            if self.managed_config_dir:
                self.managed_config_dir = os.path.abspath(self.managed_config_dir)

            if running_from_source:
                if not self.config_dir:
                    self.config_dir = os.path.join(self.root, "config")
                if not self.data_dir:
                    self.data_dir = os.path.join(self.root, "database")
                if not self.managed_config_dir:
                    self.managed_config_dir = self.config_dir
            else:
                if not self.config_dir:
                    self.config_dir = os.getcwd()
                if not self.data_dir:
                    self.data_dir = self._in_config_dir("data")
                if not self.managed_config_dir:
                    self.managed_config_dir = self._in_data_dir("config")

            # TODO: do we still need to support ../shed_tools when running_from_source?
            self.shed_tools_dir = self._in_data_dir("shed_tools")

            log.debug("Configuration directory is %s", self.config_dir)
            log.debug("Data directory is %s", self.data_dir)
            log.debug("Managed config directory is %s", self.managed_config_dir)

        _set_global_conf()
        _set_config_directories()

    def _load_schema(self):
        # Override in subclasses
        raise Exception("Not implemented")

    def _preprocess_paths_to_resolve(self):
        # For these options, if option is not set, listify its defaults and add a sample config file.
        if self.add_sample_file_to_defaults:
            for key in self.add_sample_file_to_defaults:
                if not self.is_set(key):
                    defaults = listify(getattr(self, key), do_strip=True)
                    sample = f"{defaults[-1]}.sample"  # if there are multiple defaults, use last as template
                    sample = self._in_sample_dir(sample)  # resolve w.r.t sample_dir
                    defaults.append(sample)
                    setattr(self, key, defaults)

    def _postprocess_paths_to_resolve(self):
        def select_one_path_from_list():
            # To consider: options with a sample file added to defaults except options that can have multiple values.
            # If value is not set, check each path in list; set to first path that exists; if none exist, set to last path in list.
            keys = (
                self.add_sample_file_to_defaults - self.listify_options
                if self.listify_options
                else self.add_sample_file_to_defaults
            )
            for key in keys:
                if not self.is_set(key):
                    paths = getattr(self, key)
                    for path in paths:
                        if self._path_exists(path):
                            setattr(self, key, path)
                            break
                    else:
                        setattr(
                            self, key, paths[-1]
                        )  # TODO: we assume it exists; but we've already checked in the loop! Raise error instead?

        def select_one_or_all_paths_from_list():
            # Values for these options are lists of paths. If value is not set, use defaults if all paths in list exist;
            # otherwise, set to last path in list.
            for key in self.listify_options:
                if not self.is_set(key):
                    paths = getattr(self, key)
                    for path in paths:
                        if not self._path_exists(path):
                            setattr(self, key, [paths[-1]])  # value is a list
                            break

        if (
            self.add_sample_file_to_defaults
        ):  # Currently, this is the ONLY case when we need to pick one file from a list
            select_one_path_from_list()
        if self.listify_options:
            select_one_or_all_paths_from_list()

    def _path_exists(self, path):  # factored out so we can mock it in tests
        return os.path.exists(path)

    def _set_alt_paths(self, option, *alt_paths):
        # If `option` is not set, check *alt_paths. Set `option` to first path that exists and return it.
        if not self.is_set(option):
            for path in alt_paths:
                if self._path_exists(path):
                    setattr(self, option, path)
                    return path

    def _update_raw_config_from_kwargs(self, kwargs):
        type_converters: Dict[str, Callable[[Any], Union[bool, int, float, str]]] = {
            "bool": string_as_bool,
            "int": int,
            "float": float,
            "str": str,
        }

        def convert_datatype(key, value):
            datatype = self.schema.app_schema[key].get("type")
            # check for `not None` explicitly (value can be falsy)
            if value is not None and datatype in type_converters:
                # convert value or each item in value to type `datatype`
                f = type_converters[datatype]
                if isinstance(value, list):
                    return [f(item) for item in value]
                else:
                    return f(value)
            return value

        def strip_deprecated_dir(key, value):
            resolves_to = self.schema.paths_to_resolve.get(key)
            if resolves_to:  # value contains paths that will be resolved
                paths = listify(value, do_strip=True)
                for i, path in enumerate(paths):
                    first_dir = path.split(os.sep)[0]  # get first directory component
                    if first_dir == self.deprecated_dirs.get(resolves_to):  # first_dir is deprecated for this option
                        ignore = first_dir + os.sep
                        log.warning(
                            "Paths for the '%s' option are now relative to '%s', remove the leading '%s' "
                            "to suppress this warning: %s",
                            key,
                            resolves_to,
                            ignore,
                            path,
                        )
                        paths[i] = path[len(ignore) :]

                # return list or string, depending on type of `value`
                if isinstance(value, list):
                    return paths
                return ",".join(paths)
            return value

        for key, value in kwargs.items():
            if key in self.schema._deprecated_aliases:
                new_key = self.schema._deprecated_aliases[key]
                log.warning(f"Option {key} has been deprecated in favor of {new_key}")
                key = new_key

            if key in self.schema.app_schema:
                value = convert_datatype(key, value)
                if value and self.deprecated_dirs:
                    value = strip_deprecated_dir(key, value)
                self._raw_config[key] = value

    def _create_attributes_from_raw_config(self):
        # `base_configs` are a special case: these attributes have been created and will be ignored
        # by the code below. Trying to overwrite any other existing attributes will raise an error.
        base_configs = {"config_dir", "data_dir", "managed_config_dir"}
        for key, value in self._raw_config.items():
            if not hasattr(self, key):
                setattr(self, key, value)
            elif key not in base_configs:
                raise ConfigurationError(f"Attempting to override existing attribute '{key}'")

    def _resolve_paths(self):
        def resolve(key):
            if key in _cache:  # resolve each path only once
                return _cache[key]

            path = getattr(self, key)  # path prior to being resolved
            parent = self.schema.paths_to_resolve.get(key)
            if not parent:  # base case: nothing else needs resolving
                return path
            parent_path = resolve(parent)  # recursively resolve parent path
            if path:
                path = os.path.join(parent_path, path)  # resolve path
            else:
                log.warning("Trying to resolve path for the '%s' option but it's empty/None", key)

            setattr(self, key, path)  # update property
            _cache[key] = path  # cache it!
            return path

        _cache = {}
        for key in self.schema.paths_to_resolve:
            value = getattr(self, key)
            # Check if value is a list or should be listified; if so, listify and resolve each item separately.
            if isinstance(value, list) or (self.listify_options and key in self.listify_options):
                saved_values = listify(getattr(self, key), do_strip=True)  # listify and save original value
                setattr(self, key, "_")  # replace value with temporary placeholder
                resolve(key)  # resolve temporary value (`_` becomes `parent-path/_`)
                resolved_base = getattr(self, key)[:-1]  # get rid of placeholder in resolved path
                # apply resolved base to saved values
                resolved_paths = [os.path.join(resolved_base, value) for value in saved_values]
                setattr(self, key, resolved_paths)  # set config.key to a list of resolved paths
            else:
                resolve(key)
            # Check options that have been set and may need to be resolved w.r.t. root
            if self.is_set(key) and self.paths_to_check_against_root and key in self.paths_to_check_against_root:
                self._check_against_root(key)

    def _check_against_root(self, key: str):
        def get_path(current_path, initial_path):
            # TODO: Not sure why this is needed for the logging API tests...
            if initial_path is None:
                return current_path
            # if path does not exist and was set as relative:
            if not self._path_exists(current_path) and not os.path.isabs(initial_path):
                new_path = self._in_root_dir(initial_path)
                if self._path_exists(new_path):  # That's a bingo!
                    resolves_to = self.schema.paths_to_resolve.get(key)
                    log.warning(
                        "Paths for the '%s' option should be relative to '%s'. To suppress this warning, "
                        "move '%s' into '%s', or set its value to an absolute path.",
                        key,
                        resolves_to,
                        key,
                        resolves_to,
                    )
                    return new_path
            return current_path

        current_value = getattr(self, key)  # resolved path or list of resolved paths
        if not current_value:
            return
        if isinstance(current_value, list):
            initial_paths = listify(self._raw_config[key], do_strip=True)  # initial unresolved paths
            updated_paths = []
            # check and, if needed, update each path in the list
            for current_path, initial_path in zip(current_value, initial_paths):
                path = get_path(current_path, initial_path)
                updated_paths.append(path)  # add to new list regardless of whether path has changed or not
            setattr(self, key, updated_paths)  # update: one or more paths may have changed
        else:
            initial_path = self._raw_config[key]  # initial unresolved path
            path = get_path(current_value, initial_path)
            if path != current_value:
                setattr(self, key, path)  # update if path has changed

    def _in_root_dir(self, path: OptStr) -> OptStr:
        return self._in_dir(self.root, path)

    def _in_managed_config_dir(self, path: OptStr) -> OptStr:
        return self._in_dir(self.managed_config_dir, path)

    def _in_config_dir(self, path: OptStr) -> OptStr:
        return self._in_dir(self.config_dir, path)

    def _in_sample_dir(self, path: OptStr) -> OptStr:
        return self._in_dir(self.sample_config_dir, path)

    def _in_data_dir(self, path: OptStr) -> OptStr:
        return self._in_dir(self.data_dir, path)

    def _in_dir(self, _dir: str, path: OptStr) -> OptStr:
        if path is not None:
            return os.path.join(_dir, path)
        return None


class CommonConfigurationMixin:
    """Shared configuration settings code for Galaxy and ToolShed."""

    sentry_dsn: str
    config_dict: Dict[str, str]

    @property
    def admin_users(self):
        return self._admin_users

    @admin_users.setter
    def admin_users(self, value):
        self._admin_users = value
        self.admin_users_list = listify(value, do_strip=True)

    def is_admin_user(self, user: Optional["User"]) -> bool:
        """Determine if the provided user is listed in `admin_users`."""
        return user is not None and (user.email in self.admin_users_list or user.bootstrap_admin_user)

    @property
    def sentry_dsn_public(self):
        """
        Sentry URL with private key removed for use in client side scripts,
        sentry server will need to be configured to accept events
        """
        if self.sentry_dsn:
            return re.sub(r"^([^:/?#]+:)?//(\w+):(\w+)", r"\1//\2", self.sentry_dsn)

    def get_bool(self, key, default):
        # Warning: the value of self.config_dict['foo'] may be different from self.foo
        if key in self.config_dict:
            return string_as_bool(self.config_dict[key])
        else:
            return default

    def get(self, key, default=None):
        # Warning: the value of self.config_dict['foo'] may be different from self.foo
        return self.config_dict.get(key, default)

    def _ensure_directory(self, path):
        if path not in [None, False] and not os.path.isdir(path):
            try:
                os.makedirs(path)
            except Exception as e:
                raise ConfigurationError(f"Unable to create missing directory: {path}\n{unicodify(e)}")


class GalaxyAppConfiguration(BaseAppConfiguration, CommonConfigurationMixin):
    renamed_options = {
        "blacklist_file": "email_domain_blocklist_file",
        "whitelist_file": "email_domain_allowlist_file",
        "sanitize_whitelist_file": "sanitize_allowlist_file",
        "user_library_import_symlink_whitelist": "user_library_import_symlink_allowlist",
        "fetch_url_whitelist": "fetch_url_allowlist",
        "containers_resolvers_config_file": "container_resolvers_config_file",
        "activation_email": "email_from",
        "ga4gh_service_organization_name": "organization_name",
        "ga4gh_service_organization_url": "organization_url",
    }

    deprecated_options = list(renamed_options.keys()) + [
        "database_file",
        "track_jobs_in_database",
    ]

    default_config_file_name = "galaxy.yml"
    deprecated_dirs = {"config_dir": "config", "data_dir": "database"}

    paths_to_check_against_root = {
        "auth_config_file",
        "build_sites_config_file",
        "data_manager_config_file",
        "datatypes_config_file",
        "dependency_resolvers_config_file",
        "error_report_file",
        "job_config_file",
        "job_metrics_config_file",
        "job_resource_params_file",
        "local_conda_mapping_file",
        "migrated_tools_config",
        "modules_mapping_files",
        "object_store_config_file",
        "oidc_backends_config_file",
        "oidc_config_file",
        "shed_data_manager_config_file",
        "shed_tool_config_file",
        "shed_tool_data_table_config",
        "tool_destinations_config_file",
        "tool_sheds_config_file",
        "user_preferences_extra_conf_path",
        "workflow_resource_params_file",
        "workflow_schedulers_config_file",
        "markdown_export_css",
        "markdown_export_css_pages",
        "markdown_export_css_invocation_reports",
        "file_path",
        "tool_data_table_config_path",
        "tool_config_file",
        "themes_config_file",
    }

    add_sample_file_to_defaults = {
        "build_sites_config_file",
        "datatypes_config_file",
        "tool_data_table_config_path",
        "tool_config_file",
    }

    listify_options = {
        "tool_data_table_config_path",
        "tool_config_file",
    }

    allowed_origin_hostnames: List[str]
    builds_file_path: str
    container_resolvers_config_file: str
    database_connection: str
    drmaa_external_runjob_script: str
    email_from: Optional[str]
    enable_tool_shed_check: bool
    file_source_temp_dir: str
    galaxy_data_manager_data_path: str
    galaxy_infrastructure_url: str
    hours_between_check: int
    hash_function: HashFunctionNameEnum
    integrated_tool_panel_config: str
    involucro_path: str
    len_file_path: str
    manage_dependency_relationships: bool
    monitor_thread_join_timeout: int
    mulled_channels: List[str]
    new_file_path: str
    nginx_upload_store: str
    password_expiration_period: timedelta
    preserve_python_environment: str
    pretty_datetime_format: str
    sanitize_allowlist_file: str
    shed_tool_data_path: str
    themes: Dict[str, Dict[str, str]]
    themes_by_host: Dict[str, Dict[str, Dict[str, str]]]
    tool_data_path: str
    tool_dependency_dir: Optional[str]
    tool_filters: List[str]
    tool_label_filters: List[str]
    tool_path: str
    tool_section_filters: List[str]
    toolbox_filter_base_modules: List[str]
    track_jobs_in_database: bool
    trust_jupyter_notebook_conversion: bool
    tus_upload_store: str
    use_remote_user: bool
    user_library_import_dir_auto_creation: bool
    user_library_import_symlink_allowlist: List[str]
    user_tool_filters: List[str]
    user_tool_label_filters: List[str]
    user_tool_section_filters: List[str]
    visualization_plugins_directory: str
    workflow_resource_params_mapper: str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._override_tempdir(kwargs)
        self._process_config(kwargs)
        self._set_dependent_defaults()

    def _set_dependent_defaults(self):
        """Set values of unset parameters which take their default values from other parameters"""
        for dependent_config_param, config_param in DEPENDENT_CONFIG_DEFAULTS.items():
            try:
                if getattr(self, dependent_config_param) is None:
                    setattr(self, dependent_config_param, getattr(self, config_param))
            except AttributeError:
                raise Exception(
                    "One or more invalid config parameter names specified in "
                    "DEPENDENT_CONFIG_DEFAULTS, "
                    f"{dependent_config_param}, {config_param}"
                )

    def _load_schema(self):
        return AppSchema(GALAXY_CONFIG_SCHEMA_PATH, GALAXY_APP_NAME)

    def _override_tempdir(self, kwargs):
        if string_as_bool(kwargs.get("override_tempdir", "True")):
            tempfile.tempdir = self.new_file_path

    def config_value_for_host(self, config_option, host):
        val = getattr(self, config_option)
        if config_option in self.schema.per_host_options:
            per_host_option = f"{config_option}_by_host"
            per_host: Dict[str, Any] = {}
            if per_host_option in self.config_dict:
                per_host = self.config_dict[per_host_option] or {}
            else:
                per_host = getattr(self, per_host_option, {})
            for host_key, host_val in per_host.items():
                if host_key in host:
                    val = host_val
                    break

        return val

    def _process_config(self, kwargs: Dict[str, Any]) -> None:
        self._check_database_connection_strings()
        # Backwards compatibility for names used in too many places to fix
        self.datatypes_config = self.datatypes_config_file
        self.tool_configs = self.tool_config_file

        # Collect the umask and primary gid from the environment
        self.umask = os.umask(0o77)  # get the current umask
        os.umask(self.umask)  # can't get w/o set, so set it back
        self.gid = os.getgid()  # if running under newgrp(1) we'll need to fix the group of data created on the cluster

        self.version_major = VERSION_MAJOR
        self.version_minor = VERSION_MINOR
        # Try loading extra version info
        self.version_extra = None
        json_file = os.environ.get(
            "GALAXY_VERSION_JSON_FILE", self._in_root_dir(VERSION_JSON_FILE)
        )  # TODO: add this to schema
        try:
            with open(json_file) as f:
                extra_info = json.load(f)
        except FileNotFoundError:
            log.debug("No extra version JSON file detected at %s", json_file)
        except ValueError:
            log.error("Error loading Galaxy extra version JSON file %s - details not loaded.", json_file)
        else:
            self.version_extra = extra_info

        # Database related configuration
        self.check_migrate_databases = string_as_bool(kwargs.get("check_migrate_databases", True))
        if not self.database_connection:  # Provide default if not supplied by user
            db_path = self._in_data_dir("universe.sqlite")
            self.database_connection = f"sqlite:///{db_path}?isolation_level=IMMEDIATE"
        self.database_engine_options = get_database_engine_options(kwargs)
        self.database_encoding = kwargs.get("database_encoding")  # Create new databases with this encoding
        self.thread_local_log = None
        if self.enable_per_request_sql_debugging:
            self.thread_local_log = threading.local()
        # Install database related configuration (if different)
        self.install_database_engine_options = get_database_engine_options(kwargs, model_prefix="install_")
        self.shared_home_dir = kwargs.get("shared_home_dir")
        self.cookie_path = kwargs.get("cookie_path")
        if not running_from_source and kwargs.get("tool_path") is None:
            try:
                with as_file(resource_path("galaxy.tools", "bundled")) as path:
                    self.tool_path = os.fspath(path)
            except ModuleNotFoundError:
                # Might not be a full galaxy installation
                self.tool_path = self._in_root_dir(self.tool_path)
        else:
            self.tool_path = self._in_root_dir(self.tool_path)
        self.tool_data_path = self._in_root_dir(self.tool_data_path)
        if not running_from_source and kwargs.get("tool_data_path") is None:
            self.tool_data_path = self._in_data_dir(self.schema.defaults["tool_data_path"])
        self.builds_file_path = os.path.join(self.tool_data_path, self.builds_file_path)
        self.len_file_path = os.path.join(self.tool_data_path, self.len_file_path)
        self.oidc: Dict[str, Dict] = {}
        self.fixed_delegated_auth: bool = False
        self.integrated_tool_panel_config = self._in_managed_config_dir(self.integrated_tool_panel_config)
        integrated_tool_panel_tracking_directory = kwargs.get("integrated_tool_panel_tracking_directory")
        if integrated_tool_panel_tracking_directory:
            self.integrated_tool_panel_tracking_directory = self._in_root_dir(integrated_tool_panel_tracking_directory)
        else:
            self.integrated_tool_panel_tracking_directory = None
        self.toolbox_filter_base_modules = listify(self.toolbox_filter_base_modules)
        self.tool_filters = listify(self.tool_filters, do_strip=True)
        self.tool_label_filters = listify(self.tool_label_filters, do_strip=True)
        self.tool_section_filters = listify(self.tool_section_filters, do_strip=True)

        self.user_tool_filters = listify(self.user_tool_filters, do_strip=True)
        self.user_tool_label_filters = listify(self.user_tool_label_filters, do_strip=True)
        self.user_tool_section_filters = listify(self.user_tool_section_filters, do_strip=True)
        self.has_user_tool_filters = bool(
            self.user_tool_filters or self.user_tool_label_filters or self.user_tool_section_filters
        )

        self.password_expiration_period = timedelta(days=int(cast(SupportsInt, self.password_expiration_period)))

        if self.shed_tool_data_path:
            self.shed_tool_data_path = self._in_root_dir(self.shed_tool_data_path)
        else:
            self.shed_tool_data_path = self.tool_data_path

        self.running_functional_tests = string_as_bool(kwargs.get("running_functional_tests", False))
        if isinstance(self.hours_between_check, str):
            self.hours_between_check = float(self.hours_between_check)
        try:
            if isinstance(self.hours_between_check, int):
                if self.hours_between_check < 1 or self.hours_between_check > 24:
                    self.hours_between_check = 12
            elif isinstance(self.hours_between_check, float):
                # If we're running functional tests, the minimum hours between check should be reduced to 0.001, or 3.6 seconds.
                if self.running_functional_tests:
                    if self.hours_between_check < 0.001 or self.hours_between_check > 24.0:
                        self.hours_between_check = 12.0
                else:
                    if self.hours_between_check < 1.0 or self.hours_between_check > 24.0:
                        self.hours_between_check = 12.0
            else:
                self.hours_between_check = 12
        except Exception:
            self.hours_between_check = 12
        self.update_integrated_tool_panel = kwargs.get("update_integrated_tool_panel", True)
        self.galaxy_data_manager_data_path = self.galaxy_data_manager_data_path or self.tool_data_path
        self.tool_secret = kwargs.get("tool_secret", "")
        if self.calculate_dataset_hash not in ("always", "upload", "never"):
            raise ConfigurationError(
                f"Unrecognized value for calculate_dataset_hash option: {self.calculate_dataset_hash}"
            )
        if self.hash_function not in HashFunctionNameEnum.__members__:
            raise ConfigurationError(f"Unrecognized value for hash_function option: {self.hash_function}")
        self.hash_function = HashFunctionNameEnum[self.hash_function]
        self.metadata_strategy = kwargs.get("metadata_strategy", "directory")
        self.use_remote_user = self.use_remote_user or self.single_user
        self.fetch_url_allowlist_ips = parse_allowlist_ips(listify(kwargs.get("fetch_url_allowlist")))
        self.job_queue_cleanup_interval = int(kwargs.get("job_queue_cleanup_interval", "5"))

        # Fall back to legacy job_working_directory config variable if set.
        self.jobs_directory = self._in_data_dir(kwargs.get("jobs_directory", self.job_working_directory))
        if self.preserve_python_environment not in ["legacy_only", "legacy_and_local", "always"]:
            log.warning("preserve_python_environment set to unknown value [%s], defaulting to legacy_only")
            self.preserve_python_environment = "legacy_only"
        self.nodejs_path = kwargs.get("nodejs_path")
        self.container_image_cache_path = self._in_data_dir(kwargs.get("container_image_cache_path", "container_cache"))
        self.output_size_limit = int(kwargs.get("output_size_limit", 0))

        self.email_domain_blocklist_content = (
            self._load_list_from_file(self._in_config_dir(self.email_domain_blocklist_file))
            if self.email_domain_blocklist_file
            else None
        )
        self.email_domain_allowlist_content = (
            self._load_list_from_file(self._in_config_dir(self.email_domain_allowlist_file))
            if self.email_domain_allowlist_file
            else None
        )

        # These are not even beta - just experiments - don't use them unless
        # you want yours tools to be broken in the future.
        self.enable_beta_tool_formats = string_as_bool(kwargs.get("enable_beta_tool_formats", "False"))

        if self.workflow_resource_params_mapper and ":" not in self.workflow_resource_params_mapper:
            # Assume it is not a Python function, so a file; else: a Python function
            self.workflow_resource_params_mapper = self._in_root_dir(self.workflow_resource_params_mapper)

        self.pbs_application_server = kwargs.get("pbs_application_server", "")
        self.pbs_dataset_server = kwargs.get("pbs_dataset_server", "")
        self.pbs_dataset_path = kwargs.get("pbs_dataset_path", "")
        self.pbs_stage_path = kwargs.get("pbs_stage_path", "")

        _sanitize_allowlist_path = self._in_managed_config_dir(self.sanitize_allowlist_file)
        if not os.path.isfile(_sanitize_allowlist_path):  # then check old default location
            for deprecated in (
                self._in_managed_config_dir("sanitize_whitelist.txt"),
                self._in_root_dir("config/sanitize_whitelist.txt"),
            ):
                if os.path.isfile(deprecated):
                    log.warning(
                        "The path '%s' for the 'sanitize_allowlist_file' config option is "
                        "deprecated and will be no longer checked in a future release. Please consult "
                        "the latest version of the sample configuration file.",
                        deprecated,
                    )
                    _sanitize_allowlist_path = deprecated
                    break
        self.sanitize_allowlist_file = _sanitize_allowlist_path

        self.allowed_origin_hostnames = self._parse_allowed_origin_hostnames(self.allowed_origin_hostnames)
        if "trust_jupyter_notebook_conversion" not in kwargs:
            # if option not set, check IPython-named alternative, falling back to schema default if not set either
            _default = self.trust_jupyter_notebook_conversion
            self.trust_jupyter_notebook_conversion = string_as_bool(
                kwargs.get("trust_ipython_notebook_conversion", _default)
            )
        # Configuration for the message box directly below the masthead.
        self.blog_url = kwargs.get("blog_url")
        self.user_library_import_symlink_allowlist = listify(self.user_library_import_symlink_allowlist, do_strip=True)
        self.user_library_import_dir_auto_creation = (
            self.user_library_import_dir_auto_creation if self.user_library_import_dir else False
        )
        # Searching data libraries
        self.ftp_upload_dir_template = kwargs.get(
            "ftp_upload_dir_template", f"${{ftp_upload_dir}}{os.path.sep}${{ftp_upload_dir_identifier}}"
        )
        # Support older library-specific path paste option but just default to the new
        # allow_path_paste value.
        self.allow_library_path_paste = string_as_bool(kwargs.get("allow_library_path_paste", self.allow_path_paste))
        self.disable_library_comptypes = kwargs.get("disable_library_comptypes", "").lower().split(",")
        self.check_upload_content = string_as_bool(kwargs.get("check_upload_content", True))
        # On can mildly speed up Galaxy startup time by disabling index of help,
        # not needed on production systems but useful if running many functional tests.
        self.index_tool_help = string_as_bool(kwargs.get("index_tool_help", True))
        self.tool_labels_boost = kwargs.get("tool_labels_boost", 1)
        default_tool_test_data_directories = os.environ.get("GALAXY_TEST_FILE_DIR", self._in_root_dir("test-data"))
        self.tool_test_data_directories = kwargs.get("tool_test_data_directories", default_tool_test_data_directories)
        # Deployers may either specify a complete list of mapping files or get the default for free and just
        # specify a local mapping file to adapt and extend the default one.
        if "conda_mapping_files" not in kwargs:
            _default_mapping = self._in_root_dir(
                os.path.join("lib", "galaxy", "tool_util", "deps", "resolvers", "default_conda_mapping.yml")
            )
            # dependency resolution options are consumed via config_dict - so don't populate
            # self, populate config_dict
            self.config_dict["conda_mapping_files"] = [self.local_conda_mapping_file, _default_mapping]

        if kwargs.get("conda_auto_init") is None:
            self.config_dict["conda_auto_init"] = running_from_source

        if self.container_resolvers_config_file:
            self.container_resolvers_config_file = self._in_config_dir(self.container_resolvers_config_file)

        # tool_dependency_dir can be "none" (in old configs). If so, set it to None
        if self.tool_dependency_dir and self.tool_dependency_dir.lower() == "none":
            self.tool_dependency_dir = None
        if self.mulled_channels:
            self.mulled_channels = [c.strip() for c in self.mulled_channels.split(",")]  # type: ignore[attr-defined]

        default_job_resubmission_condition = kwargs.get("default_job_resubmission_condition", "")
        if not default_job_resubmission_condition.strip():
            default_job_resubmission_condition = None
        self.default_job_resubmission_condition = default_job_resubmission_condition

        # Configuration options for taking advantage of nginx features
        if self.nginx_upload_store:
            self.nginx_upload_store = os.path.abspath(self.nginx_upload_store)

        if self.tus_upload_store:
            self.tus_upload_store = os.path.abspath(self.tus_upload_store)

        self.object_store = kwargs.get("object_store", "disk")
        self.object_store_check_old_style = string_as_bool(kwargs.get("object_store_check_old_style", False))
        self.object_store_cache_path = self._in_root_dir(
            kwargs.get("object_store_cache_path", self._in_data_dir("object_store_cache"))
        )
        self._configure_dataset_storage()

        # Handle AWS-specific config options for backward compatibility
        if kwargs.get("aws_access_key") is not None:
            self.os_access_key = kwargs.get("aws_access_key")
            self.os_secret_key = kwargs.get("aws_secret_key")
            self.os_bucket_name = kwargs.get("s3_bucket")
            self.os_use_reduced_redundancy = kwargs.get("use_reduced_redundancy", False)
        else:
            self.os_access_key = kwargs.get("os_access_key")
            self.os_secret_key = kwargs.get("os_secret_key")
            self.os_bucket_name = kwargs.get("os_bucket_name")
            self.os_use_reduced_redundancy = kwargs.get("os_use_reduced_redundancy", False)
        self.os_host = kwargs.get("os_host")
        self.os_port = kwargs.get("os_port")
        self.os_is_secure = string_as_bool(kwargs.get("os_is_secure", True))
        self.os_conn_path = kwargs.get("os_conn_path", "/")
        self.object_store_cache_size = float(kwargs.get("object_store_cache_size", -1))
        self.distributed_object_store_config_file = kwargs.get("distributed_object_store_config_file")
        if self.distributed_object_store_config_file is not None:
            self.distributed_object_store_config_file = self._in_root_dir(self.distributed_object_store_config_file)
        self.irods_root_collection_path = kwargs.get("irods_root_collection_path")
        self.irods_default_resource = kwargs.get("irods_default_resource")
        # Heartbeat log file name override
        if self.global_conf is not None and "heartbeat_log" in self.global_conf:
            self.heartbeat_log = self.global_conf["heartbeat_log"]
        # Determine which 'server:' this is
        self.server_name = "main"
        for arg in sys.argv:
            # Crummy, but PasteScript does not give you a way to determine this
            if arg.lower().startswith("--server-name="):
                self.server_name = arg.split("=", 1)[-1]
        # Allow explicit override of server name in config params
        if "server_name" in kwargs:
            self.server_name = kwargs["server_name"]
        # The application stack code may manipulate the server name. It also needs to be accessible via the get() method
        # for galaxy.util.facts()
        self.config_dict["base_server_name"] = self.base_server_name = self.server_name
        # Store all configured server names for the message queue routing
        self.server_names = []
        for section in self.global_conf_parser.sections():
            if section.startswith("server:"):
                self.server_names.append(section.replace("server:", "", 1))

        self._set_host_related_options(kwargs)

        # Asynchronous execution process pools - limited functionality for now, attach_to_pools is designed to allow
        # webless Galaxy server processes to attach to arbitrary message queues (e.g. as job handlers) so they do not
        # have to be explicitly defined as such in the job configuration.
        self.attach_to_pools = kwargs.get("attach_to_pools", []) or []

        # Store advanced job management config
        self.job_handlers = [x.strip() for x in kwargs.get("job_handlers", self.server_name).split(",")]
        self.default_job_handlers = [
            x.strip() for x in kwargs.get("default_job_handlers", ",".join(self.job_handlers)).split(",")
        ]
        # Galaxy internal control queue configuration.
        # If specified in universe, use it, otherwise we use whatever 'real'
        # database is specified.  Lastly, we create and use new sqlite database
        # (to minimize locking) as a final option.
        if "amqp_internal_connection" in kwargs:
            self.amqp_internal_connection = kwargs.get("amqp_internal_connection")
            # TODO Get extra amqp args as necessary for ssl
        elif "database_connection" in kwargs:
            self.amqp_internal_connection = f"sqlalchemy+{self.database_connection}"
        else:
            self.amqp_internal_connection = (
                f"sqlalchemy+sqlite:///{self._in_data_dir('control.sqlite')}?isolation_level=IMMEDIATE"
            )

        self._process_celery_config()

        # load in the chat_prompts if openai api key is configured
        if self.openai_api_key:
            self._load_chat_prompts()

        self.pretty_datetime_format = expand_pretty_datetime_format(self.pretty_datetime_format)
        try:
            with open(self.user_preferences_extra_conf_path) as stream:
                self.user_preferences_extra = yaml.safe_load(stream)
        except Exception:
            if self.is_set("user_preferences_extra_conf_path"):
                log.warning(
                    f"Config file ({self.user_preferences_extra_conf_path}) could not be found or is malformed."
                )
            self.user_preferences_extra = {"preferences": {}}

        # Experimental: This will not be enabled by default and will hide
        # nonproduction code.
        # The api_folders refers to whether the API exposes the /folders section.
        self.api_folders = string_as_bool(kwargs.get("api_folders", False))
        # This is for testing new library browsing capabilities.
        self.new_lib_browse = string_as_bool(kwargs.get("new_lib_browse", False))
        # Logging configuration with logging.config.configDict:
        # Statistics and profiling with statsd
        self.statsd_host = kwargs.get("statsd_host", "")

        self.proxy_session_map = self.dynamic_proxy_session_map
        self.manage_dynamic_proxy = self.dynamic_proxy_manage  # Set to false if being launched externally

        # Interactive tools proxy mapping
        if self.interactivetoolsproxy_map is None:
            self.interactivetools_map = "sqlite:///" + self._in_root_dir(
                kwargs.get("interactivetools_map", self._in_data_dir("interactivetools_map.sqlite"))
            )
        else:
            self.interactivetools_map = None  # overridden by `self.interactivetoolsproxy_map`

            # ensure the database URL for the SQLAlchemy map does not match that of a Galaxy DB
            urls = {
                setting: urlparse(value)
                for setting, value in (
                    ("interactivetoolsproxy_map", self.interactivetoolsproxy_map),
                    ("database_connection", self.database_connection),
                    ("install_database_connection", self.install_database_connection),
                )
                if value is not None
            }

            def is_in_conflict(url1, url2):
                return all(
                    (
                        url1.scheme == url2.scheme,
                        url1.hostname == url2.hostname,
                        url1.port == url2.port,
                        url1.path == url2.path,
                    )
                )

            conflicting_settings = {
                setting
                for setting, url in tuple(urls.items())[1:]  # exclude "interactivetoolsproxy_map"
                if is_in_conflict(url, list(urls.values())[0])  # compare with "interactivetoolsproxy_map"
            }

            if conflicting_settings:
                raise ConfigurationError(
                    f"Option `{tuple(urls)[0]}` cannot take the same value as: %s"
                    % ", ".join(f"`{setting}`" for setting in conflicting_settings)
                )

        # Compliance/Policy variables
        self.redact_username_during_deletion = False
        self.redact_email_during_deletion = False
        self.redact_ip_address = False
        self.redact_username_in_logs = False
        self.redact_email_in_job_name = False
        self.redact_user_details_in_bugreport = False
        self.redact_user_address_during_deletion = False
        # GDPR compliance mode changes values on a number of variables. Other
        # policies could change (non)overlapping subsets of these variables.
        if self.enable_beta_gdpr:
            self.expose_user_name = False
            self.expose_user_email = False

            self.redact_username_during_deletion = True
            self.redact_email_during_deletion = True
            self.redact_ip_address = True
            self.redact_username_in_logs = True
            self.redact_email_in_job_name = True
            self.redact_user_details_in_bugreport = True
            self.redact_user_address_during_deletion = True
            self.allow_user_deletion = True

            LOGGING_CONFIG_DEFAULT["formatters"]["brief"] = {
                "format": "%(asctime)s %(levelname)-8s %(name)-15s %(message)s"
            }
            LOGGING_CONFIG_DEFAULT["handlers"]["compliance_log"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "brief",
                "filename": "compliance.log",
                "backupCount": 0,
            }
            LOGGING_CONFIG_DEFAULT["loggers"]["COMPLIANCE"] = {
                "handlers": ["compliance_log"],
                "level": "DEBUG",
                "qualname": "COMPLIANCE",
            }

        log_destination = kwargs.get("log_destination")
        log_rotate_size = size_to_bytes(unicodify(kwargs.get("log_rotate_size", 0)))
        log_rotate_count = int(kwargs.get("log_rotate_count", 0))
        if log_destination == "stdout":
            LOGGING_CONFIG_DEFAULT["handlers"]["console"] = {
                "class": "logging.StreamHandler",
                "formatter": "stack",
                "level": "DEBUG",
                "stream": "ext://sys.stdout",
                "filters": ["stack"],
            }
        elif log_destination:
            LOGGING_CONFIG_DEFAULT["handlers"]["console"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "stack",
                "level": "DEBUG",
                "filename": log_destination,
                "filters": ["stack"],
                "maxBytes": log_rotate_size,
                "backupCount": log_rotate_count,
            }
        if galaxy_daemon_log_destination := os.environ.get("GALAXY_DAEMON_LOG"):
            LOGGING_CONFIG_DEFAULT["handlers"]["files"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "stack",
                "level": "DEBUG",
                "filename": galaxy_daemon_log_destination,
                "filters": ["stack"],
                "maxBytes": log_rotate_size,
                "backupCount": log_rotate_count,
            }
            LOGGING_CONFIG_DEFAULT["root"]["handlers"].append("files")

        # Load and flatten themes into css variables
        def _load_theme(path: str, theme_dict: dict):
            if self._path_exists(path):
                with open(path) as f:
                    themes = yaml.safe_load(f)
                    for key, val in themes.items():
                        theme_dict[key] = flatten_theme(val)

        self.themes = {}

        if "themes_config_file_by_host" in self.config_dict:
            self.themes_by_host = {}
            resolve_to_dir = self.schema.paths_to_resolve["themes_config_file"]
            resolve_dir_path = getattr(self, resolve_to_dir)
            for host, file_name in self.config_dict["themes_config_file_by_host"].items():
                self.themes_by_host[host] = {}
                file_path = self._in_dir(resolve_dir_path, file_name)
                _load_theme(file_path, self.themes_by_host[host])
        else:
            _load_theme(self.themes_config_file, self.themes)

        if self.file_source_temp_dir:
            self.file_source_temp_dir = os.path.abspath(self.file_source_temp_dir)

    def _load_chat_prompts(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        chat_prompts_path = os.path.join(current_dir, "chat_prompts.json")

        if os.path.exists(chat_prompts_path):
            try:
                with open(chat_prompts_path, encoding="utf-8") as file:
                    data = json.load(file)
                    self.chat_prompts = data.get("prompts", {})
            except json.JSONDecodeError as e:
                log.error(f"JSON decoding error in chat prompts file: {e}")
            except Exception as e:
                log.error(f"An error occurred while reading chat prompts file: {e}")
        else:
            log.warning(f"Chat prompts file not found at {chat_prompts_path}")

    def _process_celery_config(self):
        if self.celery_conf and self.celery_conf.get("result_backend") is None:
            # If the result_backend is not set, use a SQLite database in the data directory
            result_backend = f"db+sqlite:///{self._in_data_dir('results.sqlite')}?isolation_level=IMMEDIATE"
            self.celery_conf["result_backend"] = result_backend

    def _check_database_connection_strings(self):
        """
        Verify connection URI strings in galaxy's configuration are parseable with urllib.
        """

        def try_parsing(value, name):
            try:
                urlparse(value)
            except ValueError as e:
                msg = f"The `{name}` configuration property cannot be parsed as a connection URI."
                if "Invalid IPv6 URL" in str(e):
                    msg += (
                        "\nBesides an invalid IPv6 format, this may be caused by a bracket character in the `netloc` part of "
                        "the URI (most likely, the password). In this case, you should percent-encode that character: for `[` "
                        "use `%5B`, for `]` use `%5D`. For example, if your URI is `postgresql://user:pass[word@host/db`, "
                        "change it to `postgresql://user:pass%5Bword@host/db`. "
                    )
                raise ConfigurationError(msg) from e

        try_parsing(self.database_connection, "database_connection")
        try_parsing(self.install_database_connection, "install_database_connection")
        if self.interactivetoolsproxy_map is not None:
            try_parsing(self.interactivetoolsproxy_map, "interactivetoolsproxy_map")
        try_parsing(self.amqp_internal_connection, "amqp_internal_connection")

    def _configure_dataset_storage(self):
        # The default for `file_path` has changed in 20.05; we may need to fall back to the old default
        self._set_alt_paths("file_path", self._in_data_dir("files"))  # this is called BEFORE guessing id/uuid
        ID, UUID = "id", "uuid"
        if self.is_set("object_store_store_by"):
            if self.object_store_store_by not in [ID, UUID]:
                raise Exception(f"Invalid value for object_store_store_by [{self.object_store_store_by}]")
        elif os.path.basename(self.file_path) == "objects":
            self.object_store_store_by = UUID
        else:
            self.object_store_store_by = ID

    def _load_list_from_file(self, filepath):
        with open(filepath) as f:
            return [line.strip() for line in f]

    def _set_host_related_options(self, kwargs):
        # The following 3 method calls must be made in sequence
        self._set_galaxy_infrastructure_url(kwargs)
        self._set_hostname()
        self._set_email_from()

    def _set_galaxy_infrastructure_url(self, kwargs):
        # indicate if this was not set explicitly, so dependending on the context a better default
        # can be used (request url in a web thread, Docker parent in IE stuff, etc.)
        self.galaxy_infrastructure_url_set = kwargs.get("galaxy_infrastructure_url") is not None
        if "HOST_IP" in self.galaxy_infrastructure_url:
            self.galaxy_infrastructure_url = string.Template(self.galaxy_infrastructure_url).safe_substitute(
                {"HOST_IP": socket.gethostbyname(socket.gethostname())}
            )
        if "GALAXY_WEB_PORT" in self.galaxy_infrastructure_url:
            port = os.environ.get("GALAXY_WEB_PORT")
            if not port:
                raise Exception("$GALAXY_WEB_PORT set in galaxy_infrastructure_url, but environment variable not set")
            self.galaxy_infrastructure_url = string.Template(self.galaxy_infrastructure_url).safe_substitute(
                {"GALAXY_WEB_PORT": port}
            )
        if "UWSGI_PORT" in self.galaxy_infrastructure_url:
            raise Exception("UWSGI_PORT is not supported anymore")

    def _set_hostname(self):
        if self.galaxy_infrastructure_url_set:
            self.hostname = urlparse(self.galaxy_infrastructure_url).hostname
        else:
            self.hostname = socket.getfqdn()

    def _set_email_from(self):
        if not self.email_from:
            self.email_from = f"{DEFAULT_EMAIL_FROM_LOCAL_PART}@{self.hostname}"

    def reload_sanitize_allowlist(self, explicit=True):
        self.sanitize_allowlist = []
        if not os.path.exists(self.sanitize_allowlist_file):
            if explicit:
                log.warning(
                    "Sanitize log file explicitly specified as '%s' but does not exist, continuing with no tools allowlisted.",
                    self.sanitize_allowlist_file,
                )
        else:
            with open(self.sanitize_allowlist_file) as f:
                self.sanitize_allowlist = sorted(
                    line.strip() for line in f.readlines() if line.strip() and not line.startswith("#")
                )

    def ensure_tempdir(self):
        self._ensure_directory(self.new_file_path)

    def check(self):
        # Check that required directories exist; attempt to create otherwise
        paths_to_check = [
            self.data_dir,
            self.ftp_upload_dir,
            self.library_import_dir,
            self.managed_config_dir,
            self.new_file_path,
            self.nginx_upload_store,
            self.tus_upload_store,
            self.object_store_cache_path,
            self.template_cache_path,
            self.tool_data_path,
            self.user_library_import_dir,
            self.file_source_temp_dir,
        ]
        for path in paths_to_check:
            self._ensure_directory(path)
        # Check that required files exist
        tool_configs = self.tool_configs
        for path in tool_configs:
            if not os.path.exists(path) and path not in (self.shed_tool_config_file, self.migrated_tools_config):
                raise ConfigurationError(f"Tool config file not found: {path}")
        for datatypes_config in listify(self.datatypes_config):
            if not os.path.isfile(datatypes_config):
                raise ConfigurationError(f"Datatypes config file not found: {datatypes_config}")
        # Check for deprecated options.
        for key in self.config_dict.keys():
            if key in self.deprecated_options:
                log.warning(
                    f"Config option '{key}' is deprecated and will be removed in a future release.  Please consult the latest version of the sample configuration file."
                )

    def is_fetch_with_celery_enabled(self):
        """
        True iff celery is enabled and celery_conf["task_routes"]["galaxy.fetch_data"] != DISABLED_FLAG.
        """
        celery_enabled = self.enable_celery_tasks
        try:
            fetch_disabled = self.celery_conf["task_routes"]["galaxy.fetch_data"] == DISABLED_FLAG
        except (TypeError, KeyError):  # celery_conf is None or sub-dictionary is none or either key is not present
            fetch_disabled = False
        return celery_enabled and not fetch_disabled

    @staticmethod
    def _parse_allowed_origin_hostnames(allowed_origin_hostnames):
        """
        Parse a CSV list of strings/regexp of hostnames that should be allowed
        to use CORS and will be sent the Access-Control-Allow-Origin header.
        """
        allowed_origin_hostnames_list = listify(allowed_origin_hostnames)
        if not allowed_origin_hostnames_list:
            return None

        def parse(string):
            # a string enclosed in fwd slashes will be parsed as a regexp: e.g. /<some val>/
            if string[0] == "/" and string[-1] == "/":
                string = string[1:-1]
                return re.compile(string, flags=(re.UNICODE))
            return string

        return [parse(v) for v in allowed_origin_hostnames_list if v]


# legacy naming
Configuration = GalaxyAppConfiguration


def reload_config_options(current_config):
    """Reload modified reloadable config options."""
    modified_config = read_properties_from_file(current_config.config_file)
    for option in current_config.schema.reloadable_options:
        if option in modified_config:
            # compare to raw value, as that one is set only on load and reload
            if current_config._raw_config[option] != modified_config[option]:
                current_config._raw_config[option] = modified_config[option]
                setattr(current_config, option, modified_config[option])
                log.info(f"Reloaded {option}")


def get_database_engine_options(kwargs, model_prefix=""):
    """
    Allow options for the SQLAlchemy database engine to be passed by using
    the prefix "database_engine_option".
    """
    conversions: Dict[str, Callable[[Any], Union[bool, int]]] = {
        "convert_unicode": string_as_bool,
        "pool_timeout": int,
        "echo": string_as_bool,
        "echo_pool": string_as_bool,
        "pool_recycle": int,
        "pool_size": int,
        "max_overflow": int,
        "pool_threadlocal": string_as_bool,
        "server_side_cursors": string_as_bool,
    }
    prefix = f"{model_prefix}database_engine_option_"
    prefix_len = len(prefix)
    rval = {}
    for key, value in kwargs.items():
        if key.startswith(prefix):
            key = key[prefix_len:]
            if key in conversions:
                value = conversions[key](value)
            rval[key] = value
    return rval
