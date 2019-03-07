"""
Universe configuration builder.
"""
import logging
import logging.config
import os
import re
from datetime import timedelta

from six.moves import configparser

from galaxy.util import string_as_bool
from galaxy.version import VERSION, VERSION_MAJOR
from galaxy.web.formatting import expand_pretty_datetime_format

log = logging.getLogger(__name__)


def resolve_path(path, root):
    """If 'path' is relative make absolute by prepending 'root'"""
    if not(os.path.isabs(path)):
        path = os.path.join(root, path)
    return path


class ConfigurationError(Exception):
    pass


class Configuration(object):

    def __init__(self, **kwargs):
        self.config_dict = kwargs
        self.root = kwargs.get('root_dir', '.')

        # Resolve paths of other config files
        self.__parse_config_file_options(kwargs)

        # Collect the umask and primary gid from the environment
        self.umask = os.umask(0o77)  # get the current umask
        os.umask(self.umask)  # can't get w/o set, so set it back
        self.gid = os.getgid()  # if running under newgrp(1) we'll need to fix the group of data created on the cluster
        self.version_major = VERSION_MAJOR
        self.version = VERSION
        # Database related configuration
        self.database = resolve_path(kwargs.get("database_file", "database/community.sqlite"), self.root)
        self.database_connection = kwargs.get("database_connection", False)
        self.database_engine_options = get_database_engine_options(kwargs)
        self.database_create_tables = string_as_bool(kwargs.get("database_create_tables", "True"))
        # Repository and Tool search API
        self.toolshed_search_on = string_as_bool(kwargs.get("toolshed_search_on", True))
        self.whoosh_index_dir = kwargs.get("whoosh_index_dir", 'database/toolshed_whoosh_indexes')
        self.repo_name_boost = kwargs.get("repo_name_boost", 0.9)
        self.repo_description_boost = kwargs.get("repo_description_boost", 0.6)
        self.repo_long_description_boost = kwargs.get("repo_long_description_boost", 0.5)
        self.repo_homepage_url_boost = kwargs.get("repo_homepage_url_boost", 0.3)
        self.repo_remote_repository_url_boost = kwargs.get("repo_remote_repository_url_boost", 0.2)
        self.repo_owner_username_boost = kwargs.get("repo_owner_username_boost", 0.3)
        self.tool_name_boost = kwargs.get("tool_name_boost", 1.2)
        self.tool_description_boost = kwargs.get("tool_description_boost", 0.6)
        self.tool_help_boost = kwargs.get("tool_help_boost", 0.4)
        self.tool_repo_owner_username = kwargs.get("tool_repo_owner_username", 0.3)
        # Analytics
        self.ga_code = kwargs.get("ga_code", None)
        self.session_duration = int(kwargs.get('session_duration', 0))
        # Where dataset files are stored
        self.file_path = resolve_path(kwargs.get("file_path", "database/community_files"), self.root)
        self.new_file_path = resolve_path(kwargs.get("new_file_path", "database/tmp"), self.root)
        self.cookie_path = kwargs.get("cookie_path", "/")
        self.enable_quotas = string_as_bool(kwargs.get('enable_quotas', False))
        self.id_secret = kwargs.get("id_secret", "changethisinproductiontoo")
        # Tool stuff
        self.tool_path = resolve_path(kwargs.get("tool_path", "tools"), self.root)
        self.tool_secret = kwargs.get("tool_secret", "")
        self.tool_data_path = resolve_path(kwargs.get("tool_data_path", "shed-tool-data"), os.getcwd())
        self.tool_data_table_config_path = None
        self.integrated_tool_panel_config = resolve_path(kwargs.get('integrated_tool_panel_config', 'integrated_tool_panel.xml'), self.root)
        self.builds_file_path = resolve_path(kwargs.get("builds_file_path", os.path.join(self.tool_data_path, 'shared', 'ucsc', 'builds.txt')), self.root)
        self.len_file_path = resolve_path(kwargs.get("len_file_path", os.path.join(self.tool_data_path, 'shared', 'ucsc', 'chrom')), self.root)
        self.ftp_upload_dir = kwargs.get('ftp_upload_dir', None)
        self.update_integrated_tool_panel = False
        # Galaxy flavor Docker Image
        self.enable_galaxy_flavor_docker_image = string_as_bool(kwargs.get("enable_galaxy_flavor_docker_image", "False"))
        self.use_remote_user = string_as_bool(kwargs.get("use_remote_user", "False"))
        self.user_activation_on = None
        self.registration_warning_message = kwargs.get('registration_warning_message', None)
        self.terms_url = kwargs.get('terms_url', None)
        self.blacklist_location = kwargs.get('blacklist_file', None)
        self.blacklist_content = None
        self.remote_user_maildomain = kwargs.get("remote_user_maildomain", None)
        self.remote_user_header = kwargs.get("remote_user_header", 'HTTP_REMOTE_USER')
        self.remote_user_logout_href = kwargs.get("remote_user_logout_href", None)
        self.remote_user_secret = kwargs.get("remote_user_secret", None)
        self.require_login = string_as_bool(kwargs.get("require_login", "False"))
        self.allow_user_creation = string_as_bool(kwargs.get("allow_user_creation", "True"))
        self.allow_user_deletion = string_as_bool(kwargs.get("allow_user_deletion", "False"))
        self.template_path = resolve_path(kwargs.get("template_path", "templates"), self.root)
        self.template_cache = resolve_path(kwargs.get("template_cache_path", "database/compiled_templates/community"), self.root)
        self.admin_users = kwargs.get("admin_users", "")
        self.admin_users_list = [u.strip() for u in self.admin_users.split(',') if u]
        self.mailing_join_addr = kwargs.get('mailing_join_addr', "galaxy-announce-join@bx.psu.edu")
        self.error_email_to = kwargs.get('error_email_to', None)
        self.smtp_server = kwargs.get('smtp_server', None)
        self.smtp_username = kwargs.get('smtp_username', None)
        self.smtp_password = kwargs.get('smtp_password', None)
        self.smtp_ssl = kwargs.get('smtp_ssl', None)
        self.email_from = kwargs.get('email_from', None)
        self.nginx_upload_path = kwargs.get('nginx_upload_path', False)
        self.log_actions = string_as_bool(kwargs.get('log_actions', 'False'))
        self.brand = kwargs.get('brand', None)
        self.pretty_datetime_format = expand_pretty_datetime_format(kwargs.get('pretty_datetime_format', '$locale (UTC)'))
        # Configuration for the message box directly below the masthead.
        self.message_box_visible = string_as_bool(kwargs.get('message_box_visible', False))
        self.message_box_content = kwargs.get('message_box_content', None)
        self.message_box_class = kwargs.get('message_box_class', 'info')
        self.support_url = kwargs.get('support_url', 'https://galaxyproject.org/support')
        self.wiki_url = kwargs.get('wiki_url', 'https://galaxyproject.org/')
        self.blog_url = kwargs.get('blog_url', None)
        self.biostar_url = kwargs.get('biostar_url', None)
        self.screencasts_url = kwargs.get('screencasts_url', None)
        self.log_events = False
        self.cloud_controller_instance = False
        self.server_name = ''
        # Error logging with sentry
        self.sentry_dsn = kwargs.get('sentry_dsn', None)
        # Where the tool shed hgweb.config file is stored - the default is the Galaxy installation directory.
        self.hgweb_config_dir = resolve_path(kwargs.get('hgweb_config_dir', ''), self.root)
        # Proxy features
        self.apache_xsendfile = kwargs.get('apache_xsendfile', False)
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
        self.citation_cache_data_dir = resolve_path(kwargs.get("citation_cache_data_dir", "database/tool_shed_citations/data"), self.root)
        self.citation_cache_lock_dir = resolve_path(kwargs.get("citation_cache_lock_dir", "database/tool_shed_citations/locks"), self.root)
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

    @property
    def sentry_dsn_public(self):
        """
        Sentry URL with private key removed for use in client side scripts,
        sentry server will need to be configured to accept events
        """
        # TODO refactor this to a common place between toolshed/galaxy config, along
        # with other duplicated methods.
        if self.sentry_dsn:
            return re.sub(r"^([^:/?#]+:)?//(\w+):(\w+)", r"\1//\2", self.sentry_dsn)
        else:
            return None

    def __parse_config_file_options(self, kwargs):
        path_list_defaults = dict(
            auth_config_file=['config/auth_conf.xml', 'config/auth_conf.xml.sample'],
            datatypes_config_file=['config/datatypes_conf.xml', 'datatypes_conf.xml', 'config/datatypes_conf.xml.sample'],
            shed_tool_data_table_config=['shed_tool_data_table_conf.xml', 'config/shed_tool_data_table_conf.xml'],
        )

        for var, defaults in path_list_defaults.items():
            if kwargs.get(var, None) is not None:
                path = kwargs.get(var)
            else:
                for default in defaults:
                    if os.path.exists(resolve_path(default, self.root)):
                        path = default
                        break
                else:
                    path = defaults[-1]
            setattr(self, var, resolve_path(path, self.root))

        # Backwards compatibility for names used in too many places to fix
        self.datatypes_config = self.datatypes_config_file

    def get(self, key, default):
        return self.config_dict.get(key, default)

    def get_bool(self, key, default):
        if key in self.config_dict:
            return string_as_bool(self.config_dict[key])
        else:
            return default

    def check(self):
        # Check that required directories exist.
        paths_to_check = [self.root, self.file_path, self.hgweb_config_dir, self.tool_data_path, self.template_path]
        for path in paths_to_check:
            if path not in [None, False] and not os.path.isdir(path):
                try:
                    os.makedirs(path)
                except Exception as e:
                    raise ConfigurationError("Unable to create missing directory: %s\n%s" % (path, e))
        # Create the directories that it makes sense to create.
        for path in self.file_path, \
            self.template_cache, \
                os.path.join(self.tool_data_path, 'shared', 'jars'):
            if path not in [None, False] and not os.path.isdir(path):
                try:
                    os.makedirs(path)
                except Exception as e:
                    raise ConfigurationError("Unable to create missing directory: %s\n%s" % (path, e))
        # Check that required files exist.
        if not os.path.isfile(self.datatypes_config):
            raise ConfigurationError("File not found: %s" % self.datatypes_config)

    def is_admin_user(self, user):
        """
        Determine if the provided user is listed in `admin_users`.
        """
        admin_users = self.get("admin_users", "").split(",")
        return user is not None and user.email in admin_users


def get_database_engine_options(kwargs):
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
    prefix = "database_engine_option_"
    prefix_len = len(prefix)
    rval = {}
    for key, value in kwargs.items():
        if key.startswith(prefix):
            key = key[prefix_len:]
            if key in conversions:
                value = conversions[key](value)
            rval[key] = value
    return rval
