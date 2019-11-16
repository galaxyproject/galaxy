"""
Universe configuration builder.
"""
# absolute_import needed for tool_shed package.
from __future__ import absolute_import

import collections
import errno
import ipaddress
import logging
import logging.config
import os
import re
import signal
import socket
import string
import sys
import tempfile
import threading
import time
from datetime import timedelta

import yaml
from six import string_types
from six.moves import configparser

from galaxy.config.schema import AppSchema
from galaxy.containers import parse_containers_config
from galaxy.exceptions import ConfigurationError
from galaxy.model import mapping
from galaxy.model.tool_shed_install.migrate.check import create_or_verify_database as tsi_create_or_verify_database
from galaxy.tool_util.deps.container_resolvers.mulled import DEFAULT_CHANNELS
from galaxy.util import (
    ExecutionTimer,
    listify,
    string_as_bool,
    unicodify,
)
from galaxy.util.dbkeys import GenomeBuilds
from galaxy.util.logging import LOGLV_TRACE
from galaxy.util.properties import (
    find_config_file,
    read_properties_from_file,
    running_from_source,
)
from galaxy.web.formatting import expand_pretty_datetime_format
from galaxy.web_stack import (
    get_stack_facts,
    register_postfork_function
)
from ..version import VERSION_MAJOR

log = logging.getLogger(__name__)

GALAXY_APP_NAME = 'galaxy'
GALAXY_CONFIG_SCHEMA_PATH = 'lib/galaxy/webapps/galaxy/config_schema.yml'
LOGGING_CONFIG_DEFAULT = {
    'disable_existing_loggers': False,
    'version': 1,
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'paste.httpserver.ThreadPool': {
            'level': 'WARN',
            'qualname': 'paste.httpserver.ThreadPool',
        },
        'routes.middleware': {
            'level': 'WARN',
            'qualname': 'routes.middleware',
        },
        'amqp': {
            'level': 'INFO',
            'qualname': 'amqp',
        },
    },
    'filters': {
        'stack': {
            '()': 'galaxy.web_stack.application_stack_log_filter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'stack',
            'level': 'DEBUG',
            'stream': 'ext://sys.stderr',
            'filters': ['stack'],
        },
    },
    'formatters': {
        'stack': {
            '()': 'galaxy.web_stack.application_stack_log_formatter',
        },
    },
}
"""Default value for logging configuration, passed to :func:`logging.config.dictConfig`"""


def find_root(kwargs):
    root = os.path.abspath(kwargs.get('root_dir', '.'))
    return root


class BaseAppConfiguration(object):
    def _set_config_base(self, config_kwargs):
        self.sample_config_dir = os.path.join(os.path.dirname(__file__), 'sample')
        self.config_file = find_config_file('galaxy')
        # Parse global_conf and save the parser
        self.global_conf = config_kwargs.get('global_conf', None)
        self.global_conf_parser = configparser.ConfigParser()
        if not self.config_file and self.global_conf and "__file__" in self.global_conf:
            self.config_file = self.global_conf['__file__']

        if self.config_file is None:
            log.warning("No Galaxy config file found, running from current working directory: %s", os.getcwd())
        else:
            try:
                self.global_conf_parser.read(self.config_file)
            except (IOError, OSError):
                raise
            except Exception:
                # Not an INI file
                pass

        _config_dir = os.path.dirname(self.config_file) if self.config_file else os.getcwd()
        self.config_dir = config_kwargs.get('config_dir', _config_dir)

        self.data_dir = config_kwargs.get('data_dir')
        # mutable_config_dir is intentionally not configurable. You can
        # override individual mutable configs with config options, but they
        # should be considered Galaxy-controlled data files and will by default
        # just live in the data dir

        if running_from_source:
            if self.data_dir is None:
                self.data_dir = os.path.join(self.root, 'database')
            if self.config_file is None:
                self.config_dir = os.path.join(self.root, 'config')
            self.mutable_config_dir = self.config_dir
            # TODO: do we still need to support ../shed_tools?
            self.shed_tools_dir = os.path.join(self.data_dir, 'shed_tools')
        else:
            if self.data_dir is None:
                self.data_dir = os.path.join(self.config_dir, 'data')
            self.mutable_config_dir = os.path.join(self.data_dir, 'config')
            self.shed_tools_dir = os.path.join(self.data_dir, 'shed_tools')

        log.debug("Configuration directory is %s", self.config_dir)
        log.debug("Data directory is %s", self.data_dir)
        log.debug("Mutable config directory is %s", self.mutable_config_dir)

    def _in_mutable_config_dir(self, path):
        return os.path.join(self.mutable_config_dir, path)

    def _in_config_dir(self, path):
        return os.path.join(self.config_dir, path)

    def _in_sample_dir(self, path):
        return os.path.join(self.sample_config_dir, path)

    def _parse_config_file_options(self, defaults, listify_defaults, config_kwargs):
        for var, values in defaults.items():
            if config_kwargs.get(var, None) is not None:
                path = config_kwargs.get(var)
                setattr(self, var + '_set', True)
            else:
                for value in values:
                    if os.path.exists(os.path.join(self.root, value)):
                        path = value
                        break
                else:
                    path = values[-1]
                setattr(self, var + '_set', False)
            setattr(self, var, os.path.join(self.root, path))

        for var, values in listify_defaults.items():
            paths = []
            if config_kwargs.get(var, None) is not None:
                paths = listify(config_kwargs.get(var))
                setattr(self, var + '_set', True)
            else:
                for value in values:
                    for path in listify(value):
                        if not os.path.exists(os.path.join(self.root, path)):
                            break
                    else:
                        paths = listify(value)
                        break
                else:
                    paths = listify(values[-1])
                setattr(self, var + '_set', False)
            setattr(self, var, [os.path.join(self.root, x) for x in paths])


