"""
This tests: (1) automatic creation of configuration properties; and
(2) assignment of default values that are specified in the schema and, in
some cases, are also processed at load time (paths resolved, csv strings
converted to lists, etc).

This module will test ALL schema properties, unless they are listed in the
global DO_NOT_TEST. Whenever a property's default value is changed (edits to
schema or configuration loading procedures), this test code must be modified to
reflect that change.

Test assumptions for a default configuration:
- If a default is set and not modified at load time, expect schema default.
- If a default is not set, expect null.
- If a default is set and modified at load time, the test should reflect that
  (if a default is specified in the schema, it is expected that it will be used
  in some form at load time; otherwise it should not be listed as a default).

Configuration options NOT tested:
- config_dir (value overridden for testing)
- data_dir (value overridden for testing)
- managed_config_dir (value depends on config_dir: see note above)
- new_file_path (value overridden for testing)
- logging (mapping loaded in config/; TODO)
- dependency_resolution (nested properties; TODO)
- job_config (no obvious testable defaults)
"""

import os
from collections import namedtuple
from datetime import timedelta

import pytest

from galaxy.util import listify
from galaxy_test.driver.driver_util import GalaxyTestDriver

OptionData = namedtuple("OptionData", ("key", "expected", "loaded"))

driver_created = False

# Configuration properties that are paths should be absolute paths, by default resolved w.r.t root.
PATH_CONFIG_PROPERTIES = [
    # For now, these include base config properties
    "root",
    "config_file",
    "config_dir",
    "managed_config_dir",
    "cache_dir",
    "data_dir",
    "auth_config_file",
    "email_domain_blocklist_file",
    "builds_file_path",
    "citation_cache_data_dir",
    "citation_cache_lock_dir",
    "cluster_files_directory",
    "container_resolvers_config_file",
    "data_manager_config_file",
    "datatypes_config_file",
    "dependency_resolvers_config_file",
    "file_path",
    "file_sources_config_file",
    "ftp_upload_dir",
    "galaxy_data_manager_data_path",
    "integrated_tool_panel_config",
    "involucro_path",
    "job_config_file",
    "job_resource_params_file",
    "job_working_directory",
    "len_file_path",
    "library_import_dir",
    "markdown_export_css",
    "markdown_export_css_pages",
    "markdown_export_css_invocation_reports",
    "migrated_tools_config",
    "new_file_path",
    "nginx_upload_job_files_path",
    "nginx_upload_job_files_store",
    "nginx_upload_path",
    "object_store_config_file",
    "oidc_backends_config_file",
    "oidc_config_file",
    "sanitize_allowlist_file",
    "shed_data_manager_config_file",
    "shed_tool_config_file",
    "shed_tool_data_path",
    "shed_tool_data_table_config",
    "short_term_storage_dir",
    "template_cache_path",
    "tool_data_path",
    "tool_dependency_cache_dir",
    "tool_path",
    "tool_sheds_config_file",
    "trs_servers_config_file",
    "user_preferences_extra_conf_path",
    "vault_config_file",
    "webhooks_dir",
    "workflow_resource_params_file",
    "workflow_resource_params_mapper",
    "workflow_schedulers_config_file",
]
# TODO: fix or mark as not absolute (2 are lists):
# - 'tool_config_file',
# - 'tool_data_table_config_path',
# - 'tool_dependency_dir',
# - 'tool_test_data_directories',
# - 'tour_config_dir',
# - 'visualization_plugins_directory',


