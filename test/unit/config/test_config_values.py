import os
from collections import namedtuple
from datetime import timedelta
from unittest.mock import patch

import pytest

from galaxy import config
from galaxy.util import listify
from galaxy.web.formatting import expand_pretty_datetime_format

TestData = namedtuple('TestData', ('key', 'expected', 'loaded'))


DO_NOT_TEST = {
    'datatypes_config_file',        # fix schema; parse_config_files
    'tool_config_file',             # fix schema; parse_config_files
    'tool_data_table_config_path',  # fix schema; parse_config_files
    'job_config_file',              # TODO: remove after applying recent schema commits
    'data_manager_config_file',     # TODO: remove after applying recent schema commits
}


@pytest.fixture(scope='module')
def appconfig():
    return config.GalaxyAppConfiguration()


@pytest.fixture
def mock_config_file(monkeypatch):
    # Patch this; otherwise tempfile.tempdir will be set, which is a global variable that
    # defines the value of the default `dir` argument to the functions in Python's
    # tempfile module - which breaks multiple tests.
    monkeypatch.setattr(config.GalaxyAppConfiguration, '_override_tempdir', lambda a, b: None)
    # Set this to return None to force the creation of base config directories
    # in _set_config_directories(). Used to test the values of these directories only.
    monkeypatch.setattr(config, 'find_config_file', lambda x: None)


def test_root(appconfig):
    assert appconfig.root == os.path.abspath('.')


def test_common_base_config(appconfig):
    assert appconfig.shed_tools_dir == os.path.join(appconfig.data_dir, 'shed_tools')
    assert appconfig.sample_config_dir == os.path.join(appconfig.root, 'lib', 'galaxy', 'config', 'sample')


def test_base_config_if_running_from_source(monkeypatch, mock_config_file):
    # Simulated condition: running from source, config_file is None.
    monkeypatch.setattr(config, 'running_from_source', True)
    appconfig = config.GalaxyAppConfiguration()
    assert not appconfig.config_file
    assert appconfig.config_dir == os.path.join(appconfig.root, 'config')
    assert appconfig.data_dir == os.path.join(appconfig.root, 'database')
    assert appconfig.managed_config_dir == appconfig.config_dir


def test_base_config_if_running_not_from_source(monkeypatch, mock_config_file):
    # Simulated condition: running not from source, config_file is None.
    monkeypatch.setattr(config, 'running_from_source', False)
    appconfig = config.GalaxyAppConfiguration()
    assert not appconfig.config_file
    assert appconfig.config_dir == os.getcwd()
    assert appconfig.data_dir == os.path.join(appconfig.config_dir, 'data')
    assert appconfig.managed_config_dir == os.path.join(appconfig.data_dir, 'config')


def listify_strip(value):
    return listify(value, do_strip=True)