class GalaxyAppConfiguration(BaseAppConfiguration):
    deprecated_options = ('database_file', 'track_jobs_in_database')
    default_config_file_name = 'galaxy.yml'

    def __init__(self, **kwargs):
        self.config_dict = kwargs
        self.root = find_root(kwargs)

        self._set_config_base(kwargs)
        self._set_reloadable_properties(kwargs)

        # Resolve paths of other config files
        self.parse_config_file_options(kwargs)

        # Collect the umask and primary gid from the environment
        self.umask = os.umask(0o77)  # get the current umask
        os.umask(self.umask)  # can't get w/o set, so set it back
        self.gid = os.getgid()  # if running under newgrp(1) we'll need to fix the group of data created on the cluster

        self.version_major = VERSION_MAJOR
        # Database related configuration
        self.check_migrate_databases = kwargs.get('check_migrate_databases', True)
        self.database_connection = kwargs.get("database_connection",
                                              "sqlite:///%s?isolation_level=IMMEDIATE" % os.path.join(self.data_dir, "universe.sqlite"))
        self.database_engine_options = get_database_engine_options(kwargs)
        self.database_create_tables = string_as_bool(kwargs.get("database_create_tables", "True"))
        self.database_query_profiling_proxy = string_as_bool(kwargs.get("database_query_profiling_proxy", "False"))
        self.database_template = kwargs.get("database_template", None)
        self.database_encoding = kwargs.get("database_encoding", None)  # Create new databases with this encoding.
        self.slow_query_log_threshold = float(kwargs.get("slow_query_log_threshold", 0))
        self.thread_local_log = None
        if string_as_bool(kwargs.get("enable_per_request_sql_debugging", "False")):
            self.thread_local_log = threading.local()

        # Don't set this to true for production databases, but probably should
        # default to True for sqlite databases.
        self.database_auto_migrate = string_as_bool(kwargs.get("database_auto_migrate", "False"))

        # Install database related configuration (if different).
        self.install_database_connection = kwargs.get("install_database_connection", None)
        self.install_database_engine_options = get_database_engine_options(kwargs, model_prefix="install_")

        # Wait for database to become available instead of failing
        self.database_wait = string_as_bool(kwargs.get("database_wait", "False"))
        # Attempts before failing
        self.database_wait_attempts = int(kwargs.get("database_wait_attempts", 60))
        # Sleep period between attepmts (seconds)
        self.database_wait_sleep = float(kwargs.get("database_wait_sleep", 1))

        # Where dataset files are stored
        self.file_path = self.resolve_path(kwargs.get("file_path", os.path.join(self.data_dir, "files")))
        # new_file_path and legacy_home_dir can be overridden per destination in job_conf.
        self.new_file_path = self.resolve_path(kwargs.get("new_file_path", os.path.join(self.data_dir, "tmp")))
        override_tempdir = string_as_bool(kwargs.get("override_tempdir", "True"))
        if override_tempdir:
            tempfile.tempdir = self.new_file_path
        self.shared_home_dir = kwargs.get("shared_home_dir", None)
        self.openid_consumer_cache_path = self.resolve_path(kwargs.get("openid_consumer_cache_path", os.path.join(self.data_dir, "openid_consumer_cache")))
        self.cookie_path = kwargs.get("cookie_path", None)
        self.enable_quotas = string_as_bool(kwargs.get('enable_quotas', False))
        self.enable_unique_workflow_defaults = string_as_bool(kwargs.get('enable_unique_workflow_defaults', False))
        self.tool_path = self.resolve_path(kwargs.get("tool_path", "tools"))
        self.tool_data_path = self.resolve_path(kwargs.get("tool_data_path", "tool-data"))
        if not running_from_source and kwargs.get("tool_data_path", None) is None:
            self.tool_data_path = os.path.join(self.data_dir, "tool-data")
        self.builds_file_path = self.resolve_path(kwargs.get("builds_file_path", os.path.join(self.tool_data_path, 'shared', 'ucsc', 'builds.txt')))
        self.len_file_path = self.resolve_path(kwargs.get("len_file_path", os.path.join(self.tool_data_path, 'shared', 'ucsc', 'chrom')))
        # Galaxy OIDC settings.
        self.enable_oidc = kwargs.get("enable_oidc", False)
        self.oidc_config = kwargs.get("oidc_config_file", self.oidc_config_file)
        self.oidc_backends_config = kwargs.get("oidc_backends_config_file", self.oidc_backends_config_file)
        self.oidc = []
        self.integrated_tool_panel_config = self.resolve_path(kwargs.get('integrated_tool_panel_config', os.path.join(self.mutable_config_dir, 'integrated_tool_panel.xml')))
        integrated_tool_panel_tracking_directory = kwargs.get('integrated_tool_panel_tracking_directory', None)
        if integrated_tool_panel_tracking_directory:
            self.integrated_tool_panel_tracking_directory = self.resolve_path(integrated_tool_panel_tracking_directory)
        else:
            self.integrated_tool_panel_tracking_directory = None
        self.toolbox_filter_base_modules = listify(kwargs.get("toolbox_filter_base_modules", "galaxy.tools.filters,galaxy.tools.toolbox.filters"))
        self.tool_filters = listify(kwargs.get("tool_filters", []), do_strip=True)
        self.tool_label_filters = listify(kwargs.get("tool_label_filters", []), do_strip=True)
        self.tool_section_filters = listify(kwargs.get("tool_section_filters", []), do_strip=True)

        self.user_tool_filters = listify(kwargs.get("user_tool_filters", []), do_strip=True)
        self.user_tool_label_filters = listify(kwargs.get("user_tool_label_filters", []), do_strip=True)
        self.user_tool_section_filters = listify(kwargs.get("user_tool_section_filters", []), do_strip=True)
        self.has_user_tool_filters = bool(self.user_tool_filters or self.user_tool_label_filters or self.user_tool_section_filters)

        self.tour_config_dir = self.resolve_path(kwargs.get("tour_config_dir", "config/plugins/tours"))
        self.webhooks_dirs = self.resolve_path(kwargs.get("webhooks_dir", "config/plugins/webhooks"))

        self.expose_user_name = kwargs.get("expose_user_name", False)
        self.expose_user_email = kwargs.get("expose_user_email", False)

        self.password_expiration_period = timedelta(days=int(kwargs.get("password_expiration_period", 0)))

        # Check for tools defined in the above non-shed tool configs (i.e., tool_conf.xml) tht have
        # been migrated from the Galaxy code distribution to the Tool Shed.
        self.check_migrate_tools = string_as_bool(kwargs.get('check_migrate_tools', False))
        self.shed_tool_data_path = kwargs.get("shed_tool_data_path", None)
        self.x_frame_options = kwargs.get("x_frame_options", "SAMEORIGIN")
        if self.shed_tool_data_path:
            self.shed_tool_data_path = self.resolve_path(self.shed_tool_data_path)
        else:
            self.shed_tool_data_path = self.tool_data_path
        self.manage_dependency_relationships = string_as_bool(kwargs.get('manage_dependency_relationships', False))
        self.running_functional_tests = string_as_bool(kwargs.get('running_functional_tests', False))
        self.hours_between_check = kwargs.get('hours_between_check', 12)
        self.enable_tool_shed_check = string_as_bool(kwargs.get('enable_tool_shed_check', False))
        if isinstance(self.hours_between_check, string_types):
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
        self.enable_data_manager_user_view = string_as_bool(kwargs.get("enable_data_manager_user_view", "False"))
        self.galaxy_data_manager_data_path = kwargs.get('galaxy_data_manager_data_path', self.tool_data_path)
        self.tool_secret = kwargs.get("tool_secret", "")
        self.id_secret = kwargs.get("id_secret", "USING THE DEFAULT IS NOT SECURE!")
        self.retry_metadata_internally = string_as_bool(kwargs.get("retry_metadata_internally", "True"))
        self.max_metadata_value_size = int(kwargs.get("max_metadata_value_size", 5242880))
        self.metadata_strategy = kwargs.get("metadata_strategy", "directory")
        self.single_user = kwargs.get("single_user", None)
        self.use_remote_user = string_as_bool(kwargs.get("use_remote_user", "False")) or self.single_user
        self.normalize_remote_user_email = string_as_bool(kwargs.get("normalize_remote_user_email", "False"))
        self.remote_user_maildomain = kwargs.get("remote_user_maildomain", None)
        self.remote_user_header = kwargs.get("remote_user_header", 'HTTP_REMOTE_USER')
        self.remote_user_logout_href = kwargs.get("remote_user_logout_href", None)
        self.remote_user_secret = kwargs.get("remote_user_secret", None)
        self.require_login = string_as_bool(kwargs.get("require_login", "False"))
        self.fetch_url_whitelist_ips = [
            ipaddress.ip_network(unicodify(ip.strip()))  # If it has a slash, assume 127.0.0.1/24 notation
            if '/' in ip else
            ipaddress.ip_address(unicodify(ip.strip()))  # Otherwise interpret it as an ip address.
            for ip in kwargs.get("fetch_url_whitelist", "").split(',')
            if len(ip.strip()) > 0
        ]
        self.allow_user_creation = string_as_bool(kwargs.get("allow_user_creation", "True"))
        self.allow_user_deletion = string_as_bool(kwargs.get("allow_user_deletion", "False"))
        self.allow_user_dataset_purge = string_as_bool(kwargs.get("allow_user_dataset_purge", "True"))
        self.allow_user_impersonation = string_as_bool(kwargs.get("allow_user_impersonation", "False"))
        self.show_user_prepopulate_form = string_as_bool(kwargs.get("show_user_prepopulate_form", "False"))
        self.new_user_dataset_access_role_default_private = string_as_bool(kwargs.get("new_user_dataset_access_role_default_private", "False"))
        self.template_path = self.resolve_path(kwargs.get("template_path", "templates"))
        self.template_cache = self.resolve_path(kwargs.get("template_cache_path", os.path.join(self.data_dir, "compiled_templates")))
        self.job_queue_cleanup_interval = int(kwargs.get("job_queue_cleanup_interval", "5"))
        self.cluster_files_directory = self.resolve_path(kwargs.get("cluster_files_directory", os.path.join(self.data_dir, "pbs")))

        # Fall back to legacy job_working_directory config variable if set.
        default_jobs_directory = kwargs.get("job_working_directory", os.path.join(self.data_dir, "jobs_directory"))
        self.jobs_directory = self.resolve_path(kwargs.get("jobs_directory", default_jobs_directory))
        self.default_job_shell = kwargs.get("default_job_shell", "/bin/bash")
        preserve_python_environment = kwargs.get("preserve_python_environment", "legacy_only")
        if preserve_python_environment not in ["legacy_only", "legacy_and_local", "always"]:
            log.warning("preserve_python_environment set to unknown value [%s], defaulting to legacy_only")
            preserve_python_environment = "legacy_only"
        self.preserve_python_environment = preserve_python_environment
        self.nodejs_path = kwargs.get("nodejs_path", None)
        # Older default container cache path, I don't think anyone is using it anymore and it wasn't documented - we
        # should probably drop the backward compatiblity to save the path check.
        self.container_image_cache_path = self.resolve_path(kwargs.get("container_image_cache_path", os.path.join(self.data_dir, "container_images")))
        if not os.path.exists(self.container_image_cache_path):
            self.container_image_cache_path = self.resolve_path(kwargs.get("container_image_cache_path", os.path.join(self.data_dir, "container_cache")))
        self.outputs_to_working_directory = string_as_bool(kwargs.get('outputs_to_working_directory', False))
        self.output_size_limit = int(kwargs.get('output_size_limit', 0))
        self.retry_job_output_collection = int(kwargs.get('retry_job_output_collection', 0))
        self.check_job_script_integrity = string_as_bool(kwargs.get("check_job_script_integrity", True))
        self.mailing_join_addr = kwargs.get('mailing_join_addr', 'galaxy-announce-join@bx.psu.edu')
        self.error_email_to = kwargs.get('error_email_to', None)
        # activation_email was used until release_15.03
        activation_email = kwargs.get('activation_email', None)
        self.email_from = kwargs.get('email_from', activation_email)
        self.user_activation_on = string_as_bool(kwargs.get('user_activation_on', False))
        self.activation_grace_period = int(kwargs.get('activation_grace_period', 3))
        default_inactivity_box_content = ("Your account has not been activated yet. Feel free to browse around and see what's available, but"
                                          " you won't be able to upload data or run jobs until you have verified your email address.")
        self.inactivity_box_content = kwargs.get('inactivity_box_content', default_inactivity_box_content)
        self.terms_url = kwargs.get('terms_url', None)
        self.myexperiment_target_url = kwargs.get('my_experiment_target_url', 'www.myexperiment.org')
        self.instance_resource_url = kwargs.get('instance_resource_url', None)
        self.registration_warning_message = kwargs.get('registration_warning_message', None)
        self.ga_code = kwargs.get('ga_code', None)
        self.session_duration = int(kwargs.get('session_duration', 0))
        #  Get the disposable email domains blacklist file and its contents
        self.blacklist_location = kwargs.get('blacklist_file', None)
        self.blacklist_content = None
        if self.blacklist_location is not None:
            self.blacklist_file = self.resolve_path(kwargs.get('blacklist_file', None))
            try:
                with open(self.blacklist_file) as blacklist:
                    self.blacklist_content = [line.rstrip() for line in blacklist.readlines()]
            except IOError:
                log.error("CONFIGURATION ERROR: Can't open supplied blacklist file from path: " + str(self.blacklist_file))
        self.smtp_server = kwargs.get('smtp_server', None)
        self.smtp_username = kwargs.get('smtp_username', None)
        self.smtp_password = kwargs.get('smtp_password', None)
        self.smtp_ssl = kwargs.get('smtp_ssl', None)
        self.track_jobs_in_database = string_as_bool(kwargs.get('track_jobs_in_database', 'True'))
        self.expose_dataset_path = string_as_bool(kwargs.get('expose_dataset_path', 'False'))
        self.expose_potentially_sensitive_job_metrics = string_as_bool(kwargs.get('expose_potentially_sensitive_job_metrics', 'False'))
        self.enable_communication_server = string_as_bool(kwargs.get('enable_communication_server', 'False'))
        self.communication_server_host = kwargs.get('communication_server_host', 'http://localhost')
        self.communication_server_port = int(kwargs.get('communication_server_port', '7070'))
        self.persistent_communication_rooms = listify(kwargs.get("persistent_communication_rooms", []), do_strip=True)
        self.enable_openid = string_as_bool(kwargs.get('enable_openid', 'False'))
        self.enable_quotas = string_as_bool(kwargs.get('enable_quotas', 'False'))
        # Tasked job runner.
        self.use_tasked_jobs = string_as_bool(kwargs.get('use_tasked_jobs', False))
        self.local_task_queue_workers = int(kwargs.get("local_task_queue_workers", 2))
        # The transfer manager and deferred job queue
        self.enable_beta_job_managers = string_as_bool(kwargs.get('enable_beta_job_managers', 'False'))
        # Set this to go back to setting the object store in the tool request instead of
        # in the job handler.
        self.legacy_eager_objectstore_initialization = string_as_bool(kwargs.get('legacy_eager_objectstore_initialization', 'False'))
        # These workflow modules should not be considered part of Galaxy's
        # public API yet - the module state definitions may change and
        # workflows built using these modules may not function in the
        # future.
        self.enable_beta_workflow_modules = string_as_bool(kwargs.get('enable_beta_workflow_modules', 'False'))
        # Default format for the export of workflows.
        self.default_workflow_export_format = kwargs.get('default_workflow_export_format', 'ga')
        # These are not even beta - just experiments - don't use them unless
        # you want yours tools to be broken in the future.
        self.enable_beta_tool_formats = string_as_bool(kwargs.get('enable_beta_tool_formats', 'False'))
        # Beta containers interface used by GIEs
        self.enable_beta_containers_interface = string_as_bool(kwargs.get('enable_beta_containers_interface', 'False'))

        # Certain modules such as the pause module will automatically cause
        # workflows to be scheduled in job handlers the way all workflows will
        # be someday - the following two properties can also be used to force this
        # behavior in under conditions - namely for workflows that have a minimum
        # number of steps or that consume collections.
        self.force_beta_workflow_scheduled_min_steps = int(kwargs.get('force_beta_workflow_scheduled_min_steps', '250'))
        self.force_beta_workflow_scheduled_for_collections = string_as_bool(kwargs.get('force_beta_workflow_scheduled_for_collections', 'False'))

        self.history_local_serial_workflow_scheduling = string_as_bool(kwargs.get('history_local_serial_workflow_scheduling', 'False'))
        self.parallelize_workflow_scheduling_within_histories = string_as_bool(kwargs.get('parallelize_workflow_scheduling_within_histories', 'False'))
        self.maximum_workflow_invocation_duration = int(kwargs.get("maximum_workflow_invocation_duration", 2678400))
        self.maximum_workflow_jobs_per_scheduling_iteration = int(kwargs.get("maximum_workflow_jobs_per_scheduling_iteration", -1))

        workflow_resource_params_mapper = kwargs.get("workflow_resource_params_mapper", None)
        if not workflow_resource_params_mapper:
            workflow_resource_params_mapper = None
        elif ":" not in workflow_resource_params_mapper:
            # Assume it is not a Python function, so a file
            workflow_resource_params_mapper = self.resolve_path(workflow_resource_params_mapper)
        # else: a Python a function!
        self.workflow_resource_params_mapper = workflow_resource_params_mapper

        self.cache_user_job_count = string_as_bool(kwargs.get('cache_user_job_count', False))
        self.pbs_application_server = kwargs.get('pbs_application_server', "")
        self.pbs_dataset_server = kwargs.get('pbs_dataset_server', "")
        self.pbs_dataset_path = kwargs.get('pbs_dataset_path', "")
        self.pbs_stage_path = kwargs.get('pbs_stage_path', "")
        self.drmaa_external_runjob_script = kwargs.get('drmaa_external_runjob_script', None)
        self.drmaa_external_killjob_script = kwargs.get('drmaa_external_killjob_script', None)
        self.external_chown_script = kwargs.get('external_chown_script', None)
        self.real_system_username = kwargs.get('real_system_username', 'user_email')
        self.environment_setup_file = kwargs.get('environment_setup_file', None)
        self.use_heartbeat = string_as_bool(kwargs.get('use_heartbeat', 'False'))
        self.heartbeat_interval = int(kwargs.get('heartbeat_interval', 20))
        self.heartbeat_log = kwargs.get('heartbeat_log', None)
        self.monitor_thread_join_timeout = int(kwargs.get("monitor_thread_join_timeout", 30))
        self.log_actions = string_as_bool(kwargs.get('log_actions', 'False'))
        self.log_events = string_as_bool(kwargs.get('log_events', 'False'))
        self.sanitize_all_html = string_as_bool(kwargs.get('sanitize_all_html', True))
        self.sanitize_whitelist_file = self.resolve_path(kwargs.get('sanitize_whitelist_file', "config/sanitize_whitelist.txt"))
        self.serve_xss_vulnerable_mimetypes = string_as_bool(kwargs.get('serve_xss_vulnerable_mimetypes', False))
        self.allowed_origin_hostnames = self._parse_allowed_origin_hostnames(kwargs)
        if "trust_jupyter_notebook_conversion" in kwargs:
            trust_jupyter_notebook_conversion = string_as_bool(kwargs.get('trust_jupyter_notebook_conversion', False))
        else:
            trust_jupyter_notebook_conversion = string_as_bool(kwargs.get('trust_ipython_notebook_conversion', False))
        self.trust_jupyter_notebook_conversion = trust_jupyter_notebook_conversion
        self.enable_old_display_applications = string_as_bool(kwargs.get("enable_old_display_applications", "True"))
        self.brand = kwargs.get('brand', None)
        self.show_welcome_with_login = string_as_bool(kwargs.get("show_welcome_with_login", "False"))
        self.visualizations_visible = string_as_bool(kwargs.get('visualizations_visible', True))
        # Configuration for the message box directly below the masthead.
        self.message_box_visible = string_as_bool(kwargs.get('message_box_visible', False))
        self.message_box_class = kwargs.get('message_box_class', 'info')
        self.support_url = kwargs.get('support_url', 'https://galaxyproject.org/support')
        self.citation_url = kwargs.get('citation_url', 'https://galaxyproject.org/citing-galaxy')
        self.helpsite_url = kwargs.get('helpsite_url', None)
        self.wiki_url = kwargs.get('wiki_url', 'https://galaxyproject.org/')
        self.blog_url = kwargs.get('blog_url', None)
        self.screencasts_url = kwargs.get('screencasts_url', None)
        self.genomespace_ui_url = kwargs.get('genomespace_ui_url', 'https://gsui.genomespace.org/jsui/')
        self.library_import_dir = kwargs.get('library_import_dir', None)
        self.user_library_import_dir = kwargs.get('user_library_import_dir', None)
        self.user_library_import_symlink_whitelist = listify(kwargs.get('user_library_import_symlink_whitelist', []), do_strip=True)
        self.user_library_import_check_permissions = string_as_bool(kwargs.get('user_library_import_check_permissions', False))
        self.user_library_import_dir_auto_creation = string_as_bool(kwargs.get('user_library_import_dir_auto_creation', False)) if self.user_library_import_dir else False
        # Searching data libraries
        self.chunk_upload_size = int(kwargs.get('chunk_upload_size', 104857600))
        self.ftp_upload_dir = kwargs.get('ftp_upload_dir', None)
        self.ftp_upload_dir_identifier = kwargs.get('ftp_upload_dir_identifier', 'email')  # attribute on user - email, username, id, etc...
        self.ftp_upload_dir_template = kwargs.get('ftp_upload_dir_template', '${ftp_upload_dir}%s${ftp_upload_dir_identifier}' % os.path.sep)
        self.ftp_upload_purge = string_as_bool(kwargs.get('ftp_upload_purge', 'True'))
        self.ftp_upload_site = kwargs.get('ftp_upload_site', None)
        self.allow_path_paste = string_as_bool(kwargs.get('allow_path_paste', False))
        # Support older library-specific path paste option but just default to the new
        # allow_path_paste value.
        self.allow_library_path_paste = string_as_bool(kwargs.get('allow_library_path_paste', self.allow_path_paste))
        self.disable_library_comptypes = kwargs.get('disable_library_comptypes', '').lower().split(',')
        self.sniff_compressed_dynamic_datatypes_default = string_as_bool(kwargs.get("sniff_compressed_dynamic_datatypes_default", True))
        self.check_upload_content = string_as_bool(kwargs.get('check_upload_content', True))
        self.watch_tools = kwargs.get('watch_tools', 'false')
        self.watch_tool_data_dir = kwargs.get('watch_tool_data_dir', 'false')
        self.watch_job_rules = kwargs.get('watch_job_rules', 'false')
        self.watch_core_config = kwargs.get('watch_core_config', 'false')
        # On can mildly speed up Galaxy startup time by disabling index of help,
        # not needed on production systems but useful if running many functional tests.
        self.index_tool_help = string_as_bool(kwargs.get("index_tool_help", True))
        self.tool_labels_boost = kwargs.get("tool_labels_boost", 1)
        default_tool_test_data_directories = os.environ.get("GALAXY_TEST_FILE_DIR", self.resolve_path("test-data"))
        self.tool_test_data_directories = kwargs.get("tool_test_data_directories", default_tool_test_data_directories)
        # Deployers may either specify a complete list of mapping files or get the default for free and just
        # specify a local mapping file to adapt and extend the default one.
        if "conda_mapping_files" not in kwargs:
            conda_mapping_files = [
                self.local_conda_mapping_file,
                os.path.join(self.root, "lib", "galaxy", "tool_util", "deps", "resolvers", "default_conda_mapping.yml"),
            ]
            # dependency resolution options are consumed via config_dict - so don't populate
            # self, populate config_dict
            self.config_dict["conda_mapping_files"] = conda_mapping_files

        self.enable_mulled_containers = string_as_bool(kwargs.get('enable_mulled_containers', 'True'))
        containers_resolvers_config_file = kwargs.get('containers_resolvers_config_file', None)
        if containers_resolvers_config_file:
            containers_resolvers_config_file = self.resolve_path(containers_resolvers_config_file)
        self.containers_resolvers_config_file = containers_resolvers_config_file

        involucro_path = kwargs.get('involucro_path')
        if involucro_path is None:
            target_dir = kwargs.get("tool_dependency_dir")
            if target_dir in [None, "none"]:
                target_dir = os.path.join(self.data_dir, "dependencies")
            involucro_path = os.path.join(target_dir, "involucro")
        self.involucro_path = self.resolve_path(involucro_path)
        self.involucro_auto_init = string_as_bool(kwargs.get('involucro_auto_init', True))
        mulled_channels = kwargs.get('mulled_channels')
        if mulled_channels:
            self.mulled_channels = [c.strip() for c in mulled_channels.split(',')]
        else:
            self.mulled_channels = DEFAULT_CHANNELS

        default_job_resubmission_condition = kwargs.get('default_job_resubmission_condition', '')
        if not default_job_resubmission_condition.strip():
            default_job_resubmission_condition = None
        self.default_job_resubmission_condition = default_job_resubmission_condition

        # Configuration options for taking advantage of nginx features
        self.upstream_gzip = string_as_bool(kwargs.get('upstream_gzip', False))
        self.apache_xsendfile = string_as_bool(kwargs.get('apache_xsendfile', False))
        self.nginx_x_accel_redirect_base = kwargs.get('nginx_x_accel_redirect_base', False)
        self.nginx_upload_store = kwargs.get('nginx_upload_store', False)
        self.nginx_upload_path = kwargs.get('nginx_upload_path', False)
        self.nginx_upload_job_files_store = kwargs.get('nginx_upload_job_files_store', False)
        self.nginx_upload_job_files_path = kwargs.get('nginx_upload_job_files_path', False)
        if self.nginx_upload_store:
            self.nginx_upload_store = os.path.abspath(self.nginx_upload_store)
        self.object_store = kwargs.get('object_store', 'disk')
        self.object_store_check_old_style = string_as_bool(kwargs.get('object_store_check_old_style', False))
        self.object_store_cache_path = self.resolve_path(kwargs.get("object_store_cache_path", os.path.join(self.data_dir, "object_store_cache")))
        self.object_store_store_by = kwargs.get("object_store_store_by", "id")

        # Handle AWS-specific config options for backward compatibility
        if kwargs.get('aws_access_key', None) is not None:
            self.os_access_key = kwargs.get('aws_access_key', None)
            self.os_secret_key = kwargs.get('aws_secret_key', None)
            self.os_bucket_name = kwargs.get('s3_bucket', None)
            self.os_use_reduced_redundancy = kwargs.get('use_reduced_redundancy', False)
        else:
            self.os_access_key = kwargs.get('os_access_key', None)
            self.os_secret_key = kwargs.get('os_secret_key', None)
            self.os_bucket_name = kwargs.get('os_bucket_name', None)
            self.os_use_reduced_redundancy = kwargs.get('os_use_reduced_redundancy', False)
        self.os_host = kwargs.get('os_host', None)
        self.os_port = kwargs.get('os_port', None)
        self.os_is_secure = string_as_bool(kwargs.get('os_is_secure', True))
        self.os_conn_path = kwargs.get('os_conn_path', '/')
        self.object_store_cache_size = float(kwargs.get('object_store_cache_size', -1))
        self.distributed_object_store_config_file = kwargs.get('distributed_object_store_config_file', None)
        if self.distributed_object_store_config_file is not None:
            self.distributed_object_store_config_file = self.resolve_path(self.distributed_object_store_config_file)
        self.irods_root_collection_path = kwargs.get('irods_root_collection_path', None)
        self.irods_default_resource = kwargs.get('irods_default_resource', None)
        # Heartbeat log file name override
        if self.global_conf is not None and 'heartbeat_log' in self.global_conf:
            self.heartbeat_log = self.global_conf['heartbeat_log']
        if self.heartbeat_log is None:
            self.heartbeat_log = 'heartbeat_{server_name}.log'
        # Determine which 'server:' this is
        self.server_name = 'main'
        for arg in sys.argv:
            # Crummy, but PasteScript does not give you a way to determine this
            if arg.lower().startswith('--server-name='):
                self.server_name = arg.split('=', 1)[-1]
        # Allow explicit override of server name in config params
        if "server_name" in kwargs:
            self.server_name = kwargs.get("server_name")
        # The application stack code may manipulate the server name. It also needs to be accessible via the get() method
        # for galaxy.util.facts()
        self.config_dict['base_server_name'] = self.base_server_name = self.server_name
        # Store all configured server names for the message queue routing
        self.server_names = []
        for section in self.global_conf_parser.sections():
            if section.startswith('server:'):
                self.server_names.append(section.replace('server:', '', 1))

        # Default URL (with schema http/https) of the Galaxy instance within the
        # local network - used to remotely communicate with the Galaxy API.
        web_port = kwargs.get("galaxy_infrastructure_web_port", None)
        self.galaxy_infrastructure_web_port = web_port
        galaxy_infrastructure_url = kwargs.get('galaxy_infrastructure_url', None)
        galaxy_infrastructure_url_set = True
        if galaxy_infrastructure_url is None:
            # Still provide a default but indicate it was not explicitly set
            # so dependending on the context a better default can be used (
            # request url in a web thread, Docker parent in IE stuff, etc...)
            galaxy_infrastructure_url = "http://localhost"
            web_port = self.galaxy_infrastructure_web_port
            if web_port:
                galaxy_infrastructure_url += ":%s" % (web_port)
            galaxy_infrastructure_url_set = False
        if "HOST_IP" in galaxy_infrastructure_url:
            galaxy_infrastructure_url = string.Template(galaxy_infrastructure_url).safe_substitute({
                'HOST_IP': socket.gethostbyname(socket.gethostname())
            })
        self.galaxy_infrastructure_url = galaxy_infrastructure_url
        self.galaxy_infrastructure_url_set = galaxy_infrastructure_url_set

        # Asynchronous execution process pools - limited functionality for now, attach_to_pools is designed to allow
        # webless Galaxy server processes to attach to arbitrary message queues (e.g. as job handlers) so they do not
        # have to be explicitly defined as such in the job configuration.
        self.attach_to_pools = kwargs.get('attach_to_pools', []) or []

        # Store advanced job management config
        self.job_handlers = [x.strip() for x in kwargs.get('job_handlers', self.server_name).split(',')]
        self.default_job_handlers = [x.strip() for x in kwargs.get('default_job_handlers', ','.join(self.job_handlers)).split(',')]
        # Galaxy internal control queue configuration.
        # If specified in universe, use it, otherwise we use whatever 'real'
        # database is specified.  Lastly, we create and use new sqlite database
        # (to minimize locking) as a final option.
        if 'amqp_internal_connection' in kwargs:
            self.amqp_internal_connection = kwargs.get('amqp_internal_connection')
            # TODO Get extra amqp args as necessary for ssl
        elif 'database_connection' in kwargs:
            self.amqp_internal_connection = "sqlalchemy+" + self.database_connection
        else:
            self.amqp_internal_connection = "sqlalchemy+sqlite:///%s?isolation_level=IMMEDIATE" % os.path.join(self.data_dir, "control.sqlite")
        self.pretty_datetime_format = expand_pretty_datetime_format(kwargs.get('pretty_datetime_format', '$locale (UTC)'))
        try:
            with open(self.user_preferences_extra_conf_path, 'r') as stream:
                self.user_preferences_extra = yaml.safe_load(stream)
        except Exception:
            if self.user_preferences_extra_conf_path_set:
                log.warning('Config file (%s) could not be found or is malformed.' % self.user_preferences_extra_conf_path)
            self.user_preferences_extra = {'preferences': {}}

        self.default_locale = kwargs.get('default_locale', None)
        self.master_api_key = kwargs.get('master_api_key', None)
        if self.master_api_key == "changethis":  # default in sample config file
            raise ConfigurationError("Insecure configuration, please change master_api_key to something other than default (changethis)")

        # Experimental: This will not be enabled by default and will hide
        # nonproduction code.
        # The api_folders refers to whether the API exposes the /folders section.
        self.api_folders = string_as_bool(kwargs.get('api_folders', False))
        # This is for testing new library browsing capabilities.
        self.new_lib_browse = string_as_bool(kwargs.get('new_lib_browse', False))
        # Logging configuration with logging.config.configDict:
        self.logging = kwargs.get('logging', None)
        # Error logging with sentry
        self.sentry_dsn = kwargs.get('sentry_dsn', None)
        # Statistics and profiling with statsd
        self.statsd_host = kwargs.get('statsd_host', '')
        self.statsd_port = int(kwargs.get('statsd_port', 8125))
        self.statsd_prefix = kwargs.get('statsd_prefix', 'galaxy')
        self.statsd_influxdb = string_as_bool(kwargs.get('statsd_influxdb', False))
        # Logging with fluentd
        self.fluent_log = string_as_bool(kwargs.get('fluent_log', False))
        self.fluent_host = kwargs.get('fluent_host', 'localhost')
        self.fluent_port = int(kwargs.get('fluent_port', 24224))

        # directory where the visualization registry searches for plugins
        self.visualization_plugins_directory = kwargs.get(
            'visualization_plugins_directory', 'config/plugins/visualizations')
        ie_dirs = kwargs.get('interactive_environment_plugins_directory', None)
        self.gie_dirs = [d.strip() for d in (ie_dirs.split(",") if ie_dirs else [])]
        if ie_dirs and not self.visualization_plugins_directory:
            self.visualization_plugins_directory = ie_dirs
        elif ie_dirs:
            self.visualization_plugins_directory += ",%s" % ie_dirs

        self.gie_swarm_mode = string_as_bool(kwargs.get('interactive_environment_swarm_mode', False))

        self.proxy_session_map = self.resolve_path(kwargs.get("dynamic_proxy_session_map", os.path.join(self.data_dir, "session_map.sqlite")))
        self.manage_dynamic_proxy = string_as_bool(kwargs.get("dynamic_proxy_manage", "True"))  # Set to false if being launched externally
        self.dynamic_proxy_debug = string_as_bool(kwargs.get("dynamic_proxy_debug", "False"))
        self.dynamic_proxy_bind_port = int(kwargs.get("dynamic_proxy_bind_port", "8800"))
        self.dynamic_proxy_bind_ip = kwargs.get("dynamic_proxy_bind_ip", "0.0.0.0")
        self.dynamic_proxy_external_proxy = string_as_bool(kwargs.get("dynamic_proxy_external_proxy", "False"))
        self.dynamic_proxy_prefix = kwargs.get("dynamic_proxy_prefix", "gie_proxy")

        self.dynamic_proxy = kwargs.get("dynamic_proxy", "node")
        self.dynamic_proxy_golang_noaccess = kwargs.get("dynamic_proxy_golang_noaccess", 60)
        self.dynamic_proxy_golang_clean_interval = kwargs.get("dynamic_proxy_golang_clean_interval", 10)
        self.dynamic_proxy_golang_docker_address = kwargs.get("dynamic_proxy_golang_docker_address", "unix:///var/run/docker.sock")
        self.dynamic_proxy_golang_api_key = kwargs.get("dynamic_proxy_golang_api_key", None)

        # InteractiveTools propagator mapping file
        self.interactivetool_map = self.resolve_path(kwargs.get("interactivetools_map", os.path.join(self.data_dir, "interactivetools_map.sqlite")))
        self.interactivetool_prefix = kwargs.get("interactivetools_prefix", "interactivetool")
        self.interactivetools_enable = string_as_bool(kwargs.get('interactivetools_enable', False))

        # Default chunk size for chunkable datatypes -- 64k
        self.display_chunk_size = int(kwargs.get('display_chunk_size', 65536))

        self.citation_cache_type = kwargs.get("citation_cache_type", "file")
        self.citation_cache_data_dir = self.resolve_path(kwargs.get("citation_cache_data_dir", os.path.join(self.data_dir, "citations/data")))
        self.citation_cache_lock_dir = self.resolve_path(kwargs.get("citation_cache_lock_dir", os.path.join(self.data_dir, "citations/locks")))

        self.containers_conf = parse_containers_config(self.containers_config_file)

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
        self.enable_beta_gdpr = string_as_bool(kwargs.get("enable_beta_gdpr", False))
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

            LOGGING_CONFIG_DEFAULT['formatters']['brief'] = {
                'format': '%(asctime)s %(levelname)-8s %(name)-15s %(message)s'
            }
            LOGGING_CONFIG_DEFAULT['handlers']['compliance_log'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'brief',
                'filename': 'compliance.log',
                'backupCount': 0,
            }
            LOGGING_CONFIG_DEFAULT['loggers']['COMPLIANCE'] = {
                'handlers': ['compliance_log'],
                'level': 'DEBUG',
                'qualname': 'COMPLIANCE'
            }

        log_destination = kwargs.get("log_destination", None)
        if log_destination == "stdout":
            LOGGING_CONFIG_DEFAULT['handlers']['console'] = {
                'class': 'logging.StreamHandler',
                'formatter': 'stack',
                'level': 'DEBUG',
                'stream': 'ext://sys.stdout',
                'filters': ['stack']
            }
        elif log_destination:
            LOGGING_CONFIG_DEFAULT['handlers']['console'] = {
                'class': 'logging.FileHandler',
                'formatter': 'stack',
                'level': 'DEBUG',
                'filename': kwargs['log_destination'],
                'filters': ['stack']
            }

    def _set_reloadable_properties(self, kwargs):
        reloadable_config_options = get_reloadable_config_options()
        for key, default_value in reloadable_config_options.items():
            value = kwargs.get(key) or default_value
            setattr(self, key, value)

    def update_reloadable_property(self, key, value):
        # TODO: after config_schema.yml is read only once at startup, add this:
        # "if key in reloadable_config_options" (just a safety measure)
        setattr(self, key, value)

    @property
    def admin_users(self):
        return self._admin_users

    @admin_users.setter
    def admin_users(self, value):
        self._admin_users = value
        self.admin_users_list = [u.strip() for u in value.split(',') if u]

    @property
    def sentry_dsn_public(self):
        """
        Sentry URL with private key removed for use in client side scripts,
        sentry server will need to be configured to accept events
        """
        if self.sentry_dsn:
            return re.sub(r"^([^:/?#]+:)?//(\w+):(\w+)", r"\1//\2", self.sentry_dsn)
        else:
            return None

    def parse_config_file_options(self, kwargs):
        """
        Backwards compatibility for config files moved to the config/ dir.
        """
        defaults = dict(
            auth_config_file=[self._in_config_dir('auth_conf.xml')],
            build_sites_config_file=[self._in_config_dir('build_sites.yml')],
            containers_config_file=[self._in_config_dir('containers_conf.yml')],
            data_manager_config_file=[self._in_config_dir('data_manager_conf.xml')],
            datatypes_config_file=[self._in_config_dir('datatypes_conf.xml'), self._in_sample_dir('datatypes_conf.xml.sample')],
            dependency_resolvers_config_file=[self._in_config_dir('dependency_resolvers_conf.xml')],
            error_report_file=[self._in_config_dir('error_report.yml')],
            job_config_file=[self._in_config_dir('job_conf.xml')],
            job_metrics_config_file=[self._in_config_dir('job_metrics_conf.xml'), self._in_sample_dir('job_metrics_conf.xml.sample')],
            job_resource_params_file=[self._in_config_dir('job_resource_params_conf.xml')],
            local_conda_mapping_file=[self._in_config_dir('local_conda_mapping.yml')],
            migrated_tools_config=[self._in_config_dir('migrated_tools_conf.xml')],
            modules_mapping_files=[self._in_config_dir('environment_modules_mapping.yml')],
            object_store_config_file=[self._in_config_dir('object_store_conf.xml')],
            oidc_backends_config_file=[self._in_config_dir('oidc_backends_config.xml')],
            oidc_config_file=[self._in_config_dir('oidc_config.xml')],
            shed_data_manager_config_file=[self._in_mutable_config_dir('shed_data_manager_conf.xml')],
            shed_tool_config_file=[self._in_mutable_config_dir('shed_tool_conf.xml')],
            shed_tool_data_table_config=[self._in_mutable_config_dir('shed_tool_data_table_conf.xml')],
            tool_destinations_config_file=[self._in_config_dir('tool_destinations.yml')],
            tool_sheds_config_file=[self._in_config_dir('tool_sheds_conf.xml')],
            user_preferences_extra_conf_path=[self._in_config_dir('user_preferences_extra_conf.yml')],
            workflow_resource_params_file=[self._in_config_dir('workflow_resource_params_conf.xml')],
            workflow_schedulers_config_file=[self._in_config_dir('workflow_schedulers_conf.xml')],
        )
        listify_defaults = {
            'tool_data_table_config_path': [
                self._in_config_dir('tool_data_table_conf.xml'),
                self._in_sample_dir('tool_data_table_conf.xml.sample')],
            'tool_config_file': [
                self._in_config_dir('tool_conf.xml'),
                self._in_sample_dir('tool_conf.xml.sample')]
        }

        self._parse_config_file_options(defaults, listify_defaults, kwargs)

        # Backwards compatibility for names used in too many places to fix
        self.datatypes_config = self.datatypes_config_file
        self.tool_configs = self.tool_config_file

    def reload_sanitize_whitelist(self, explicit=True):
        self.sanitize_whitelist = []
        try:
            with open(self.sanitize_whitelist_file, 'rt') as f:
                for line in f.readlines():
                    if not line.startswith("#"):
                        self.sanitize_whitelist.append(line.strip())
        except IOError:
            if explicit:
                log.warning("Sanitize log file explicitly specified as '%s' but does not exist, continuing with no tools whitelisted.", self.sanitize_whitelist_file)

    def get(self, key, default):
        return self.config_dict.get(key, default)

    def get_bool(self, key, default):
        if key in self.config_dict:
            return string_as_bool(self.config_dict[key])
        else:
            return default

    def ensure_tempdir(self):
        self._ensure_directory(self.new_file_path)

    def _ensure_directory(self, path):
        if path not in [None, False] and not os.path.isdir(path):
            try:
                os.makedirs(path)
            except Exception as e:
                raise ConfigurationError("Unable to create missing directory: %s\n%s" % (path, unicodify(e)))

    def check(self):
        paths_to_check = [self.tool_data_path, self.data_dir, self.mutable_config_dir]
        # Check that required directories exist
        for path in paths_to_check:
            if path not in [None, False] and not os.path.isdir(path):
                try:
                    os.makedirs(path)
                except Exception as e:
                    raise ConfigurationError("Unable to create missing directory: %s\n%s" % (path, unicodify(e)))
        # Create the directories that it makes sense to create
        for path in (self.new_file_path, self.template_cache, self.ftp_upload_dir,
                     self.library_import_dir, self.user_library_import_dir,
                     self.nginx_upload_store, self.object_store_cache_path):
            self._ensure_directory(path)
        # Check that required files exist
        tool_configs = self.tool_configs
        for path in tool_configs:
            if not os.path.exists(path) and path not in (self.shed_tool_config_file, self.migrated_tools_config):
                raise ConfigurationError("Tool config file not found: %s" % path)
        for datatypes_config in listify(self.datatypes_config):
            if not os.path.isfile(datatypes_config):
                raise ConfigurationError("Datatypes config file not found: %s" % datatypes_config)
        # Check for deprecated options.
        for key in self.config_dict.keys():
            if key in self.deprecated_options:
                log.warning("Config option '%s' is deprecated and will be removed in a future release.  Please consult the latest version of the sample configuration file." % key)

    def is_admin_user(self, user):
        """
        Determine if the provided user is listed in `admin_users`.

        NOTE: This is temporary, admin users will likely be specified in the
              database in the future.
        """
        return user is not None and user.email in self.admin_users_list

    def resolve_path(self, path):
        """ Resolve a path relative to Galaxy's root.
        """
        return os.path.join(self.root, path)

    @staticmethod
    def _parse_allowed_origin_hostnames(kwargs):
        """
        Parse a CSV list of strings/regexp of hostnames that should be allowed
        to use CORS and will be sent the Access-Control-Allow-Origin header.
        """
        allowed_origin_hostnames = listify(kwargs.get('allowed_origin_hostnames', None))
        if not allowed_origin_hostnames:
            return None

        def parse(string):
            # a string enclosed in fwd slashes will be parsed as a regexp: e.g. /<some val>/
            if string[0] == '/' and string[-1] == '/':
                string = string[1:-1]
                return re.compile(string, flags=(re.UNICODE))
            return string

        return [parse(v) for v in allowed_origin_hostnames if v]


