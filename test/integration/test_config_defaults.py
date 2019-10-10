import os
from datetime import timedelta

from base import integration_util


class ConfigDefaultsTestCase(integration_util.IntegrationTestCase):
    """
    This tests: (1) automatic creation of configuration properties; and
    (2) assignment of default values that are specified in the schema and, in
    some cases, are also processed at load time (paths resolved, csv strings
    converted to lists, etc).

    This test case should have tests for ALL properties listed in the main
    schema file. Whenever a property's default value is changed (edits to
    schema or configuration loading procedures), this test code must be
    modified to reflect that change.

    Test assumptions for a default configuration:
    - If a default is set and not modified at load time, expect schema default.
    - If a default is not set, expect null.
    - If a default is set and modified at load time, the test should reflect that
      (if a default is specified in the schema, it is expected that it will be used
      in some form at load time; otherwise it should not be listed as a default).

    Configuration options NOT tested:
    - config_dir (value overridden for testing)
    - data_dir (value overridden for testing)
    - new_file_path (value overridden for testing)
    - logging (mapping loaded in config/; TODO)
    - dependency_resolution (nested properties; TODO)
    - job_config (no obvious testable defaults)
    """

    def __init__(self, *args, **kwargs):
        super(ConfigDefaultsTestCase, self).__init__(*args, **kwargs)
        # use lazy loading for attributes below
        self._root_dir = None
        self._config_dir = None
        self._data_dir = None
        self._tool_data_path = None

    def get_default(self, key):
        # Returns default value or None (because if default value is not
        # specified in the schema, we expect None  by default)
        return self._app.config.appschema[key].get('default', None)

    def get_csv_default_as_list(self, key):
        # Use when schema default is a comma-separated values list
        # which is converted to a list
        return self._app.config.appschema[key]['default'].split(',')

    def get_default_in_root_dir(self, key):
        # Use when schema default is resolved with respect to the installation's root directory
        self._root_dir = self._root_dir or self._app.config.root
        return self._resolve(self._root_dir, self.get_default(key))

    def get_default_in_config_dir(self, key):
        # Use when schema default is resolved with respect to the value of 'config_dir'
        self._config_dir = self._config_dir or self._app.config.config_dir
        return self._resolve(self._config_dir, self.get_default(key))

    def get_default_in_data_dir(self, key):
        # Use when schema default is resolved with respect to the value of 'data_dir'
        self._data_dir = self._data_dir or self._app.config.data_dir
        return self._resolve(self._data_dir, self.get_default(key))

    def get_default_in_tool_data_path(self, key):
        # Use when schema default is resolved with respect to the value of 'tool_data_path'
        self._tool_data_path = self._tool_data_path or self._app.config.tool_data_path
        return self._resolve(self._tool_data_path, self.get_default(key))

    def _resolve(self, parent, child):
        return os.path.join(parent, child) if child else parent

    # def test_default_database_connection(self):
    # TODO: untestable; refactor config/__init__ to test

    # def test_default_database_engine_option_pool_size(self):
    # TODO: default value overridden for tests runnign on non-sqlite databases

    # def test_default_database_engine_option_max_overflow(self):
    # TODO: default value overridden for tests runnign on non-sqlite databases

    def test_default_database_engine_option_pool_recycle(self):
        expect = self.get_default('database_engine_option_pool_recycle')
        assert expect == self._app.config.database_engine_option_pool_recycle

    def test_default_database_engine_option_server_side_cursors(self):
        expect = self.get_default('database_engine_option_server_side_cursors')
        assert expect == self._app.config.database_engine_option_server_side_cursors

    def test_default_database_query_profiling_proxy(self):
        expect = self.get_default('database_query_profiling_proxy')
        assert expect == self._app.config.database_query_profiling_proxy

    # def test_default_database_template(self):
    # TODO: default value set for tests

    def test_default_slow_query_log_threshold(self):
        expect = self.get_default('slow_query_log_threshold')
        assert expect == self._app.config.slow_query_log_threshold

    def test_default_enable_per_request_sql_debugging(self):
        expect = self.get_default('enable_per_request_sql_debugging')
        assert expect == self._app.config.enable_per_request_sql_debugging

    def test_default_install_database_connection(self):
        assert self._app.config.install_database_connection is None

    def test_default_database_auto_migrate(self):
        expect = self.get_default('database_auto_migrate')
        assert expect == self._app.config.database_auto_migrate

    def test_default_database_wait(self):
        expect = self.get_default('database_wait')
        assert expect == self._app.config.database_wait

    def test_default_database_wait_attempts(self):
        expect = self.get_default('database_wait_attempts')
        assert expect == self._app.config.database_wait_attempts

    def test_default_database_wait_sleep(self):
        expect = self.get_default('database_wait_sleep')
        assert expect == self._app.config.database_wait_sleep

    def test_default_file_path(self):
        expect = self.get_default_in_data_dir('file_path')
        assert expect == self._app.config.file_path

    # def test_default_tool_config_file(self):
    # TODO: default not used; may or may not be testable

    # def test_default_shed_tool_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    def test_default_check_migrate_tools(self):
        expect = self.get_default('check_migrate_tools')
        assert expect == self._app.config.check_migrate_tools

    def test_default_migrated_tools_config(self):
        expect = self.get_default_in_config_dir('migrated_tools_config')
        assert expect == self._app.config.migrated_tools_config

    def test_default_integrated_tool_panel_config(self):
        expect = self.get_default_in_config_dir('integrated_tool_panel_config')
        assert expect == self._app.config.integrated_tool_panel_config

    def test_default_tool_path(self):
        expect = self.get_default_in_root_dir('tool_path')
        assert expect == self._app.config.tool_path

    def test_default_tool_dependency_dir(self):
        expect = self.get_default('tool_dependency_dir')
        assert expect == self._app.config.tool_dependency_dir

    # def test_default_dependency_resolvers_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    def test_default_conda_prefix(self):
        assert self._app.config.conda_prefix is None

    def test_default_conda_exec(self):
        assert self._app.config.conda_exec is None

    def test_default_conda_debug(self):
        expect = self.get_default('conda_debug')
        assert expect == self._app.config.conda_debug

    def test_default_conda_ensure_channels(self):
        expect = self.get_default('conda_ensure_channels')
        assert expect == self._app.config.conda_ensure_channels

    def test_default_conda_use_local(self):
        expect = self.get_default('conda_use_local')
        assert expect == self._app.config.conda_use_local

    def test_default_conda_auto_install(self):
        expect = self.get_default('conda_auto_install')
        assert expect == self._app.config.conda_auto_install

    # def test_default_conda_auto_init(self):
    # TODO: broken: default overridden

    def test_default_conda_copy_dependencies(self):
        expect = self.get_default('conda_copy_dependencies')
        assert expect == self._app.config.conda_copy_dependencies

    def test_default_use_cached_dependency_manager(self):
        expect = self.get_default('use_cached_dependency_manager')
        assert expect == self._app.config.use_cached_dependency_manager

    def test_default_tool_dependency_cache_dir(self):
        assert self._app.config.tool_dependency_cache_dir is None

    def test_default_precache_dependencies(self):
        expect = self.get_default('precache_dependencies')
        assert expect == self._app.config.precache_dependencies

    # def test_default_tool_sheds_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    def test_default_watch_tools(self):
        expect = self.get_default('watch_tools')
        assert expect == self._app.config.watch_tools

    def test_default_watch_job_rules(self):
        expect = self.get_default('watch_job_rules')
        assert expect == self._app.config.watch_job_rules

    def test_default_watch_core_config(self):
        expect = self.get_default('watch_core_config')
        assert expect == self._app.config.watch_core_config

    def test_default_legacy_eager_objectstore_initialization(self):
        expect = self.get_default('legacy_eager_objectstore_initialization')
        assert expect == self._app.config.legacy_eager_objectstore_initialization

    def test_default_enable_mulled_containers(self):
        expect = self.get_default('enable_mulled_containers')
        assert expect == self._app.config.enable_mulled_containers

    def test_default_containers_resolvers_config_file(self):
        assert self._app.config.containers_resolvers_config_file is None

    def test_default_involucro_path(self):
        expect = self.get_default_in_root_dir('involucro_path')
        assert expect == self._app.config.involucro_path

    def test_default_involucro_auto_init(self):
        expect = self.get_default('involucro_auto_init')
        assert expect == self._app.config.involucro_auto_init

    def test_default_mulled_channels(self):
        expect = self.get_csv_default_as_list('mulled_channels')
        assert expect == self._app.config.mulled_channels

    def test_default_enable_tool_shed_check(self):
        expect = self.get_default('enable_tool_shed_check')
        assert expect == self._app.config.enable_tool_shed_check

    def test_default_hours_between_check(self):
        expect = self.get_default('hours_between_check')
        assert expect == self._app.config.hours_between_check

    def test_default_manage_dependency_relationships(self):
        expect = self.get_default('manage_dependency_relationships')
        assert expect == self._app.config.manage_dependency_relationships

    # def test_default_tool_data_table_config_path(self):
    # TODO: broken: remove 'config/' prefix from schema

    # def test_default_shed_tool_data_table_config(self):
    # TODO: broken: remove 'config/' prefix from schema

    def test_default_tool_data_path(self):
        expect = self.get_default_in_root_dir('tool_data_path')
        assert expect == self._app.config.tool_data_path

    def test_default_shed_tool_data_path(self):
        expect = self.get_default_in_tool_data_path('shed_tool_data_path')
        assert expect == self._app.config.shed_tool_data_path

    def test_default_watch_tool_data_dir(self):
        expect = self.get_default('watch_tool_data_dir')
        assert expect == self._app.config.watch_tool_data_dir

    def test_default_builds_file_path(self):
        expect = self.get_default_in_tool_data_path('builds_file_path')
        assert expect == self._app.config.builds_file_path

    def test_default_len_file_path(self):
        expect = self.get_default_in_tool_data_path('len_file_path')
        assert expect == self._app.config.len_file_path

    # def test_default_datatypes_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    def test_default_sniff_compressed_dynamic_datatypes_default(self):
        expect = self.get_default('sniff_compressed_dynamic_datatypes_default')
        assert expect == self._app.config.sniff_compressed_dynamic_datatypes_default

    def test_default_datatypes_disable_auto(self):
        expect = self.get_default('datatypes_disable_auto')
        assert expect == self._app.config.datatypes_disable_auto

    def test_default_visualization_plugins_directory(self):
        expect = self.get_default('visualization_plugins_directory')
        assert expect == self._app.config.visualization_plugins_directory

    def test_default_interactive_environment_plugins_directory(self):
        assert self._app.config.interactive_environment_plugins_directory is None

    def test_default_tour_config_dir(self):
        expect = self.get_default('tour_config_dir')
        assert expect == self._app.config.tour_config_dir

    # def test_default_webhooks_dir(self):
    # TODO broken; also remove 'config/' prefix from schema

    # def test_default_job_working_directory(self):
    # TODO broken; may or may not be able to test

    def test_default_cluster_files_directory(self):
        expect = self.get_default_in_data_dir('cluster_files_directory')
        assert expect == self._app.config.cluster_files_directory

    # def test_default_template_cache_path(self):
    # TODO may or may not be able to test; may be broken

    def test_default_check_job_script_integrity(self):
        expect = self.get_default('check_job_script_integrity')
        assert expect == self._app.config.check_job_script_integrity

    def test_default_check_job_script_integrity_count(self):
        expect = self.get_default('check_job_script_integrity_count')
        assert expect == self._app.config.check_job_script_integrity_count

    def test_default_check_job_script_integrity_sleep(self):
        expect = self.get_default('check_job_script_integrity_sleep')
        assert expect == self._app.config.check_job_script_integrity_sleep

    def test_default_default_job_shell(self):
        expect = self.get_default('default_job_shell')
        assert expect == self._app.config.default_job_shell

    def test_default_citation_cache_type(self):
        expect = self.get_default('citation_cache_type')
        assert expect == self._app.config.citation_cache_type

    def test_default_citation_cache_data_dir(self):
        expect = self.get_default_in_data_dir('citation_cache_data_dir')
        assert expect == self._app.config.citation_cache_data_dir

    def test_default_citation_cache_lock_dir(self):
        expect = self.get_default_in_data_dir('citation_cache_lock_dir')
        assert expect == self._app.config.citation_cache_lock_dir

    # def test_default_object_store_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    # def test_default_object_store_store_by(self):
    # TODO: broken: default overridden

    def test_default_smtp_server(self):
        assert self._app.config.smtp_server is None

    def test_default_smtp_username(self):
        assert self._app.config.smtp_username is None

    def test_default_smtp_password(self):
        assert self._app.config.smtp_password is None

    def test_default_smtp_ssl(self):
        expect = self.get_default('smtp_ssl')
        assert expect == self._app.config.smtp_ssl

    def test_default_mailing_join_addr(self):
        assert self._app.config.mailing_join_addr is None

    def test_default_error_email_to(self):
        assert self._app.config.error_email_to is None

    def test_default_email_from(self):
        assert self._app.config.email_from is None

    def test_default_instance_resource_url(self):
        assert self._app.config.instance_resource_url is None

    def test_default_blacklist_file(self):
        assert self._app.config.blacklist_file is None

    def test_default_registration_warning_message(self):
        expect = self.get_default('registration_warning_message')
        assert expect == self._app.config.registration_warning_message

    def test_default_user_activation_on(self):
        expect = self.get_default('user_activation_on')
        assert expect == self._app.config.user_activation_on

    def test_default_activation_grace_period(self):
        expect = self.get_default('activation_grace_period')
        assert expect == self._app.config.activation_grace_period

    def test_default_inactivity_box_content(self):
        expect = self.get_default('inactivity_box_content')
        assert expect == self._app.config.inactivity_box_content

    def test_default_password_expiration_period(self):
        expect = self.get_default('password_expiration_period')
        expect = timedelta(expect)
        assert expect == self._app.config.password_expiration_period

    def test_default_session_duration(self):
        expect = self.get_default('session_duration')
        assert expect == self._app.config.session_duration

    def test_default_ga_code(self):
        assert self._app.config.ga_code is None

    def test_default_display_servers(self):
        expect = self.get_default('display_servers')
        assert expect == self._app.config.display_servers

    def test_default_enable_old_display_applications(self):
        expect = self.get_default('enable_old_display_applications')
        assert expect == self._app.config.enable_old_display_applications

    def test_default_interactivetools_enable(self):
        expect = self.get_default('interactivetools_enable')
        assert expect == self._app.config.interactivetools_enable

    def test_default_visualizations_visible(self):
        expect = self.get_default('visualizations_visible')
        assert expect == self._app.config.visualizations_visible

    def test_default_message_box_visible(self):
        expect = self.get_default('message_box_visible')
        assert expect == self._app.config.message_box_visible

    def test_default_message_box_content(self):
        assert self._app.config.message_box_content is None

    def test_default_message_box_class(self):
        expect = self.get_default('message_box_class')
        assert expect == self._app.config.message_box_class

    def test_default_brand(self):
        assert self._app.config.brand is None

    # def test_default_pretty_datetime_format(self):
    # TODO: untestable; refactor config/__init__ to test

    # def test_default_user_preferences_extra_conf_path
    # TODO: broken: remove 'config/' prefix from schema

    # def test_default_default_locale(self):
    # TODO broken

    # def test_default_galaxy_infrastructure_url(self):
    # TODO broken

    # def test_default_galaxy_infrastructure_web_port(self):
    # TODO broken

    def test_default_welcome_url(self):
        expect = self.get_default('welcome_url')
        assert expect == self._app.config.welcome_url

    def test_default_logo_url(self):
        expect = self.get_default('logo_url')
        assert expect == self._app.config.logo_url

    def test_default_helpsite_url(self):
        assert self._app.config.helpsite_url is None

    def test_default_wiki_url(self):
        expect = self.get_default('wiki_url')
        assert expect == self._app.config.wiki_url

    def test_default_support_url(self):
        expect = self.get_default('support_url')
        assert expect == self._app.config.support_url

    def test_default_citation_url(self):
        expect = self.get_default('citation_url')
        assert expect == self._app.config.citation_url

    def test_default_search_url(self):
        expect = self.get_default('search_url')
        assert expect == self._app.config.search_url

    def test_default_mailing_lists_url(self):
        expect = self.get_default('mailing_lists_url')
        assert expect == self._app.config.mailing_lists_url

    def test_default_screencasts_url(self):
        expect = self.get_default('screencasts_url')
        assert expect == self._app.config.screencasts_url

    def test_default_genomespace_ui_url(self):
        expect = self.get_default('genomespace_ui_url')
        assert expect == self._app.config.genomespace_ui_url

    def test_default_terms_url(self):
        assert self._app.config.terms_url is None

    def test_default_qa_url(self):
        assert self._app.config.qa_url is None

    def test_default_static_enabled(self):
        expect = self.get_default('static_enabled')
        assert expect == self._app.config.static_enabled

    def test_default_static_cache_time(self):
        expect = self.get_default('static_cache_time')
        assert expect == self._app.config.static_cache_time

    def test_default_static_dir(self):
        expect = self.get_default('static_dir')
        assert expect == self._app.config.static_dir

    def test_default_static_images_dir(self):
        expect = self.get_default('static_images_dir')
        assert expect == self._app.config.static_images_dir

    def test_default_static_favicon_dir(self):
        expect = self.get_default('static_favicon_dir')
        assert expect == self._app.config.static_favicon_dir

    def test_default_static_scripts_dir(self):
        expect = self.get_default('static_scripts_dir')
        assert expect == self._app.config.static_scripts_dir

    def test_default_static_style_dir(self):
        expect = self.get_default('static_style_dir')
        assert expect == self._app.config.static_style_dir

    def test_default_static_robots_txt(self):
        expect = self.get_default('static_robots_txt')
        assert expect == self._app.config.static_robots_txt

    def test_default_display_chunk_size(self):
        expect = self.get_default('display_chunk_size')
        assert expect == self._app.config.display_chunk_size

    def test_default_apache_xsendfile(self):
        expect = self.get_default('apache_xsendfile')
        assert expect == self._app.config.apache_xsendfile

    def test_default_nginx_x_accel_redirect_base(self):
        assert self._app.config.nginx_x_accel_redirect_base is None

    def test_default_upstream_gzip(self):
        expect = self.get_default('upstream_gzip')
        assert expect == self._app.config.upstream_gzip

    def test_default_x_frame_options(self):
        expect = self.get_default('x_frame_options')
        assert expect == self._app.config.x_frame_options

    def test_default_nginx_upload_store(self):
        assert self._app.config.nginx_upload_store is None

    def test_default_nginx_upload_path(self):
        assert self._app.config.nginx_upload_path is None

    def test_default_nginx_upload_job_files_store(self):
        assert self._app.config.nginx_upload_job_files_store is None

    def test_default_nginx_upload_job_files_path(self):
        assert self._app.config.nginx_upload_job_files_path is None

    # def test_default_chunk_upload_size(self):
    # TODO: broken: default overridden

    def test_default_dynamic_proxy_manage(self):
        expect = self.get_default('dynamic_proxy_manage')
        assert expect == self._app.config.dynamic_proxy_manage

    def test_default_dynamic_proxy(self):
        expect = self.get_default('dynamic_proxy')
        assert expect == self._app.config.dynamic_proxy

    def test_default_dynamic_proxy_session_map(self):
        expect = self.get_default_in_data_dir('dynamic_proxy_session_map')
        assert expect == self._app.config.dynamic_proxy_session_map

    def test_default_dynamic_proxy_bind_port(self):
        expect = self.get_default('dynamic_proxy_bind_port')
        assert expect == self._app.config.dynamic_proxy_bind_port

    def test_default_dynamic_proxy_bind_ip(self):
        expect = self.get_default('dynamic_proxy_bind_ip')
        assert expect == self._app.config.dynamic_proxy_bind_ip

    def test_default_dynamic_proxy_debug(self):
        expect = self.get_default('dynamic_proxy_debug')
        assert expect == self._app.config.dynamic_proxy_debug

    def test_default_dynamic_proxy_external_proxy(self):
        expect = self.get_default('dynamic_proxy_external_proxy')
        assert expect == self._app.config.dynamic_proxy_external_proxy

    def test_default_dynamic_proxy_prefix(self):
        expect = self.get_default('dynamic_proxy_prefix')
        assert expect == self._app.config.dynamic_proxy_prefix

    def test_default_dynamic_proxy_golang_noaccess(self):
        expect = self.get_default('dynamic_proxy_golang_noaccess')
        assert expect == self._app.config.dynamic_proxy_golang_noaccess

    def test_default_dynamic_proxy_golang_clean_interval(self):
        expect = self.get_default('dynamic_proxy_golang_clean_interval')
        assert expect == self._app.config.dynamic_proxy_golang_clean_interval

    def test_default_dynamic_proxy_golang_docker_address(self):
        expect = self.get_default('dynamic_proxy_golang_docker_address')
        assert expect == self._app.config.dynamic_proxy_golang_docker_address

    def test_default_dynamic_proxy_golang_api_key(self):
        assert self._app.config.dynamic_proxy_golang_api_key is None

    def test_default_auto_configure_logging(self):
        expect = self.get_default('auto_configure_logging')
        assert expect == self._app.config.auto_configure_logging

    def test_default_log_level(self):
        expect = self.get_default('log_level')
        assert expect == self._app.config.log_level

    def test_default_database_engine_option_echo(self):
        expect = self.get_default('database_engine_option_echo')
        assert expect == self._app.config.database_engine_option_echo

    def test_default_database_engine_option_echo_pool(self):
        expect = self.get_default('database_engine_option_echo_pool')
        assert expect == self._app.config.database_engine_option_echo_pool

    def test_default_log_events(self):
        expect = self.get_default('log_events')
        assert expect == self._app.config.log_events

    def test_default_log_actions(self):
        expect = self.get_default('log_actions')
        assert expect == self._app.config.log_actions

    def test_default_fluent_log(self):
        expect = self.get_default('fluent_log')
        assert expect == self._app.config.fluent_log

    def test_default_fluent_host(self):
        expect = self.get_default('fluent_host')
        assert expect == self._app.config.fluent_host

    def test_default_fluent_port(self):
        expect = self.get_default('fluent_port')
        assert expect == self._app.config.fluent_port

    def test_default_sanitize_all_html(self):
        expect = self.get_default('sanitize_all_html')
        assert expect == self._app.config.sanitize_all_html

    def test_default_sanitize_whitelist_file(self):
        expect = self.get_default_in_root_dir('sanitize_whitelist_file')
        assert expect == self._app.config.sanitize_whitelist_file

    def test_default_serve_xss_vulnerable_mimetypes(self):
        expect = self.get_default('serve_xss_vulnerable_mimetypes')
        assert expect == self._app.config.serve_xss_vulnerable_mimetypes

    def test_default_allowed_origin_hostnames(self):
        assert self._app.config.allowed_origin_hostnames is None

    def test_default_trust_jupyter_notebook_conversion(self):
        expect = self.get_default('trust_jupyter_notebook_conversion')
        assert expect == self._app.config.trust_jupyter_notebook_conversion

    def test_default_debug(self):
        expect = self.get_default('debug')
        assert expect == self._app.config.debug

    def test_default_use_lint(self):
        expect = self.get_default('use_lint')
        assert expect == self._app.config.use_lint

    def test_default_use_profile(self):
        expect = self.get_default('use_profile')
        assert expect == self._app.config.use_profile

    def test_default_use_printdebug(self):
        expect = self.get_default('use_printdebug')
        assert expect == self._app.config.use_printdebug

    def test_default_use_interactive(self):
        expect = self.get_default('use_interactive')
        assert expect == self._app.config.use_interactive

    # def test_default_monitor_thread_join_timeout(self):
    # TODO broken: default overridden

    def test_default_use_heartbeat(self):
        expect = self.get_default('use_heartbeat')
        assert expect == self._app.config.use_heartbeat

    def test_default_heartbeat_interval(self):
        expect = self.get_default('heartbeat_interval')
        assert expect == self._app.config.heartbeat_interval

    # def test_default_heartbeat_log(self):
    # TODO: untestable; refactor config/__init__ to test

    def test_default_sentry_dsn(self):
        assert self._app.config.sentry_dsn is None

    def test_default_sentry_sloreq_threshold(self):
        expect = self.get_default('sentry_sloreq_threshold')
        assert expect == self._app.config.sentry_sloreq_threshold

    # def test_default_statsd_host(self):
    # TODO broken: default overridden with empty string

    def test_default_statsd_port(self):
        expect = self.get_default('statsd_port')
        assert expect == self._app.config.statsd_port

    def test_default_statsd_prefix(self):
        expect = self.get_default('statsd_prefix')
        assert expect == self._app.config.statsd_prefix

    def test_default_statsd_influxdb(self):
        expect = self.get_default('statsd_influxdb')
        assert expect == self._app.config.statsd_influxdb

    # def test_default_library_import_dir(self):
    # TODO broken: default overridden

    # def test_default_user_library_import_dir(self):
    # TODO broken: default overridden

    def test_default_user_library_import_dir_auto_creation(self):
        expect = self.get_default('user_library_import_dir_auto_creation')
        assert expect == self._app.config.user_library_import_dir_auto_creation

    def test_default_user_library_import_symlink_whitelist(self):
        expect = []
        assert expect == self._app.config.user_library_import_symlink_whitelist

    def test_default_user_library_import_check_permissions(self):
        expect = self.get_default('user_library_import_check_permissions')
        assert expect == self._app.config.user_library_import_check_permissions

    def test_default_allow_path_paste(self):
        expect = self.get_default('allow_path_paste')
        assert expect == self._app.config.allow_path_paste

    # def test_default_disable_library_comptypes(self):
    # TODO broken: default overridden with empty string

    def test_default_transfer_manager_port(self):
        expect = self.get_default('transfer_manager_port')
        assert expect == self._app.config.transfer_manager_port

    def test_default_tool_name_boost(self):
        expect = self.get_default('tool_name_boost')
        assert expect == self._app.config.tool_name_boost

    def test_default_tool_section_boost(self):
        expect = self.get_default('tool_section_boost')
        assert expect == self._app.config.tool_section_boost

    def test_default_tool_description_boost(self):
        expect = self.get_default('tool_description_boost')
        assert expect == self._app.config.tool_description_boost

    def test_default_tool_label_boost(self):
        expect = self.get_default('tool_label_boost')
        assert expect == self._app.config.tool_label_boost

    def test_default_tool_stub_boost(self):
        expect = self.get_default('tool_stub_boost')
        assert expect == self._app.config.tool_stub_boost

    def test_default_tool_help_boost(self):
        expect = self.get_default('tool_help_boost')
        assert expect == self._app.config.tool_help_boost

    def test_default_tool_search_limit(self):
        expect = self.get_default('tool_search_limit')
        assert expect == self._app.config.tool_search_limit

    def test_default_tool_enable_ngram_search(self):
        expect = self.get_default('tool_enable_ngram_search')
        assert expect == self._app.config.tool_enable_ngram_search

    def test_default_tool_ngram_minsize(self):
        expect = self.get_default('tool_ngram_minsize')
        assert expect == self._app.config.tool_ngram_minsize

    def test_default_tool_ngram_maxsize(self):
        expect = self.get_default('tool_ngram_maxsize')
        assert expect == self._app.config.tool_ngram_maxsize

    # def test_default_tool_test_data_directories(self):
    # TODO: untestable; refactor config/__init__ to test

    # def test_default_id_secret(self):
    # TODO broken: default overridden

    # def test_default_use_remote_user(self):
    # TODO broken: default overridden

    def test_default_remote_user_maildomain(self):
        assert self._app.config.remote_user_maildomain is None

    def test_default_remote_user_header(self):
        expect = self.get_default('remote_user_header')
        assert expect == self._app.config.remote_user_header

    def test_default_remote_user_secret(self):
        expect = self.get_default('remote_user_secret')
        assert expect == self._app.config.remote_user_secret

    def test_default_remote_user_logout_href(self):
        assert self._app.config.remote_user_logout_href is None

    def test_default_normalize_remote_user_email(self):
        expect = self.get_default('normalize_remote_user_email')
        assert expect == self._app.config.normalize_remote_user_email

    def test_default_single_user(self):
        assert self._app.config.single_user is None

    # def test_default_admin_users(self):
    # TODO: may or may not be testable: special test value assigned

    def test_default_require_login(self):
        expect = self.get_default('require_login')
        assert expect == self._app.config.require_login

    def test_default_show_welcome_with_login(self):
        expect = self.get_default('show_welcome_with_login')
        assert expect == self._app.config.show_welcome_with_login

    def test_default_allow_user_creation(self):
        expect = self.get_default('allow_user_creation')
        assert expect == self._app.config.allow_user_creation

    # def test_default_allow_user_deletion(self):
    # TODO: broken: default overridden

    def test_default_allow_user_impersonation(self):
        expect = self.get_default('allow_user_impersonation')
        assert expect == self._app.config.allow_user_impersonation

    def test_default_show_user_prepopulate_form(self):
        expect = self.get_default('show_user_prepopulate_form')
        assert expect == self._app.config.show_user_prepopulate_form

    def test_default_allow_user_dataset_purge(self):
        expect = self.get_default('allow_user_dataset_purge')
        assert expect == self._app.config.allow_user_dataset_purge

    def test_default_new_user_dataset_access_role_default_private(self):
        expect = self.get_default('new_user_dataset_access_role_default_private')
        assert expect == self._app.config.new_user_dataset_access_role_default_private

    def test_default_expose_user_name(self):
        expect = self.get_default('expose_user_name')
        assert expect == self._app.config.expose_user_name

    def test_default_expose_user_email(self):
        expect = self.get_default('expose_user_email')
        assert expect == self._app.config.expose_user_email

    def test_default_fetch_url_whitelist(self):
        assert self._app.config.fetch_url_whitelist is None

    def test_default_enable_beta_gdpr(self):
        expect = self.get_default('enable_beta_gdpr')
        assert expect == self._app.config.enable_beta_gdpr

    def test_default_enable_beta_containers_interface(self):
        expect = self.get_default('enable_beta_containers_interface')
        assert expect == self._app.config.enable_beta_containers_interface

    def test_default_enable_beta_workflow_modules(self):
        expect = self.get_default('enable_beta_workflow_modules')
        assert expect == self._app.config.enable_beta_workflow_modules

    def test_default_default_workflow_export_format(self):
        expect = self.get_default('default_workflow_export_format')
        assert expect == self._app.config.default_workflow_export_format

    def test_default_force_beta_workflow_scheduled_min_steps(self):
        expect = self.get_default('force_beta_workflow_scheduled_min_steps')
        assert expect == self._app.config.force_beta_workflow_scheduled_min_steps

    def test_default_force_beta_workflow_scheduled_for_collections(self):
        expect = self.get_default('force_beta_workflow_scheduled_for_collections')
        assert expect == self._app.config.force_beta_workflow_scheduled_for_collections

    def test_default_parallelize_workflow_scheduling_within_histories(self):
        expect = self.get_default('parallelize_workflow_scheduling_within_histories')
        assert expect == self._app.config.parallelize_workflow_scheduling_within_histories

    def test_default_maximum_workflow_invocation_duration(self):
        expect = self.get_default('maximum_workflow_invocation_duration')
        assert expect == self._app.config.maximum_workflow_invocation_duration

    def test_default_maximum_workflow_jobs_per_scheduling_iteration(self):
        expect = self.get_default('maximum_workflow_jobs_per_scheduling_iteration')
        assert expect == self._app.config.maximum_workflow_jobs_per_scheduling_iteration

    def test_default_history_local_serial_workflow_scheduling(self):
        expect = self.get_default('history_local_serial_workflow_scheduling')
        assert expect == self._app.config.history_local_serial_workflow_scheduling

    def test_default_enable_oidc(self):
        expect = self.get_default('enable_oidc')
        assert expect == self._app.config.enable_oidc

    # def test_default_oidc_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    # def test_default_oidc_backends_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    # def test_default_auth_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    # def test_default_api_allow_run_as(self):
    # TODO may or may not be testable: test value assigned

    # def test_default_master_api_key(self):
    # TODO broken: default value assigned outside of config/

    def test_default_enable_openid(self):
        expect = self.get_default('enable_openid')
        assert expect == self._app.config.enable_openid

    def test_default_openid_consumer_cache_path(self):
        expect = self.get_default_in_data_dir('openid_consumer_cache_path')
        assert expect == self._app.config.openid_consumer_cache_path

    def test_default_enable_tool_tags(self):
        expect = self.get_default('enable_tool_tags')
        assert expect == self._app.config.enable_tool_tags

    def test_default_enable_unique_workflow_defaults(self):
        expect = self.get_default('enable_unique_workflow_defaults')
        assert expect == self._app.config.enable_unique_workflow_defaults

    def test_default_myexperiment_url(self):
        expect = self.get_default('myexperiment_url')
        assert expect == self._app.config.myexperiment_url

    def test_default_ftp_upload_dir(self):
        assert self._app.config.ftp_upload_dir is None

    def test_default_ftp_upload_site(self):
        assert self._app.config.ftp_upload_site is None

    def test_default_ftp_upload_dir_identifier(self):
        expect = self.get_default('ftp_upload_dir_identifier')
        assert expect == self._app.config.ftp_upload_dir_identifier

    def test_default_ftp_upload_dir_template(self):
        expect = self.get_default('ftp_upload_dir_template')
        assert expect == self._app.config.ftp_upload_dir_template

    # def test_default_ftp_upload_purge(self):
    # TODO: broken: default overridden

    def test_default_enable_quotas(self):
        expect = self.get_default('enable_quotas')
        assert expect == self._app.config.enable_quotas

    # def test_default_expose_dataset_path(self):
    # TODO: broken: default overridden

    def test_default_expose_potentially_sensitive_job_metrics(self):
        expect = self.get_default('expose_potentially_sensitive_job_metrics')
        assert expect == self._app.config.expose_potentially_sensitive_job_metrics

    def test_default_enable_legacy_sample_tracking_api(self):
        expect = self.get_default('enable_legacy_sample_tracking_api')
        assert expect == self._app.config.enable_legacy_sample_tracking_api

    def test_default_enable_data_manager_user_view(self):
        expect = self.get_default('enable_data_manager_user_view')
        assert expect == self._app.config.enable_data_manager_user_view

    # def test_default_data_manager_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    # def test_default_shed_data_manager_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    # def test_default_galaxy_data_manager_data_path(self):
    # TODO broken: review config/, possibly refactor

    # def test_default_job_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    def test_default_dependency_resolvers(self):
        assert self._app.config.dependency_resolvers is None

    def test_default_default_job_resubmission_condition(self):
        assert self._app.config.default_job_resubmission_condition is None

    def test_default_track_jobs_in_database(self):
        expect = self.get_default('track_jobs_in_database')
        assert expect == self._app.config.track_jobs_in_database

    # def test_default_use_tasked_jobs(self):
    # TODO: broken: default overridden

    def test_default_local_task_queue_workers(self):
        expect = self.get_default('local_task_queue_workers')
        assert expect == self._app.config.local_task_queue_workers

    def test_default_enable_job_recovery(self):
        expect = self.get_default('enable_job_recovery')
        assert expect == self._app.config.enable_job_recovery

    # def test_default_retry_metadata_internally(self):
    # TODO: broken: default overridden

    def test_default_max_metadata_value_size(self):
        expect = self.get_default('max_metadata_value_size')
        assert expect == self._app.config.max_metadata_value_size

    def test_default_outputs_to_working_directory(self):
        expect = self.get_default('outputs_to_working_directory')
        assert expect == self._app.config.outputs_to_working_directory

    def test_default_retry_job_output_collection(self):
        expect = self.get_default('retry_job_output_collection')
        assert expect == self._app.config.retry_job_output_collection

    def test_default_preserve_python_environment(self):
        expect = self.get_default('preserve_python_environment')
        assert expect == self._app.config.preserve_python_environment

    # def test_default_cleanup_job(self):
    # TODO: broken: default overridden

    def test_default_drmaa_external_runjob_script(self):
        assert self._app.config.drmaa_external_runjob_script is None

    def test_default_drmaa_external_killjob_script(self):
        assert self._app.config.drmaa_external_killjob_script is None

    def test_default_external_chown_script(self):
        assert self._app.config.external_chown_script is None

    def test_default_real_system_username(self):
        expect = self.get_default('real_system_username')
        assert expect == self._app.config.real_system_username

    def test_default_environment_setup_file(self):
        assert self._app.config.environment_setup_file is None

    # def test_default_job_resource_params_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    # def test_default_workflow_resource_params_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    # def test_default_workflow_resource_params_mapper(self):
    # TODO: broken: remove 'config/' prefix from schema

    # def test_default_workflow_schedulers_config_file(self):
    # TODO: broken: remove 'config/' prefix from schema

    def test_default_cache_user_job_count(self):
        expect = self.get_default('cache_user_job_count')
        assert expect == self._app.config.cache_user_job_count

    def test_default_tool_filters(self):
        expect = []
        assert expect == self._app.config.tool_filters

    def test_default_tool_label_filters(self):
        expect = []
        assert expect == self._app.config.tool_label_filters

    def test_default_tool_section_filters(self):
        expect = []
        assert expect == self._app.config.tool_section_filters

    # def test_default_user_tool_filters(self):
    # TODO: broken: default overridden

    # def test_default_user_tool_section_filters(self):
    # # TODO: broken: default overridden

    # def test_default_user_tool_label_filters(self):
    # TODO: broken: default overridden

    def test_default_toolbox_filter_base_modules(self):
        expect = self.get_csv_default_as_list('toolbox_filter_base_modules')
        assert expect == self._app.config.toolbox_filter_base_modules

    # def test_default_amqp_internal_connection(self):
    # TODO may or may not be testable; refactor config/

    def test_default_enable_communication_server(self):
        expect = self.get_default('enable_communication_server')
        assert expect == self._app.config.enable_communication_server

    def test_default_communication_server_host(self):
        expect = self.get_default('communication_server_host')
        assert expect == self._app.config.communication_server_host

    def test_default_communication_server_port(self):
        expect = self.get_default('communication_server_port')
        assert expect == self._app.config.communication_server_port

    def test_default_persistent_communication_rooms(self):
        expect = []
        assert expect == self._app.config.persistent_communication_rooms

    def test_default_use_pbkdf2(self):
        expect = self.get_default('use_pbkdf2')
        assert expect == self._app.config.use_pbkdf2
