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
        super().__init__(app)

        self.default_view = 'all'
        self.add_view('all', list(self.serializers.keys()))

    def default_serializer(self, config, key):
        return getattr(config, key, None)

    def add_serializers(self):

        def _defaults_to(default):
            return lambda config, key, **context: getattr(config, key, default)

        def _use_config(config, key, **context):
            """Let config object determine the value for key"""
            assert hasattr(config, key)
            return getattr(config, key)

        self.serializers = {
            # TODO: this is available from user data, remove
            'is_admin_user'                     : lambda *a, **c: False,
            'brand'                             : _use_config,
            'display_galaxy_brand'              : _use_config,
            # TODO: this doesn't seem right
            'logo_url'                          : lambda config, key, **context: self.url_for(config.get(key, '/')),
            'logo_src'                          : lambda config, key, **context: self.url_for('/static/favicon.png'),
            'terms_url'                         : _use_config,
            'myexperiment_target_url'           : _use_config,
            'wiki_url'                          : _use_config,
            'search_url'                        : _use_config,
            'mailing_lists'                     : _defaults_to(self.app.config.mailing_lists_url),
            'screencasts_url'                   : _use_config,
            'citation_url'                      : _use_config,
            'support_url'                       : _use_config,
            'helpsite_url'                      : _use_config,
            'lims_doc_url'                      : _defaults_to("https://usegalaxy.org/u/rkchak/p/sts"),
            'default_locale'                    : _use_config,
            'enable_openid'                     : _use_config,
            'enable_communication_server'       : _use_config,
            'communication_server_port'         : _use_config,
            'communication_server_host'         : _use_config,
            'persistent_communication_rooms'    : _use_config,
            'enable_tool_recommendations'       : _use_config,
            'tool_recommendation_model_path'    : _use_config,
            'admin_tool_recommendations_path'   : _use_config,
            'overwrite_model_recommendations'   : _use_config,
            'topk_recommendations'              : _use_config,
            'allow_user_impersonation'          : _use_config,
            'allow_user_creation'               : _defaults_to(False),  # schema default is True
            'use_remote_user'                   : _defaults_to(None),  # schema default is False; or config.single_user
            'enable_oidc'                       : _use_config,
            'oidc'                              : _use_config,
            'enable_quotas'                     : _use_config,
            'remote_user_logout_href'           : _use_config,
            'datatypes_disable_auto'            : _use_config,
            'allow_user_dataset_purge'          : _defaults_to(False),  # schema default is True
            'ga_code'                           : _use_config,
            'enable_unique_workflow_defaults'   : _use_config,
            'enable_beta_markdown_export'       : _use_config,
            'simplified_workflow_run_ui'        : _use_config,
            'simplified_workflow_run_ui_target_history': _use_config,
            'simplified_workflow_run_ui_job_cache': _use_config,
            'has_user_tool_filters'             : _defaults_to(False),
            # TODO: is there no 'correct' way to get an api url? controller='api', action='tools' is a hack
            # at any rate: the following works with path_prefix but is still brittle
            # TODO: change this to (more generic) upload_path and incorporate config.nginx_upload_path into building it
            'nginx_upload_path'                 : lambda config, key, **context: getattr(config, key, False),
            'chunk_upload_size'                 : _use_config,
            'ftp_upload_site'                   : _use_config,
            'version_major'                     : _defaults_to(None),
            'require_login'                     : _use_config,
            'inactivity_box_content'            : _use_config,
            'visualizations_visible'            : _use_config,
            'interactivetools_enable'           : _use_config,
            'aws_estimate'                      : _use_config,
            'message_box_content'               : _use_config,
            'message_box_visible'               : _use_config,
            'message_box_class'                 : _use_config,
            'server_startttime'                 : lambda config, key, **context: server_starttime,
            'mailing_join_addr'                 : _defaults_to('galaxy-announce-join@bx.psu.edu'),  # should this be the schema default?
            'server_mail_configured'            : lambda config, key, **context: bool(getattr(config, 'smtp_server')),
            'registration_warning_message'      : _use_config,
            'welcome_url'                       : _use_config,
            'show_welcome_with_login'           : _defaults_to(True),  # schema default is False
            'cookie_domain'                     : _use_config,
            'python'                            : _defaults_to((sys.version_info.major, sys.version_info.minor)),
            'select_type_workflow_threshold'    : _use_config,
            'file_sources_configured'           : lambda config, key, **context: self.app.file_sources.custom_sources_configured,
            'upload_from_form_button'           : _use_config,
            'user_library_import_dir_available' : lambda config, key, **context: bool(config.get('user_library_import_dir')),
        }


class AdminConfigSerializer(ConfigSerializer):
    """Configuration attributes viewable only by admin users"""

    def add_serializers(self):
        super().add_serializers()

        def _defaults_to(default):
            return lambda config, key, **context: getattr(config, key, default)

        self.serializers.update({
            # TODO: this is available from user serialization: remove
            'is_admin_user'                     : lambda *a: True,

            'library_import_dir'                : _defaults_to(None),
            'user_library_import_dir'           : _defaults_to(None),
            'allow_library_path_paste'          : _defaults_to(False),
            'allow_user_deletion'               : _defaults_to(False),
        })
