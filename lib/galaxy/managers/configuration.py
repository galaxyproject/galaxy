"""
Serializers for Galaxy config file data: ConfigSerializer for all users
and a more expanded set of data for admin in AdminConfigSerializer.

Used by both the API and bootstrapped data.
"""
# TODO: this is a bit of an odd duck. It uses the serializer structure from managers
#   but doesn't have a model like them. It might be better in config.py or a
#   totally new area, but I'm leaving it in managers for now for class consistency.
import logging
import sys

from galaxy.managers import base
from galaxy.web.framework.base import server_starttime

log = logging.getLogger(__name__)


class ConfigSerializer(base.ModelSerializer):
    """Configuration (galaxy.ini) settings viewable by all users"""

    def __init__(self, app):
        super(ConfigSerializer, self).__init__(app)

        self.default_view = 'all'
        self.add_view('all', list(self.serializers.keys()))

    def default_serializer(self, config, key):
        return getattr(config, key, None)

    def add_serializers(self):

        def _defaults_to(default):
            return lambda item, key, **context: getattr(item, key, default)

        def _required_attribute(item, key, **context):
            assert hasattr(item, key)
            return getattr(item, key)

        self.serializers = {
            # TODO: this is available from user data, remove
            'is_admin_user'                     : lambda *a, **c: False,
            'brand'                             : _required_attribute,
            'display_galaxy_brand'              : _required_attribute,
            # TODO: this doesn't seem right
            'logo_url'                          : lambda item, key, **context: self.url_for(item.get(key, '/')),
            'logo_src'                          : lambda item, key, **context: self.url_for('/static/favicon.png'),
            'terms_url'                         : _required_attribute,
            'myexperiment_target_url'           : _required_attribute,
            'wiki_url'                          : _required_attribute,
            'search_url'                        : _required_attribute,
            'mailing_lists'                     : _defaults_to(self.app.config.mailing_lists_url),
            'screencasts_url'                   : _required_attribute,
            'genomespace_ui_url'                : _required_attribute,
            'citation_url'                      : _required_attribute,
            'support_url'                       : _required_attribute,
            'helpsite_url'                      : _required_attribute,
            'lims_doc_url'                      : _defaults_to("https://usegalaxy.org/u/rkchak/p/sts"),
            'default_locale'                    : _required_attribute,
            'enable_openid'                     : _required_attribute,
            'enable_communication_server'       : _required_attribute,
            'communication_server_port'         : _required_attribute,
            'communication_server_host'         : _required_attribute,
            'persistent_communication_rooms'    : _required_attribute,
            'allow_user_impersonation'          : _required_attribute,
            'allow_user_creation'               : _defaults_to(False),  # schema default is True
            'use_remote_user'                   : _defaults_to(None),  # schema default is False; or config.single_user
            'enable_oidc'                       : _required_attribute,
            'oidc'                              : _required_attribute,
            'enable_quotas'                     : _required_attribute,
            'remote_user_logout_href'           : _required_attribute,
            'datatypes_disable_auto'            : _required_attribute,
            'allow_user_dataset_purge'          : _defaults_to(False),  # schema default is True
            'ga_code'                           : _required_attribute,
            'enable_unique_workflow_defaults'   : _required_attribute,
            'enable_beta_markdown_export'       : _required_attribute,
            'has_user_tool_filters'             : _defaults_to(False),
            # TODO: is there no 'correct' way to get an api url? controller='api', action='tools' is a hack
            # at any rate: the following works with path_prefix but is still brittle
            # TODO: change this to (more generic) upload_path and incorporate config.nginx_upload_path into building it
            'nginx_upload_path'                 : lambda item, key, **context: getattr(item, key, False),
            'chunk_upload_size'                 : _required_attribute,
            'ftp_upload_site'                   : _required_attribute,
            'version_major'                     : _defaults_to(None),
            'require_login'                     : _required_attribute,
            'inactivity_box_content'            : _required_attribute,
            'visualizations_visible'            : _required_attribute,
            'interactivetools_enable'           : _required_attribute,
            'message_box_content'               : _required_attribute,
            'message_box_visible'               : _required_attribute,
            'message_box_class'                 : _required_attribute,
            'server_startttime'                 : lambda item, key, **context: server_starttime,
            'mailing_join_addr'                 : _defaults_to('galaxy-announce-join@bx.psu.edu'),  # should this be the schema default?
            'server_mail_configured'            : lambda item, key, **context: bool(getattr(item, 'smtp_server')),
            'registration_warning_message'      : _required_attribute,
            'welcome_url'                       : _required_attribute,
            'show_welcome_with_login'           : _defaults_to(True),  # schema default is False
            'cookie_domain'                     : _required_attribute,
            'python'                            : _defaults_to((sys.version_info.major, sys.version_info.minor)),
            'select_type_workflow_threshold'    : _required_attribute,
        }


class AdminConfigSerializer(ConfigSerializer):
    """Configuration attributes viewable only by admin users"""

    def add_serializers(self):
        super(AdminConfigSerializer, self).add_serializers()

        def _defaults_to(default):
            return lambda item, key, **context: getattr(item, key, default)

        self.serializers.update({
            # TODO: this is available from user serialization: remove
            'is_admin_user'                     : lambda *a: True,

            'library_import_dir'                : _defaults_to(None),
            'user_library_import_dir'           : _defaults_to(None),
            'allow_library_path_paste'          : _defaults_to(False),
            'allow_user_deletion'               : _defaults_to(False),
        })
