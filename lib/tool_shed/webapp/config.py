"""
Universe configuration builder.
"""

import configparser
import logging
import logging.config
import os
from datetime import timedelta

from galaxy.config import (
    BaseAppConfiguration,
    CommonConfigurationMixin,
    expand_pretty_datetime_format,
    get_database_engine_options,
    TOOL_SHED_CONFIG_SCHEMA_PATH,
)
from galaxy.config.schema import AppSchema
from galaxy.exceptions import ConfigurationError
from galaxy.util import string_as_bool
from galaxy.version import (
    VERSION,
    VERSION_MAJOR,
    VERSION_MINOR,
)

log = logging.getLogger(__name__)

TOOLSHED_APP_NAME = "tool_shed"
SHED_API_VERSION = os.environ.get("TOOL_SHED_API_VERSION", "v1")


class ToolShedAppConfiguration(BaseAppConfiguration, CommonConfigurationMixin):
    default_config_file_name = "tool_shed.yml"

    add_sample_file_to_defaults = {"datatypes_config_file"}

    def _load_schema(self):
        return AppSchema(TOOL_SHED_CONFIG_SCHEMA_PATH, TOOLSHED_APP_NAME)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._process_config(kwargs)

    @property
    def shed_tool_data_path(self):
        return self.tool_data_path

    def check(self):
        # Check that required directories exist; attempt to create otherwise
        paths_to_check = [
            self.file_path,
            self.hgweb_config_dir,
            self.tool_data_path,
            self.template_cache_path,
            os.path.join(self.tool_data_path, "shared", "jars"),
        ]
        for path in paths_to_check:
            self._ensure_directory(path)
        # Check that required files exist.
        if not os.path.isfile(self.datatypes_config):
            raise ConfigurationError(f"File not found: {self.datatypes_config}")

    def _process_config(self, kwargs):
        # Backwards compatibility for names used in too many places to fix
        self.datatypes_config = self.datatypes_config_file
        # Collect the umask and primary gid from the environment
        self.umask = os.umask(0o77)  # get the current umask
        os.umask(self.umask)  # can't get w/o set, so set it back
        self.gid = os.getgid()  # if running under newgrp(1) we'll need to fix the group of data created on the cluster
        self.version_major = VERSION_MAJOR
        self.version_minor = VERSION_MINOR
        self.version = VERSION
        # Database related configuration
        if not self.database_connection:  # Provide default if not supplied by user
            self.database_connection = f"sqlite:///{self._in_data_dir('community.sqlite')}?isolation_level=IMMEDIATE"
        self.database_engine_options = get_database_engine_options(kwargs)
        self.database_create_tables = string_as_bool(kwargs.get("database_create_tables", "True"))
        # Where dataset files are stored
        self.file_path = self._in_root_dir(self.file_path)
        self.new_file_path = self._in_root_dir(self.new_file_path)
        self.cookie_path = kwargs.get("cookie_path")
        self.cookie_domain = kwargs.get("cookie_domain")
        self.enable_quotas = string_as_bool(kwargs.get("enable_quotas", False))
        # Tool stuff
        self.tool_path = self._in_root_dir(kwargs.get("tool_path", "tools"))
        self.tool_secret = kwargs.get("tool_secret", "")
        self.tool_data_path = os.path.join(os.getcwd(), kwargs.get("tool_data_path", "shed-tool-data"))
        self.tool_data_table_config_path = None
        self.integrated_tool_panel_config = self._in_root_dir(
            kwargs.get("integrated_tool_panel_config", "integrated_tool_panel.xml")
        )
        self.builds_file_path = self._in_root_dir(
            kwargs.get("builds_file_path", os.path.join(self.tool_data_path, "shared", "ucsc", "builds.txt"))
        )
        self.len_file_path = self._in_root_dir(
            kwargs.get("len_file_path", os.path.join(self.tool_data_path, "shared", "ucsc", "chrom"))
        )
        self.ftp_upload_dir = kwargs.get("ftp_upload_dir")
        self.update_integrated_tool_panel = False
        # Galaxy flavor Docker Image
        self.user_activation_on = None
        self.registration_warning_message = kwargs.get("registration_warning_message")
        self.email_domain_blocklist_content = None
        self.email_domain_allowlist_content = None
        self.template_cache_path = self._in_root_dir(
            kwargs.get("template_cache_path", "database/compiled_templates/community")
        )
        self.error_email_to = kwargs.get("error_email_to")
        self.pretty_datetime_format = expand_pretty_datetime_format(self.pretty_datetime_format)
        # Configuration for the message box directly below the masthead.
        self.wiki_url = kwargs.get("wiki_url", "https://galaxyproject.org/")
        self.blog_url = kwargs.get("blog_url")
        self.screencasts_url = kwargs.get("screencasts_url")
        self.log_events = False
        self.cloud_controller_instance = False
        self.server_name = ""
        # Where the tool shed hgweb.config file is stored - the default is the Galaxy installation directory.
        self.hgweb_config_dir = self._in_root_dir(self.hgweb_config_dir) or self.root
        # Proxy features
        self.drmaa_external_runjob_script = kwargs.get("drmaa_external_runjob_script")
        # Parse global_conf and save the parser
        global_conf = kwargs.get("global_conf")
        global_conf_parser = configparser.ConfigParser()
        self.global_conf_parser = global_conf_parser
        if global_conf and "__file__" in global_conf and ".yml" not in global_conf["__file__"]:
            global_conf_parser.read(global_conf["__file__"])
        self.running_functional_tests = string_as_bool(kwargs.get("running_functional_tests", False))
        self.citation_cache_data_dir = self._in_root_dir(
            kwargs.get("citation_cache_data_dir", "database/tool_shed_citations/data")
        )
        self.citation_cache_lock_dir = self._in_root_dir(
            kwargs.get("citation_cache_lock_dir", "database/tool_shed_citations/locks")
        )
        self.citation_cache_url = kwargs.get("citation_cache_lock_dir", None)
        self.citation_cache_schema_name = kwargs.get("citation_cache_schema_name", None)
        self.citation_cache_table_name = kwargs.get("citation_cache_table_name", None)
        self.password_expiration_period = timedelta(days=int(self.password_expiration_period))

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


Configuration = ToolShedAppConfiguration
