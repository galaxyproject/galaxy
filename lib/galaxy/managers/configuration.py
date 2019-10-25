"""
Serializers for Galaxy config file data: ConfigSerializer for all users
and a more expanded set of data for admin in AdminConfigSerializer.

Used by both the API and bootstrapped data.
"""
# TODO: this is a bit of an odd duck. It uses the serializer structure from managers
#   but doesn't have a model like them. It might be better in config.py or a
#   totally new area, but I'm leaving it in managers for now for class consistency.
import logging

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

        self.serializers = {
            # TODO: this is available from user data, remove
            'is_admin_user'                     : lambda *a, **c: False,

            'brand'                             : _defaults_to(self.app.config.brand or ''),
            # TODO: this doesn't seem right
            'logo_url'                          : lambda item, key, **context: self.url_for(item.get(key, '/')),
            'logo_src'                          : lambda item, key, **context: self.url_for('/static/images/galaxyIcon_noText.png'),
            'terms_url'                         : _defaults_to(self.app.config.terms_url or ''),
            'myexperiment_target_url'           : _defaults_to(self.app.config.myexperiment_target_url),
            'wiki_url'                          : _defaults_to(self.app.config.wiki_url),
            'search_url'                        : _defaults_to(self.app.config.search_url),
            'mailing_lists'                     : _defaults_to(self.app.config.mailing_lists_url),
            'screencasts_url'                   : _defaults_to(self.app.config.screencasts_url),
            'genomespace_ui_url'                : _defaults_to(self.app.config.genomespace_ui_url),
            'citation_url'                      : _defaults_to(self.app.config.citation_url),
            'support_url'                       : _defaults_to(self.app.config.support_url),
            'helpsite_url'                      : _defaults_to(self.app.config.helpsite_url),
            'lims_doc_url'                      : _defaults_to("https://usegalaxy.org/u/rkchak/p/sts"),
            'default_locale'                    : _defaults_to(self.app.config.default_locale),
            'enable_openid'                     : _defaults_to(self.app.config.enable_openid),
            'enable_communication_server'       : _defaults_to(self.app.config.enable_communication_server),
            'communication_server_port'         : _defaults_to(self.app.config.communication_server_port),
            'communication_server_host'         : _defaults_to(self.app.config.communication_server_host),
            'persistent_communication_rooms'    : _defaults_to(self.app.config.persistent_communication_rooms),
            'allow_user_impersonation'          : _defaults_to(self.app.config.allow_user_impersonation),
            'allow_user_creation'               : _defaults_to(False),  # schema default is True
            'use_remote_user'                   : _defaults_to(None),  # schema default is False; or config.single_user
            'enable_oidc'                       : _defaults_to(self.app.config.enable_oidc),
            'oidc'                              : _defaults_to(self.app.config.oidc),
            'enable_quotas'                     : _defaults_to(self.app.config.enable_quotas),
            'remote_user_logout_href'           : _defaults_to(self.app.config.remote_user_logout_href or ''),
            'datatypes_disable_auto'            : _defaults_to(self.app.config.datatypes_disable_auto),
            'allow_user_dataset_purge'          : _defaults_to(False),  # schema default is True
            'ga_code'                           : _defaults_to(self.app.config.ga_code),
            'enable_unique_workflow_defaults'   : _defaults_to(self.app.config.enable_unique_workflow_defaults),
            'has_user_tool_filters'             : _defaults_to(False),

            # TODO: is there no 'correct' way to get an api url? controller='api', action='tools' is a hack
            # at any rate: the following works with path_prefix but is still brittle
            # TODO: change this to (more generic) upload_path and incorporate config.nginx_upload_path into building it
            'nginx_upload_path'                 : lambda item, key, **context: getattr(item, key, False),
            'chunk_upload_size'                 : _defaults_to(self.app.config.chunk_upload_size),
            'ftp_upload_site'                   : _defaults_to(self.app.config.ftp_upload_site),
            'version_major'                     : _defaults_to(None),
            'require_login'                     : _defaults_to(self.app.config.require_login),
            'inactivity_box_content'            : _defaults_to(self.app.config.inactivity_box_content),
            'visualizations_visible'            : _defaults_to(self.app.config.visualizations_visible),
            'interactivetools_enable'           : _defaults_to(self.app.config.interactivetools_enable),
            'message_box_content'               : _defaults_to(self.app.config.message_box_content),
            'message_box_visible'               : _defaults_to(self.app.config.message_box_visible),
            'message_box_class'                 : _defaults_to(self.app.config.message_box_class),
            'server_startttime'                 : lambda item, key, **context: server_starttime,
            'mailing_join_addr'                 : _defaults_to('galaxy-announce-join@bx.psu.edu'),  # should this be the schema default?
            'server_mail_configured'            : lambda item, key, **context: bool(getattr(item, 'smtp_server')),
            'registration_warning_message'      : _defaults_to(self.app.config.registration_warning_message),
            'welcome_url'                       : _defaults_to(self.app.config.welcome_url),
            'show_welcome_with_login'           : _defaults_to(True),  # schema default is False
            'cookie_domain'                     : _defaults_to(self.app.config.cookie_domain),
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
