import os
from collections import namedtuple
from datetime import timedelta

import pytest

from galaxy import config
from galaxy.config import expand_pretty_datetime_format
from galaxy.util import listify
from galaxy.util.properties import running_from_source

TestData = namedtuple("TestData", ("key", "expected", "loaded"))


@pytest.fixture(scope="module")
def appconfig():
    return config.GalaxyAppConfiguration(override_tempdir=False)


@pytest.fixture
def mock_config_file(monkeypatch):
    # Set this to return None to force the creation of base config directories
    # in _set_config_directories(). Used to test the values of these directories only.
    monkeypatch.setattr(config, "find_config_file", lambda x: None)


def test_root(appconfig):
    assert appconfig.root == os.path.abspath(".")


def test_common_base_config(appconfig):
    assert appconfig.shed_tools_dir == os.path.join(appconfig.data_dir, "shed_tools")
    if running_from_source:
        expected_path = os.path.join(appconfig.root, "lib", "galaxy", "config", "sample")
    else:
        expected_path = os.path.join(appconfig.root, "galaxy", "config", "sample")
    assert appconfig.sample_config_dir == expected_path


def test_base_config_if_running_from_source(monkeypatch, mock_config_file):
    # Simulated condition: running from source, config_file is None.
    monkeypatch.setattr(config, "running_from_source", True)
    appconfig = config.GalaxyAppConfiguration(override_tempdir=False)
    assert not appconfig.config_file
    assert appconfig.config_dir == os.path.join(appconfig.root, "config")
    assert appconfig.data_dir == os.path.join(appconfig.root, "database")
    assert appconfig.managed_config_dir == appconfig.config_dir


def test_base_config_if_running_not_from_source(monkeypatch, mock_config_file):
    # Simulated condition: running not from source, config_file is None.
    monkeypatch.setattr(config, "running_from_source", False)
    appconfig = config.GalaxyAppConfiguration(override_tempdir=False)
    assert not appconfig.config_file
    assert appconfig.config_dir == os.getcwd()
    assert appconfig.data_dir == os.path.join(appconfig.config_dir, "data")
    assert appconfig.managed_config_dir == os.path.join(appconfig.data_dir, "config")


def listify_strip(value):
    return listify(value, do_strip=True)