class ExpectedValuesProvider:
    """
    The purpose of this class is to calculate expected values for config options
    based on their key, default value, set value (default is overwritten if the
    value is set), and any processing logic specified in the schema or the
    config module. For example, a path may be resolved with respect to a parent
    directory specified in the schema (via `path_resolves_to`), or a function
    may be applied to the value (e.g., `listify` in the config module).
    """
    def __init__(self, appconfig):
        self.schema_defaults = appconfig.schema.defaults
        self._root_dir = appconfig.root
        self._config_dir = appconfig.config_dir
        self._data_dir = appconfig.data_dir
        self._managed_config_dir = appconfig.managed_config_dir
        self._sample_config_dir = appconfig.sample_config_dir
        self._tool_data_path = appconfig.tool_data_path
        self._load_resolvers()

    def _load_resolvers(self):
        """
        A resolver is used to transform an initial value to the final expected
        value. A resolver can be (1) a constant, (2) a callable that takes
        one argument, (3) a callable that takes 2 arguments. A key can be
        mapped to one resolver at most.
        """
        def load_constants():
            """Dictionary mapping keys to constants."""
            self._resolvers_constants = {
                'disable_library_comptypes': [''],  # TODO: we can do better
                'object_store_store_by': 'uuid',
                'statsd_host': '',  # TODO: do we need '' as the default?
                'use_remote_user': None,  # TODO: should be False (config logic incorrect)
            }

        def load_callables_one_arg():
            """
            Dictionary mapping keys to callables that take one argument: the value to be resolved.
            """
            self._resolvers_callables = {
                'admin_tool_recommendations_path': self._in_config_dir,
                #'allowed_origin_hostnames': config.GalaxyAppConfiguration._parse_allowed_origin_hostnames,  #TODO
                'amqp_internal_connection': self._resolve_amqp_internal_connection,
                'auth_config_file': self._in_config_dir,
                'builds_file_path': self._in_tool_data_dir,
                'citation_cache_data_dir': self._in_data_dir,
                'citation_cache_lock_dir': self._in_data_dir,
                'cluster_files_directory': self._in_data_dir,
                'config_dir': self._resolve_config_dir,
                'data_dir': self._resolve_data_dir,
                'data_manager_config_file': self._in_config_dir,
                'database_connection': self._resolve_database_connection,
                'dependency_resolvers_config_file': self._in_config_dir,
                'dynamic_proxy_session_map': self._in_data_dir,
                'file_path': self._in_data_dir,
                'file_sources_config_file': self._in_config_dir,
                'ftp_upload_dir_template': self._resolve_ftp_upload_dir_template,
                'galaxy_data_manager_data_path': self._resolve_galaxy_data_manager_data_path,
                'integrated_tool_panel_config': self._in_managed_config_dir,
                'interactivetools_map': self._in_data_dir,
                'involucro_path': self._in_root_dir,
                'job_config_file': self._in_config_dir,
                'job_resource_params_file': self._in_config_dir,
                'len_file_path': self._in_tool_data_dir,
                'managed_config_dir': self._resolve_managed_config_dir,
                'markdown_export_css': self._in_config_dir,
                'markdown_export_css_invocation_reports': self._in_config_dir,
                'markdown_export_css_pages': self._in_config_dir,
                'migrated_tools_config': self._in_managed_config_dir,
                'mulled_channels': listify_strip,
                'mulled_resolution_cache_data_dir': self._in_data_dir,
                'mulled_resolution_cache_lock_dir': self._in_data_dir,
                'new_file_path': self._in_data_dir,
                'object_store_config_file': self._in_config_dir,
                'oidc_backends_config_file': self._in_config_dir,
                'oidc_config_file': self._in_config_dir,
                'openid_consumer_cache_path': self._in_data_dir,
                'password_expiration_period': timedelta,
                'persistent_communication_rooms': listify_strip,
                'pretty_datetime_format': expand_pretty_datetime_format,
                'sanitize_allowlist_file': self._in_managed_config_dir,
                'shed_data_manager_config_file': self._in_managed_config_dir,
                'shed_tool_config_file': self._in_managed_config_dir,
                'shed_tool_data_path': self._resolve_shed_tool_data_path,
                'shed_tool_data_table_config': self._in_managed_config_dir,
                'template_cache_path': self._in_data_dir,
                'tool_cache_data_dir': self._in_data_dir,
                'tool_data_path': self._in_root_dir,
                'tool_filters': listify_strip,
                'tool_label_filters': listify_strip,
                'tool_path': self._in_root_dir,
                'tool_search_index_dir': self._in_data_dir,
                'tool_section_filters': listify_strip,
                'tool_sheds_config_file': self._in_config_dir,
                'tool_test_data_directories': self._in_root_dir,
                'toolbox_filter_base_modules': listify_strip,
                'trs_servers_config_file': self._in_config_dir,
                'user_library_import_symlink_allowlist': listify_strip,
                'user_preferences_extra_conf_path': self._in_config_dir,
                'user_tool_filters': listify_strip,
                'user_tool_label_filters': listify_strip,
                'user_tool_section_filters': listify_strip,
                'workflow_resource_params_mapper': self._resolve_workflow_resource_params_mapper,
                'workflow_resource_params_file': self._in_config_dir,
                'workflow_schedulers_config_file': self._in_config_dir,
            }

        def load_callables_two_args():
            """
            Dictionary mapping keys to callables that take two arguments: (1) the value
            to be resolved, and (2) the schema default.
            """
            self._resolvers_callables_two_args = {
                'build_sites_config_file': self._in_config_or_sample_dir,
                'job_metrics_config_file': self._in_config_or_sample_dir,
            }

        def ensure_one_resolver_per_key():
            a = set(self._resolvers_constants)
            b = set(self._resolvers_callables)
            c = set(self._resolvers_callables_two_args)
            if a & b or b & c or a & c:
                raise Exception('A key can be mapped to one resolver at most')

        load_constants()
        load_callables_one_arg()
        load_callables_two_args()
        ensure_one_resolver_per_key()

    def _in_root_dir(self, path=None):
        return self._in_dir(self._root_dir, path)

    def _in_config_dir(self, path=None):
        return self._in_dir(self._config_dir, path)

    def _in_data_dir(self, path=None):
        return self._in_dir(self._data_dir, path)

    def _in_managed_config_dir(self, path=None):
        return self._in_dir(self._managed_config_dir, path)

    def _in_tool_data_dir(self, path=None):
        return self._in_dir(self._tool_data_path, path)

    def _in_config_or_sample_dir(self, set_path, default_path):
        if set_path:
            return self._in_dir(self._config_dir, set_path)
        else:
            path = '%s.sample' % default_path
            return self._in_dir(self._sample_config_dir, path)

    def _in_dir(self, _dir, path):
        return os.path.join(_dir, path) if path else _dir

    def _resolve_config_dir(self, path=None):
        if path:
            return self._in_root_dir(path)
        return self._config_dir

    def _resolve_data_dir(self, path=None):
        if path:
            return self._in_root_dir(path)
        return self._data_dir

    def _resolve_managed_config_dir(self, path=None):
        if path:
            return self._in_root_dir(path)
        return self._managed_config_dir

    def _resolve_galaxy_data_manager_data_path(self, path=None):
        return path or self._tool_data_path

    def _resolve_database_connection(self, value):
        return 'sqlite:///{}/universe.sqlite?isolation_level=IMMEDIATE'.format(self._data_dir)

    def _resolve_ftp_upload_dir_template(self, value):
        return '${ftp_upload_dir}%s${ftp_upload_dir_identifier}' % os.path.sep

    def _resolve_amqp_internal_connection(self, value):
        return 'sqlalchemy+sqlite:///{}/control.sqlite?isolation_level=IMMEDIATE'.format(self._data_dir)

    def _resolve_shed_tool_data_path(self, path=None):
        if path:
            return self._in_root_dir(path)
        return self._tool_data_path

    def _resolve_workflow_resource_params_mapper(self, value=None):
        if value:
            return self._in_root_dir(value)
        return None

    def get_expected_value(self, key, set_value=None):
        default_value = self.schema_defaults.get(key)
        # If value not set, use schema default
        value = default_value
        if set_value is not None:  # value can be falsy, so compare to None
            value = set_value
        # Use resolver if one exists; otherwise return value unchanged
        if key in self._resolvers_constants:
            return self._resolvers_constants[key]
        elif key in self._resolvers_callables:
            return self._resolvers_callables[key](value)
        elif key in self._resolvers_callables_two_args:
            f = self._resolvers_callables_two_args[key]
            return f(set_value, default_value)
        else:
            return value


def get_test_data_with_default_values():
    """GalaxyAppConfiguration loaded with schema defaults."""
    appconfig = config.GalaxyAppConfiguration()
    evp = ExpectedValuesProvider(appconfig)
    for key, data in appconfig.schema.app_schema.items():
        if key not in DO_NOT_TEST:
            expected_value = evp.get_expected_value(key)
            loaded_value = getattr(appconfig, key)
            test_data = TestData(key, expected_value, loaded_value)
            yield pytest.param(test_data)


def get_key(test_data):
    return test_data.key


@pytest.mark.parametrize('test_data', get_test_data_with_default_values(), ids=get_key)
def test_default_config(test_data):
    assert test_data.expected == test_data.loaded