# Most of these (except root_dir) will go away once path_resolves_to is set in the schema
RESOLVE = {
    "auth_config_file": "config_dir",
    "builds_file_path": "tool_data_path",
    "dependency_resolvers_config_file": "config_dir",
    "integrated_tool_panel_config": "managed_config_dir",
    "involucro_path": "root_dir",
    "file_sources_config_file": "config_dir",
    "job_resource_params_file": "config_dir",
    "len_file_path": "tool_data_path",
    "object_store_config_file": "config_dir",
    "oidc_backends_config_file": "config_dir",
    "oidc_config_file": "config_dir",
    "trs_servers_config_file": "config_dir",
    "sanitize_allowlist_file": "managed_config_dir",
    "shed_data_manager_config_file": "managed_config_dir",
    "shed_tool_config_file": "managed_config_dir",
    "shed_tool_data_path": "tool_data_path",
    "shed_tool_data_table_config": "managed_config_dir",
    "tool_data_path": "root_dir",
    "tool_path": "root_dir",
    "tool_sheds_config_file": "config_dir",
    "user_preferences_extra_conf_path": "config_dir",
    "vault_config_file": "config_dir",
    "workflow_resource_params_file": "config_dir",
    "workflow_schedulers_config_file": "config_dir",
}


def expected_default_config_dir(value):
    # expected absolute path to the default config dir (when NO galaxy.yml provided)
    return os.path.join(DRIVER.app.config.root, "lib", "galaxy", "config", "sample")


CUSTOM = {
    "config_dir": expected_default_config_dir,
    "password_expiration_period": timedelta,
    "toolbox_filter_base_modules": listify,
    "mulled_channels": listify,
    "user_library_import_symlink_allowlist": listify,
    "tool_filters": listify,
    "tool_label_filters": listify,
    "tool_section_filters": listify,
}


# TODO: split into (1) do not test; and (2) todo: fix and test
DO_NOT_TEST = [
    "admin_users",  # may or may not be testable: special test value assigned
    "allow_user_deletion",  # broken: default overridden
    "amqp_internal_connection",  # may or may not be testable; refactor config/
    "api_allow_run_as",  # may or may not be testable: test value assigned
    "build_sites_config_file",  # broken: remove 'config/' prefix from schema
    "chunk_upload_size",  # broken: default overridden
    "cleanup_job",  # broken: default overridden
    "conda_auto_init",  # broken: default overridden
    "config_dir",  # value overridden for testing
    "data_dir",  # value overridden for testing
    "data_manager_config_file",  # broken: remove 'config/' prefix from schema
    "database_connection",  # untestable; refactor config/__init__ to test
    "database_engine_option_max_overflow",  # overridden for tests running on non-sqlite databases
    "database_engine_option_pool_size",  # overridden for tests runnign on non-sqlite databases
    "database_log_query_counts",  # overridden for tests
    "database_template",  # default value set for tests
    "datatypes_config_file",  # broken
    "default_locale",  # broken
    "dependency_resolution",  # nested properties
    "disable_library_comptypes",  # broken: default overridden with empty string
    "enable_per_request_sql_debugging",  # overridden for tests
    "expose_dataset_path",  # broken: default overridden
    "fetch_url_allowlist",  # specified in driver_util to allow history export tests to target localhost
    "ftp_upload_purge",  # broken: default overridden
    "ftp_upload_dir_template",  # dynamically sets os.path.sep
    "galaxy_data_manager_data_path",  # broken: review config/, possibly refactor
    "galaxy_infrastructure_url",  # broken
    "galaxy_infrastructure_web_port",  # broken
    "heartbeat_log",  # untestable; refactor config/__init__ to test
    "id_secret",  # broken: default overridden
    "job_config",  # no obvious testable defaults
    "job_config_file",  # broken: remove 'config/' prefix from schema
    "job_handler_monitor_sleep",  # configured in driver_util
    "job_metrics_config_file",
    "job_runner_monitor_sleep",  # configured in driver_util
    "job_working_directory",  # broken; may or may not be able to test
    "library_import_dir",  # broken: default overridden
    "logging",  # mapping loaded in config/
    "managed_config_dir",  # depends on config_dir: see note above
    "markdown_export_css",  # default not used?
    "markdown_export_css_pages",  # default not used?
    "markdown_export_css_invocation_reports",  # default not used?
    "master_api_key",  # broken: default value assigned outside of config/
    "migrated_tools_config",  # needs more work (should work)
    "monitor_thread_join_timeout",  # broken: default overridden
    "new_file_path",  # value overridden for testing
    "object_store_store_by",  # broken: default overridden
    "pretty_datetime_format",  # untestable; refactor config/__init__ to test
    "retry_metadata_internally",  # broken: default overridden
    "simplified_workflow_run_ui",  # set to off in testing
    "statsd_host",  # broken: default overridden with empty string
    "statsd_influxdb",  # overridden for tests
    "template_cache_path",  # may or may not be able to test; may be broken
    "tool_config_file",  # default not used; may or may not be testable
    "tool_data_table_config_path",  # broken: remove 'config/' prefix from schema
    "tool_test_data_directories",  # untestable; refactor config/__init__ to test
    "trs_servers_config_file",  # default not used?
    "use_remote_user",  # broken: default overridden
    "use_tasked_jobs",  # broken: default overridden
    "user_library_import_dir",  # broken: default overridden
    "user_tool_filters",  # broken: default overridden
    "user_tool_label_filters",  # broken: default overridden
    "user_tool_section_filters",  # broken: default overridden
    "webhooks_dir",  # broken; also remove 'config/' prefix from schema
    "workflow_monitor_sleep",  # configured in driver_util
    "workflow_resource_params_mapper",  # broken: remove 'config/' prefix from schema
]