class ExpectedValues:
    def __init__(self, config):
        self._config = config
        self._load_resolvers()
        self._load_paths()

    def _load_resolvers(self):
        self._resolvers = {
            "amqp_internal_connection": self.get_expected_amqp_internal_connection,
            "database_connection": self.get_expected_database_connection,
            "disable_library_comptypes": [""],  # TODO: we can do better
            "file_path": self.get_expected_file_path,
            "ftp_upload_dir_template": self.get_expected_ftp_upload_dir_template,
            "mulled_channels": listify_strip,
            "object_store_store_by": self.get_expected_object_store_store_by,
            "password_expiration_period": timedelta,
            "pretty_datetime_format": expand_pretty_datetime_format,
            "statsd_host": "",  # TODO: do we need '' as the default?
            "tool_config_file": listify_strip,
            "tool_data_table_config_path": listify_strip,
            "tool_filters": listify_strip,
            "tool_label_filters": listify_strip,
            "tool_section_filters": listify_strip,
            "toolbox_filter_base_modules": listify_strip,
            "use_remote_user": None,  # TODO: should be False (config logic incorrect)
            "user_library_import_symlink_allowlist": listify_strip,
            "user_tool_filters": listify_strip,
            "user_tool_label_filters": listify_strip,
            "user_tool_section_filters": listify_strip,
        }
        # _resolvers provides expected values for config options.
        # - key: config option
        # - value: expected value or a callable. The callable will be called with a
        #   single argument, which is the default value of the config option.

    def _load_paths(self):
        self._expected_paths = {
            "admin_tool_recommendations_path": self._in_config_dir("tool_recommendations_overwrite.yml"),
            "auth_config_file": self._in_config_dir("auth_conf.xml"),
            "biotools_service_cache_data_dir": self._in_cache_dir("biotools/data"),
            "biotools_service_cache_lock_dir": self._in_cache_dir("biotools/locks"),
            "build_sites_config_file": self._in_sample_dir("build_sites.yml.sample"),
            "builds_file_path": self._in_root_or_data_dir("tool-data/shared/ucsc/builds.txt"),
            "cache_dir": self._in_data_dir("cache"),
            "citation_cache_data_dir": self._in_cache_dir("citations/data"),
            "citation_cache_lock_dir": self._in_cache_dir("citations/locks"),
            "cluster_files_directory": self._in_data_dir("pbs"),
            "config_dir": self._in_config_dir(),
            "data_dir": self._in_data_dir(),
            "data_manager_config_file": self._in_config_dir("data_manager_conf.xml"),
            "datatypes_config_file": self._in_sample_dir("datatypes_conf.xml.sample"),
            "dependency_resolvers_config_file": self._in_config_dir("dependency_resolvers_conf.xml"),
            "dynamic_proxy_session_map": self._in_data_dir("session_map.sqlite"),
            "edam_toolbox_ontology_path": self._in_data_dir("EDAM.tsv"),
            "error_report_file": self._in_config_dir("error_report.yml"),
            "file_sources_config_file": self._in_config_dir("file_sources_conf.yml"),
            "galaxy_data_manager_data_path": self._in_root_or_data_dir("tool-data"),
            "integrated_tool_panel_config": self._in_managed_config_dir("integrated_tool_panel.xml"),
            "interactivetools_map": self._in_data_dir("interactivetools_map.sqlite"),
            "involucro_path": self._in_root_dir("involucro"),
            "job_config_file": self._in_config_dir("job_conf.xml"),
            "job_metrics_config_file": self._in_sample_dir("job_metrics_conf.xml.sample"),
            "job_resource_params_file": self._in_config_dir("job_resource_params_conf.xml"),
            "len_file_path": self._in_root_or_data_dir("tool-data/shared/ucsc/chrom"),
            "local_conda_mapping_file": self._in_config_dir("local_conda_mapping.yml"),
            "managed_config_dir": self._in_managed_config_dir(),
            "markdown_export_css": self._in_config_dir("markdown_export.css"),
            "markdown_export_css_invocation_reports": self._in_config_dir("markdown_export_invocation_reports.css"),
            "markdown_export_css_pages": self._in_config_dir("markdown_export_pages.css"),
            "migrated_tools_config": self._in_managed_config_dir("migrated_tools_conf.xml"),
            "modules_mapping_files": self._in_config_dir("environment_modules_mapping.yml"),
            "mulled_resolution_cache_data_dir": self._in_cache_dir("mulled/data"),
            "mulled_resolution_cache_lock_dir": self._in_cache_dir("mulled/locks"),
            "new_file_path": self._in_data_dir("tmp"),
            "object_store_config_file": self._in_config_dir("object_store_conf.xml"),
            "oidc_backends_config_file": self._in_config_dir("oidc_backends_config.xml"),
            "oidc_config_file": self._in_config_dir("oidc_config.xml"),
            "sanitize_allowlist_file": self._in_managed_config_dir("sanitize_allowlist.txt"),
            "shed_data_manager_config_file": self._in_managed_config_dir("shed_data_manager_conf.xml"),
            "shed_tool_config_file": self._in_managed_config_dir("shed_tool_conf.xml"),
            "shed_tool_data_path": self._in_root_or_data_dir("tool-data"),
            "shed_tool_data_table_config": self._in_managed_config_dir("shed_tool_data_table_conf.xml"),
            "short_term_storage_dir": self._in_cache_dir("short_term_web_storage"),
            "template_cache_path": self._in_cache_dir("compiled_templates"),
            "tool_cache_data_dir": self._in_cache_dir("tool_cache"),
            "tool_config_file": self._in_sample_dir("tool_conf.xml.sample"),
            "tool_data_path": self._in_root_or_data_dir("tool-data"),
            "tool_data_table_config_path": self._in_sample_dir("tool_data_table_conf.xml.sample"),
            "tool_destinations_config_file": self._in_config_dir("tool_destinations.yml"),
            "tool_path": self._in_root_dir("tools"),
            "tool_search_index_dir": self._in_data_dir("tool_search_index"),
            "tool_sheds_config_file": self._in_config_dir("tool_sheds_conf.xml"),
            "tool_test_data_directories": self._in_root_dir("test-data"),
            "trs_servers_config_file": self._in_config_dir("trs_servers_conf.yml"),
            "user_preferences_extra_conf_path": self._in_config_dir("user_preferences_extra_conf.yml"),
            "vault_config_file": self._in_config_dir("vault_conf.yml"),
            "workflow_resource_params_file": self._in_config_dir("workflow_resource_params_conf.xml"),
            "workflow_schedulers_config_file": self._in_config_dir("workflow_schedulers_conf.xml"),
        }
        # _expected_paths provides expected values for config options that are paths. Each value is
        # wrapped in a function that ensures that the path (a) is resolved w.r.t. its parent as per
        # schema and/or config module; and (b) is an absolute path. The base config paths used by
        # each function are tested separately (see tests of base config properties in this module).
        # The values are hardcoded intentionally for the sake of keeping the test readable and
        # simple. They correspond to schema defaults, and should be adjusted if the schema is
        # modified.

    def _in_root_dir(self, path=None):
        return self._in_dir(self._config.root, path)

    def _in_root_or_data_dir(self, path):
        if running_from_source:
            return self._in_root_dir(path)
        else:
            return self._in_data_dir(path)

    def _in_config_dir(self, path=None):
        return self._in_dir(self._config.config_dir, path)

    def _in_cache_dir(self, path=None):
        return self._in_dir(self._config.cache_dir, path)

    def _in_data_dir(self, path=None):
        return self._in_dir(self._config.data_dir, path)

    def _in_managed_config_dir(self, path=None):
        return self._in_dir(self._config.managed_config_dir, path)

    def _in_sample_dir(self, path=None):
        return self._in_dir(self._config.sample_config_dir, path)

    def _in_dir(self, _dir, path):
        return os.path.join(_dir, path) if path else _dir

    def get_value(self, key, data):
        value = data.get("default")
        # 1. If this is a path, resolve it
        if key in self._expected_paths:
            value = self._expected_paths[key]
        # 2. AFTER resolving paths, apply resolver, if one exists
        if key in self._resolvers:
            resolver = self._resolvers[key]
            if callable(resolver):
                value = resolver(value)
            else:
                value = resolver
        return value

    def get_expected_database_connection(self, value):
        return f"sqlite:///{self._config.data_dir}/universe.sqlite?isolation_level=IMMEDIATE"

    def get_expected_ftp_upload_dir_template(self, value):
        return "${ftp_upload_dir}%s${ftp_upload_dir_identifier}" % os.path.sep

    def get_expected_amqp_internal_connection(self, value):
        return f"sqlalchemy+sqlite:///{self._config.data_dir}/control.sqlite?isolation_level=IMMEDIATE"

    def get_expected_file_path(self, value):
        for dir in ("files", "objects"):
            dir_path = self._in_data_dir(dir)
            if os.path.exists(dir_path):
                return dir_path
        return dir_path

    def get_expected_object_store_store_by(self, value):
        if os.path.exists(self._in_data_dir("files")):
            return "id"
        return "uuid"


def get_config_data():
    configuration = config.GalaxyAppConfiguration(override_tempdir=False)
    ev = ExpectedValues(configuration)
    items = ((k, v) for k, v in configuration.schema.app_schema.items())
    for key, data in items:
        expected = ev.get_value(key, data)
        loaded = getattr(configuration, key)
        test_data = TestData(key=key, expected=expected, loaded=loaded)
        yield pytest.param(test_data)


def get_key(test_data):
    return test_data.key


@pytest.mark.parametrize("test_data", get_config_data(), ids=get_key)
def test_config_defaults(test_data):
    assert (
        test_data.expected == test_data.loaded
    ), f"Default value of option [{test_data.key}] is [{test_data.loaded}] instead of expected [{test_data.expected}]"
