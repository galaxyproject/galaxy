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
            return lambda i, k, **c: getattr(i, k, default)

        self.serializers = {
            # TODO: this is available from user data, remove
            'is_admin_user'                     : lambda *a, **c: False,

            'brand'                             : _defaults_to(''),
            # TODO: this doesn't seem right
            'logo_url'                          : lambda i, k, **c: self.url_for(i.get(k, '/')),
            'logo_src'                          : lambda i, k, **c: self.url_for('/static/images/galaxyIcon_noText.png'),
            'terms_url'                         : _defaults_to(''),
            'myexperiment_target_url'           : _defaults_to("www.myexperiment.org"),
            'wiki_url'                          : _defaults_to(self.app.config.wiki_url),
            'search_url'                        : _defaults_to(self.app.config.wiki_url.rstrip("/") + "/search/"),
            'mailing_lists'                     : _defaults_to(self.app.config.wiki_url.rstrip("/") + "/mailing-lists/"),
            'screencasts_url'                   : _defaults_to("https://vimeo.com/galaxyproject"),
            'genomespace_ui_url'                : _defaults_to(None),
            'citation_url'                      : _defaults_to(self.app.config.citation_url),
            'support_url'                       : _defaults_to(self.app.config.support_url),
            'helpsite_url'                      : _defaults_to(self.app.config.helpsite_url),
            'lims_doc_url'                      : _defaults_to("https://usegalaxy.org/u/rkchak/p/sts"),
            'biostar_url'                       : _defaults_to(''),
            'biostar_url_redirect'              : lambda *a, **c: self.url_for(controller='biostar', action='biostar_redirect', qualified=True),
            'default_locale'                    : _defaults_to(self.app.config.default_locale),

            'enable_beta_ts_api_install'        : _defaults_to(False),
            'enable_communication_server'       : _defaults_to(False),
            'communication_server_port'         : _defaults_to(None),
            'communication_server_host'         : _defaults_to(None),
            'persistent_communication_rooms'    : _defaults_to(None),
            'allow_user_impersonation'          : _defaults_to(False),
            'allow_user_creation'               : _defaults_to(False),
            'use_remote_user'                   : _defaults_to(None),
            'enable_oidc'                       : _defaults_to(False),
            'enable_quotas'                     : _defaults_to(False),
            'remote_user_logout_href'           : _defaults_to(''),
            'datatypes_disable_auto'            : _defaults_to(False),
            'allow_user_dataset_purge'          : _defaults_to(False),
            'ga_code'                           : _defaults_to(None),
            'enable_unique_workflow_defaults'   : _defaults_to(False),
            'has_user_tool_filters'             : _defaults_to(False),

            # TODO: is there no 'correct' way to get an api url? controller='api', action='tools' is a hack
            # at any rate: the following works with path_prefix but is still brittle
            # TODO: change this to (more generic) upload_path and incorporate config.nginx_upload_path into building it
            'nginx_upload_path'                 : lambda i, k, **c: getattr(i, k, False),
            'chunk_upload_size'                 : _defaults_to(104857600),
            'ftp_upload_dir'                    : _defaults_to(None),
            'ftp_upload_site'                   : _defaults_to(None),
            'version_major'                     : _defaults_to(None),
            'require_login'                     : _defaults_to(None),
            'inactivity_box_content'            : _defaults_to(None),
            'message_box_content'               : _defaults_to(None),
            'message_box_visible'               : _defaults_to(False),
            'message_box_class'                 : _defaults_to('info'),
            'server_startttime'                 : lambda i, k, **c: server_starttime,
            'mailing_join_addr'                 : _defaults_to('galaxy-announce-join@bx.psu.edu'),
            'smtp_server'                       : _defaults_to(None),
            'registration_warning_message'      : _defaults_to(None),
            'welcome_url'                       : _defaults_to(None),
            'show_welcome_with_login'           : _defaults_to(True),
        }


class AdminConfigSerializer(ConfigSerializer):
    """Configuration attributes viewable only by admin users"""

    def add_serializers(self):
        super(AdminConfigSerializer, self).add_serializers()

        def _defaults_to(default):
            return lambda i, k, **c: getattr(i, k, default)

        self.serializers.update({
            # TODO: this is available from user serialization: remove
            'is_admin_user'                     : lambda *a: True,

            'library_import_dir'                : _defaults_to(None),
            'user_library_import_dir'           : _defaults_to(None),
            'allow_library_path_paste'          : _defaults_to(False),
            'allow_user_deletion'               : _defaults_to(False),
        })