@pytest.fixture(scope="module")
def driver(request):
    request.addfinalizer(DRIVER.tear_down)
    return DRIVER


DRIVER: GalaxyTestDriver


def create_driver():
    # Same approach as in functional/test_toolbox_pytest.py:
    # We setup a global driver, so that the driver fixture can tear down the driver.
    # Ideally `create_driver` would be a fixture and clean up after the yield,
    # but that's not compatible with the use use of pytest.mark.parametrize:
    # a fixture is not directly callable, so it cannot be used in place of get_config_data.
    global driver_created
    if not driver_created:
        global DRIVER
        DRIVER = GalaxyTestDriver()
        DRIVER.setup()
        driver_created = True


def get_config_data():
    global DRIVER

    def load_parent_dirs():
        return {
            "root_dir": DRIVER.app.config.root,
            "config_dir": DRIVER.app.config.config_dir,
            "managed_config_dir": DRIVER.app.config.managed_config_dir,
            "data_dir": DRIVER.app.config.data_dir,
            "tool_data_path": DRIVER.app.config.tool_data_path,
            "cache_dir": DRIVER.app.config.cache_dir,
        }

    def resolve(parent, child):
        return os.path.join(parent, child) if child else parent

    def get_expected(key, data, parent_dirs):
        value = data.get("default")
        parent = data.get("path_resolves_to")
        if parent:
            value = resolve(parent_dirs[parent], value)
        if key in RESOLVE:
            parent = RESOLVE[key]
            value = resolve(parent_dirs[parent], value)
        if key in CUSTOM:
            value = CUSTOM[key](value)
        return value

    create_driver()  # create + setup DRIVER
    parent_dirs = load_parent_dirs()  # called after DRIVER is setup
    for key, data in DRIVER.app.config.schema.app_schema.items():
        if key in DO_NOT_TEST:
            continue
        elif f"GALAXY_CONFIG_OVERRIDE_{str(key).upper()}" in os.environ:
            continue
        expected_value = get_expected(key, data, parent_dirs)
        loaded_value = getattr(DRIVER.app.config, key)
        data = OptionData(key=key, expected=expected_value, loaded=loaded_value)  # passed to test
        yield pytest.param(data)


def get_path_data():
    create_driver()  # create + setup DRIVER
    yield from PATH_CONFIG_PROPERTIES


def get_key(option_data):
    return option_data.key


@pytest.mark.parametrize("data", get_config_data(), ids=get_key)
def test_config_option(data, driver):
    assert data.expected == data.loaded


@pytest.mark.parametrize("data", get_path_data())
def test_is_path_absolute(data, driver):
    global DRIVER
    path = getattr(DRIVER.app.config, data)
    if path:
        assert os.path.isabs(path)
