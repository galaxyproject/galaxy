"""
Universe configuration builder.
"""
import logging
import logging.config
import os
from datetime import timedelta

from six.moves import configparser

from galaxy.config import (
    BaseAppConfiguration,
    CommonConfigurationMixin,
    get_database_engine_options,
)
from galaxy.config.schema import AppSchema
from galaxy.util import string_as_bool
from galaxy.version import VERSION, VERSION_MAJOR
from galaxy.web.formatting import expand_pretty_datetime_format

log = logging.getLogger(__name__)

ts_webapp_path = os.path.abspath(os.path.dirname(__file__))
templates_path = os.path.join(ts_webapp_path, "templates")

TOOLSHED_APP_NAME = 'tool_shed'
TOOLSHED_CONFIG_SCHEMA_PATH = 'lib/tool_shed/webapp/config_schema.yml'


class ConfigurationError(Exception):
    pass


class ToolShedAppConfiguration(BaseAppConfiguration, CommonConfigurationMixin):
    default_config_file_name = 'tool_shed.yml'

    def _load_schema(self):
        return AppSchema(TOOLSHED_CONFIG_SCHEMA_PATH, TOOLSHED_APP_NAME)

    def __init__(self, **kwargs):
        super(ToolShedAppConfiguration, self).__init__(**kwargs)

        # Resolve paths of other config files
        self.parse_config_file_options(kwargs)

        # Collect the umask and primary gid from the environment
        self.umask = os.umask(0o77)  # get the current umask
        os.umask(self.umask)  # can't get w/o set, so set it back
        self.gid = os.getgid()  # if running under newgrp(1) we'll need to fix the group of data created on the cluster
        self.version_major = VERSION_MAJOR
        self.version = VERSION
        # Database related configuration
        if not self.database_connection:  # Provide default if not supplied by user
            self.database_connection = 'sqlite:///%s?isolation_level=IMMEDIATE' % self._in_data_dir('community.sqlite')
        self.database_engine_options = get_database_engine_options(kwargs)
        self.database_create_tables = string_as_bool(kwargs.get("database_create_tables", "True"))
        # Where dataset files are stored
        self.file_path = self._in_root_dir(self.file_path)
        self.new_file_path = self._in_root_dir(self.new_file_path)
        self.cookie_path = kwargs.get("cookie_path", None)
        self.cookie_domain = kwargs.get("cookie_domain", None)
        self.enable_quotas = string_as_bool(kwargs.get('enable_quotas', False))
        # Tool stuff
        self.tool_path = self._in_root_dir(kwargs.get("tool_path", "tools"))
        self.tool_secret = kwargs.get("tool_secret", "")
        self.tool_data_path = os.path.join(os.getcwd(), kwargs.get("tool_data_path", "shed-tool-data"))
        self.tool_data_table_config_path = None
        self.integrated_tool_panel_config = self._in_root_dir(kwargs.get('integrated_tool_panel_config', 'integrated_tool_panel.xml'))
        self.builds_file_path = self._in_root_dir(kwargs.get("builds_file_path", os.path.join(self.tool_data_path, 'shared', 'ucsc', 'builds.txt')))
        self.len_file_path = self._in_root_dir(kwargs.get("len_file_path", os.path.join(self.tool_data_path, 'shared', 'ucsc', 'chrom')))
        self.ftp_upload_dir = kwargs.get('ftp_upload_dir', None)
        self.update_integrated_tool_panel = False
        # Galaxy flavor Docker Image
        self.user_activation_on = None
        self.registration_warning_message = kwargs.get('registration_warning_message', None)
        self.blacklist_location = kwargs.get('blacklist_file', None)
        self.blacklist_content = None
        self.whitelist_location = kwargs.get('whitelist_file', None)
        self.whitelist_content = None
        self.remote_user_maildomain = kwargs.get("remote_user_maildomain", None)
        self.remote_user_header = kwargs.get("remote_user_header", 'HTTP_REMOTE_USER')
        self.remote_user_logout_href = kwargs.get("remote_user_logout_href", None)
        self.remote_user_secret = kwargs.get("remote_user_secret", None)
        self.template_path = templates_path
        self.template_cache_path = self._in_root_dir(kwargs.get("template_cache_path", "database/compiled_templates/community"))
        self.error_email_to = kwargs.get('error_email_to', None)
        self.smtp_server = kwargs.get('smtp_server', None)
        self.smtp_ssl = kwargs.get('smtp_ssl', None)
        self.email_from = kwargs.get('email_from', None)
        self.nginx_upload_path = kwargs.get('nginx_upload_path', False)
        self.log_actions = string_as_bool(kwargs.get('log_actions', 'False'))
        self.pretty_datetime_format = expand_pretty_datetime_format(self.pretty_datetime_format)
        # Configuration for the message box directly below the masthead.
        self.wiki_url = kwargs.get('wiki_url', 'https://galaxyproject.org/')
        self.blog_url = kwargs.get('blog_url', None)
        self.screencasts_url = kwargs.get('screencasts_url', None)
        self.log_events = False
        self.cloud_controller_instance = False
        self.server_name = ''
        # Where the tool shed hgweb.config file is stored - the default is the Galaxy installation directory.
        self.hgweb_config_dir = self._in_root_dir(self.hgweb_config_dir) or self.root
        # Proxy features
        self.nginx_x_accel_redirect_base = kwargs.get('nginx_x_accel_redirect_base', False)
        self.drmaa_external_runjob_script = kwargs.get('drmaa_external_runjob_script', None)
        # Parse global_conf and save the parser
        global_conf = kwargs.get('global_conf', None)
        global_conf_parser = configparser.ConfigParser()
        self.global_conf_parser = global_conf_parser
        if global_conf and "__file__" in global_conf and ".yml" not in global_conf["__file__"]:
            global_conf_parser.read(global_conf['__file__'])
        self.running_functional_tests = string_as_bool(kwargs.get('running_functional_tests', False))
        self.citation_cache_type = kwargs.get("citation_cache_type", "file")
        self.citation_cache_data_dir = self._in_root_dir(kwargs.get("citation_cache_data_dir", "database/tool_shed_citations/data"))
        self.citation_cache_lock_dir = self._in_root_dir(kwargs.get("citation_cache_lock_dir", "database/tool_shed_citations/locks"))
        self.password_expiration_period = timedelta(days=int(kwargs.get("password_expiration_period", 0)))

        # Security/Policy Compliance
        self.redact_username_during_deletion = False
        self.redact_email_during_deletion = False
        self.redact_username_in_logs = False
        self.enable_beta_gdpr = string_as_bool(kwargs.get("enable_beta_gdpr", False))
        if self.enable_beta_gdpr:
            self.redact_username_during_deletion = True
            self.redact_email_during_deletion = True
            self.redact_username_in_logs = True
            self.allow_user_deletion = True

    @property
    def shed_tool_data_path(self):
        return self.tool_data_path

    def parse_config_file_options(self, kwargs):
        defaults = dict(
            auth_config_file=[self._in_config_dir('config/auth_conf.xml')],
            datatypes_config_file=[self._in_config_dir('datatypes_conf.xml'), self._in_sample_dir('datatypes_conf.xml.sample')],
            shed_tool_data_table_config=[self._in_managed_config_dir('shed_tool_data_table_conf.xml')],
        )

        self._parse_config_file_options(defaults, dict(), kwargs)

        # Backwards compatibility for names used in too many places to fix
        self.datatypes_config = self.datatypes_config_file

    def check(self):
        # Check that required directories exist.
        paths_to_check = [self.file_path, self.hgweb_config_dir, self.tool_data_path, self.template_path]
        for path in paths_to_check:
            if path not in [None, False] and not os.path.isdir(path):
                try:
                    os.makedirs(path)
                except Exception as e:
                    raise ConfigurationError("Unable to create missing directory: %s\n%s" % (path, e))
        # Create the directories that it makes sense to create.
        for path in self.file_path, \
            self.template_cache_path, \
                os.path.join(self.tool_data_path, 'shared', 'jars'):
            if path not in [None, False] and not os.path.isdir(path):
                try:
                    os.makedirs(path)
                except Exception as e:
                    raise ConfigurationError("Unable to create missing directory: %s\n%s" % (path, e))
        # Check that required files exist.
        if not os.path.isfile(self.datatypes_config):
            raise ConfigurationError("File not found: %s" % self.datatypes_config)


Configuration = ToolShedAppConfiguration
