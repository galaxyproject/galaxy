"""Universe configuration builder."""
import logging
import os
import re

from galaxy.util import string_as_bool

log = logging.getLogger(__name__)


def resolve_path(path, root):
    """If 'path' is relative make absolute by prepending 'root'"""
    if not (os.path.isabs(path)):
        path = os.path.join(root, path)
    return path


class ConfigurationError(Exception):
    pass


class Configuration:
    def __init__(self, **kwargs):
        self.config_dict = kwargs
        self.root = kwargs.get("root_dir", ".")
        # Database related configuration
        self.database = resolve_path(kwargs.get("database_file", "database/universe.sqlite"), self.root)
        self.database_connection = kwargs.get("database_connection", False)
        self.database_engine_options = get_database_engine_options(kwargs)
        # Where dataset files are stored
        self.file_path = resolve_path(kwargs.get("file_path", "database/objects"), self.root)
        self.new_file_path = resolve_path(kwargs.get("new_file_path", "database/tmp"), self.root)
        self.id_secret = kwargs.get("id_secret", "USING THE DEFAULT IS NOT SECURE!")
        self.use_remote_user = string_as_bool(kwargs.get("use_remote_user", "False"))
        self.require_login = string_as_bool(kwargs.get("require_login", "False"))
        self.template_cache_path = resolve_path(
            kwargs.get("template_cache_path", "database/compiled_templates/reports"), self.root
        )
        self.allow_user_creation = string_as_bool(kwargs.get("allow_user_creation", "True"))
        self.allow_user_deletion = string_as_bool(kwargs.get("allow_user_deletion", "False"))
        self.log_actions = string_as_bool(kwargs.get("log_actions", "False"))
        self.brand = kwargs.get("brand", None)
        # Configuration for the message box directly below the masthead.
        self.message_box_visible = string_as_bool(kwargs.get("message_box_visible", False))
        self.message_box_content = kwargs.get("message_box_content", None)
        self.message_box_class = kwargs.get("message_box_class", "info")
        self.wiki_url = kwargs.get("wiki_url", "https://galaxyproject.org/")
        self.blog_url = kwargs.get("blog_url", None)
        self.screencasts_url = kwargs.get("screencasts_url", None)
        self.log_events = False
        self.cookie_path = kwargs.get("cookie_path", None)
        self.cookie_domain = kwargs.get("cookie_domain", None)
        # Error logging with sentry
        self.sentry_dsn = kwargs.get("sentry_dsn", None)

        # Security/Policy Compliance
        self.redact_username_in_logs = False
        self.redact_email_in_job_name = False
        self.enable_beta_gdpr = string_as_bool(kwargs.get("enable_beta_gdpr", False))
        if self.enable_beta_gdpr:
            self.redact_username_in_logs = True
            self.redact_email_in_job_name = True
            self.allow_user_deletion = True

    def get(self, key, default=None):
        return self.config_dict.get(key, default)

    def check(self):
        # Check that required directories exist
        for path in (self.root,):
            if not os.path.isdir(path):
                raise ConfigurationError(f"Directory does not exist: {path}")

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


def get_database_engine_options(kwargs):
    """
    Allow options for the SQLAlchemy database engine to be passed by using
    the prefix "database_engine_option".
    """
    conversions = {
        "convert_unicode": string_as_bool,
        "pool_timeout": int,
        "echo": string_as_bool,
        "echo_pool": string_as_bool,
        "pool_recycle": int,
        "pool_size": int,
        "max_overflow": int,
        "pool_threadlocal": string_as_bool,
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