# legacy naming
Configuration = GalaxyAppConfiguration


def reload_config_options(current_config, path=None):
    """ Reload modified reloadable config options """
    modified_config = read_properties_from_file(current_config.config_file)
    reloadable_config_options = get_reloadable_config_options()
    for option in reloadable_config_options:
        if option in modified_config:
            if getattr(current_config, option) != modified_config[option]:
                current_config.update_reloadable_property(option, modified_config[option])
                log.info('Reloaded %s' % option)


def get_reloadable_config_options():
    schema = AppSchema(GALAXY_CONFIG_SCHEMA_PATH, GALAXY_APP_NAME)
    return schema.get_reloadable_option_defaults()


def get_database_engine_options(kwargs, model_prefix=''):
    """
    Allow options for the SQLAlchemy database engine to be passed by using
    the prefix "database_engine_option".
    """
    conversions = {
        'convert_unicode': string_as_bool,
        'pool_timeout': int,
        'echo': string_as_bool,
        'echo_pool': string_as_bool,
        'pool_recycle': int,
        'pool_size': int,
        'max_overflow': int,
        'pool_threadlocal': string_as_bool,
        'server_side_cursors': string_as_bool
    }
    prefix = "%sdatabase_engine_option_" % model_prefix
    prefix_len = len(prefix)
    rval = {}
    for key, value in kwargs.items():
        if key.startswith(prefix):
            key = key[prefix_len:]
            if key in conversions:
                value = conversions[key](value)
            rval[key] = value
    return rval


def get_database_url(config):
    db_url = config.database_connection
    return db_url


def init_models_from_config(config, map_install_models=False, object_store=None, trace_logger=None):
    db_url = get_database_url(config)
    model = mapping.init(
        config.file_path,
        db_url,
        config.database_engine_options,
        map_install_models=map_install_models,
        database_query_profiling_proxy=config.database_query_profiling_proxy,
        object_store=object_store,
        trace_logger=trace_logger,
        use_pbkdf2=config.get_bool('use_pbkdf2', True),
        slow_query_log_threshold=config.slow_query_log_threshold,
        thread_local_log=config.thread_local_log
    )
    return model


def configure_logging(config):
    """Allow some basic logging configuration to be read from ini file.

    This should be able to consume either a galaxy.config.Configuration object
    or a simple dictionary of configuration variables.
    """
    # Get root logger
    logging.addLevelName(LOGLV_TRACE, "TRACE")
    root = logging.getLogger()
    # PasteScript will have already configured the logger if the
    # 'loggers' section was found in the config file, otherwise we do
    # some simple setup using the 'log_*' values from the config.
    parser = getattr(config, "global_conf_parser", None)
    if parser:
        paste_configures_logging = config.global_conf_parser.has_section("loggers")
    else:
        paste_configures_logging = False
    auto_configure_logging = not paste_configures_logging and string_as_bool(config.get("auto_configure_logging", "True"))
    if auto_configure_logging:
        logging_conf = config.get('logging', None)
        if logging_conf is None:
            # if using the default logging config, honor the log_level setting
            logging_conf = LOGGING_CONFIG_DEFAULT
            if config.get('log_level', 'DEBUG') != 'DEBUG':
                logging_conf['handlers']['console']['level'] = config.get('log_level', 'DEBUG')
        # configure logging with logging dict in config, template *FileHandler handler filenames with the `filename_template` option
        for name, conf in logging_conf.get('handlers', {}).items():
            if conf['class'].startswith('logging.') and conf['class'].endswith('FileHandler') and 'filename_template' in conf:
                conf['filename'] = conf.pop('filename_template').format(**get_stack_facts(config=config))
                logging_conf['handlers'][name] = conf
        logging.config.dictConfig(logging_conf)
    if getattr(config, "sentry_dsn", None):
        from raven.handlers.logging import SentryHandler
        sentry_handler = SentryHandler(config.sentry_dsn)
        sentry_handler.setLevel(logging.WARN)
        register_postfork_function(root.addHandler, sentry_handler)


class ConfiguresGalaxyMixin(object):
    """ Shared code for configuring Galaxy-like app objects.
    """

    def _configure_genome_builds(self, data_table_name="__dbkeys__", load_old_style=True):
        self.genome_builds = GenomeBuilds(self, data_table_name=data_table_name, load_old_style=load_old_style)

    def wait_for_toolbox_reload(self, old_toolbox):
        timer = ExecutionTimer()
        log.debug('Waiting for toolbox reload')
        # Wait till toolbox reload has been triggered (or more than 60 seconds have passed)
        while timer.elapsed < 60:
            if self.toolbox.has_reloaded(old_toolbox):
                log.debug('Finished waiting for toolbox reload %s', timer)
                break
            time.sleep(0.1)
        else:
            log.warning('Waiting for toolbox reload timed out after 60 seconds')

    def _configure_toolbox(self):
        from galaxy import tools
        from galaxy.managers.citations import CitationsManager
        from galaxy.tool_util.deps import containers
        from galaxy.tool_util.deps.dependencies import AppInfo
        import galaxy.tools.search

        self.citations_manager = CitationsManager(self)

        from galaxy.managers.tools import DynamicToolManager
        self.dynamic_tools_manager = DynamicToolManager(self)
        self._toolbox_lock = threading.RLock()
        # shed_tool_config_file has been set, add it to tool_configs
        if self.config.shed_tool_config_file_set:
            self.config.tool_configs.append(self.config.shed_tool_config_file)
        # The value of migrated_tools_config is the file reserved for containing only those tools that have been
        # eliminated from the distribution and moved to the tool shed. If migration checking is disabled, only add it if
        # it exists (since this may be an existing deployment where migrations were previously run).
        if ((self.config.check_migrate_tools or os.path.exists(self.config.migrated_tools_config))
                and self.config.migrated_tools_config not in self.config.tool_configs):
            self.config.tool_configs.append(self.config.migrated_tools_config)
        self.toolbox = tools.ToolBox(self.config.tool_configs, self.config.tool_path, self)
        # If no shed-enabled tool config file has been loaded, we append a default shed_tool_conf.xml
        if not self.config.shed_tool_config_file_set and not self.toolbox.dynamic_confs():
            # This seems like the likely case for problems in older deployments
            if self.config.tool_config_file_set:
                log.warning(
                    "The default shed tool config file (%s) has been added to the tool_config_file option, if this is "
                    "not the desired behavior, please set shed_tool_config_file to your primary shed-enabled tool "
                    "config file", self.config.shed_tool_config_file
                )
            self.config.tool_configs.append(self.config.shed_tool_config_file)
            self.toolbox._init_tools_from_config(self.config.shed_tool_config_file)
        galaxy_root_dir = os.path.abspath(self.config.root)
        file_path = os.path.abspath(getattr(self.config, "file_path"))
        app_info = AppInfo(
            galaxy_root_dir=galaxy_root_dir,
            default_file_path=file_path,
            outputs_to_working_directory=self.config.outputs_to_working_directory,
            container_image_cache_path=self.config.container_image_cache_path,
            library_import_dir=self.config.library_import_dir,
            enable_mulled_containers=self.config.enable_mulled_containers,
            containers_resolvers_config_file=self.config.containers_resolvers_config_file,
            involucro_path=self.config.involucro_path,
            involucro_auto_init=self.config.involucro_auto_init,
            mulled_channels=self.config.mulled_channels,
        )
        self.container_finder = containers.ContainerFinder(app_info)
        self._set_enabled_container_types()
        index_help = getattr(self.config, "index_tool_help", True)
        self.toolbox_search = galaxy.tools.search.ToolBoxSearch(self.toolbox, index_help)
        self.reindex_tool_search()

    def reindex_tool_search(self):
        # Call this when tools are added or removed.
        self.toolbox_search.build_index(tool_cache=self.tool_cache)
        self.tool_cache.reset_status()

    def _set_enabled_container_types(self):
        container_types_to_destinations = collections.defaultdict(list)
        for destinations in self.job_config.destinations.values():
            for destination in destinations:
                for enabled_container_type in self.container_finder._enabled_container_types(destination.params):
                    container_types_to_destinations[enabled_container_type].append(destination)
        self.toolbox.dependency_manager.set_enabled_container_types(container_types_to_destinations)
        self.toolbox.dependency_manager.resolver_classes.update(self.container_finder.container_registry.resolver_classes)
        self.toolbox.dependency_manager.dependency_resolvers.extend(self.container_finder.container_registry.container_resolvers)

    def _configure_tool_data_tables(self, from_shed_config):
        from galaxy.tools.data import ToolDataTableManager

        # Initialize tool data tables using the config defined by self.config.tool_data_table_config_path.
        self.tool_data_tables = ToolDataTableManager(tool_data_path=self.config.tool_data_path,
                                                     config_filename=self.config.tool_data_table_config_path)
        # Load additional entries defined by self.config.shed_tool_data_table_config into tool data tables.
        try:
            self.tool_data_tables.load_from_config_file(config_filename=self.config.shed_tool_data_table_config,
                                                        tool_data_path=self.tool_data_tables.tool_data_path,
                                                        from_shed_config=from_shed_config)
        except (OSError, IOError) as exc:
            # Missing shed_tool_data_table_config is okay if it's the default
            if exc.errno != errno.ENOENT or self.config.shed_tool_data_table_config_set:
                raise

    def _configure_datatypes_registry(self, installed_repository_manager=None):
        from galaxy.datatypes import registry
        # Create an empty datatypes registry.
        self.datatypes_registry = registry.Registry(self.config)
        if installed_repository_manager:
            # Load proprietary datatypes defined in datatypes_conf.xml files in all installed tool shed repositories.  We
            # load proprietary datatypes before datatypes in the distribution because Galaxy's default sniffers include some
            # generic sniffers (eg text,xml) which catch anything, so it's impossible for proprietary sniffers to be used.
            # However, if there is a conflict (2 datatypes with the same extension) between a proprietary datatype and a datatype
            # in the Galaxy distribution, the datatype in the Galaxy distribution will take precedence.  If there is a conflict
            # between 2 proprietary datatypes, the datatype from the repository that was installed earliest will take precedence.
            installed_repository_manager.load_proprietary_datatypes()
        # Load the data types in the Galaxy distribution, which are defined in self.config.datatypes_config.
        datatypes_configs = self.config.datatypes_config
        for datatypes_config in listify(datatypes_configs):
            # Setting override=False would make earlier files would take
            # precedence - but then they wouldn't override tool shed
            # datatypes.
            self.datatypes_registry.load_datatypes(self.config.root, datatypes_config, override=True)

    def _configure_object_store(self, **kwds):
        from galaxy.objectstore import build_object_store_from_config
        self.object_store = build_object_store_from_config(self.config, **kwds)

    def _configure_security(self):
        from galaxy.security import idencoding
        self.security = idencoding.IdEncodingHelper(id_secret=self.config.id_secret)

    def _configure_tool_shed_registry(self):
        import tool_shed.tool_shed_registry

        # Set up the tool sheds registry
        if os.path.isfile(self.config.tool_sheds_config_file):
            self.tool_shed_registry = tool_shed.tool_shed_registry.Registry(self.config.tool_sheds_config_file)
        else:
            self.tool_shed_registry = tool_shed.tool_shed_registry.Registry()

    def _configure_models(self, check_migrate_databases=False, check_migrate_tools=False, config_file=None):
        """
        Preconditions: object_store must be set on self.
        """
        db_url = get_database_url(self.config)
        install_db_url = self.config.install_database_connection
        # TODO: Consider more aggressive check here that this is not the same
        # database file under the hood.
        combined_install_database = not(install_db_url and install_db_url != db_url)
        install_db_url = install_db_url or db_url
        install_database_options = self.config.database_engine_options if combined_install_database else self.config.install_database_engine_options

        if self.config.database_wait:
            self._wait_for_database(db_url)

        if getattr(self.config, "max_metadata_value_size", None):
            from galaxy.model import custom_types
            custom_types.MAX_METADATA_VALUE_SIZE = self.config.max_metadata_value_size

        if check_migrate_databases:
            # Initialize database / check for appropriate schema version.  # If this
            # is a new installation, we'll restrict the tool migration messaging.
            from galaxy.model.migrate.check import create_or_verify_database
            create_or_verify_database(db_url, config_file, self.config.database_engine_options, app=self, map_install_models=combined_install_database)
            if not combined_install_database:
                tsi_create_or_verify_database(install_db_url, install_database_options, app=self)

        if check_migrate_tools:
            # Alert the Galaxy admin to tools that have been moved from the distribution to the tool shed.
            from tool_shed.galaxy_install.migrate.check import verify_tools
            verify_tools(self, install_db_url, config_file, install_database_options)

        self.model = init_models_from_config(
            self.config,
            map_install_models=combined_install_database,
            object_store=self.object_store,
            trace_logger=getattr(self, "trace_logger", None)
        )
        if combined_install_database:
            log.info("Install database targetting Galaxy's database configuration.")
            self.install_model = self.model
        else:
            from galaxy.model.tool_shed_install import mapping as install_mapping
            install_db_url = self.config.install_database_connection
            log.info("Install database using its own connection %s" % install_db_url)
            self.install_model = install_mapping.init(install_db_url,
                                                      install_database_options)

    def _configure_signal_handlers(self, handlers):
        for sig, handler in handlers.items():
            signal.signal(sig, handler)

    def _wait_for_database(self, url):
        from sqlalchemy_utils import database_exists
        attempts = self.config.database_wait_attempts
        pause = self.config.database_wait_sleep
        for i in range(1, attempts):
            try:
                database_exists(url)
                break
            except Exception:
                log.info("Waiting for database: attempt %d of %d" % (i, attempts))
                time.sleep(pause)

    @property
    def tool_dependency_dir(self):
        return self.toolbox.dependency_manager.default_base_path
