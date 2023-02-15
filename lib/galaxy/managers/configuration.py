"""
Managers, serializers for Galaxy config file data. ConfigSerializer for all users
and a more expanded set of data for admin in AdminConfigSerializer.

Used by both the API and bootstrapped data.
"""
import logging
import sys
from typing import (
    Any,
    Dict,
    List,
)

from galaxy.managers import base
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.markdown_util import weasyprint_available
from galaxy.schema import SerializationParams
from galaxy.structured_app import StructuredApp
from galaxy.web.framework.base import server_starttime

log = logging.getLogger(__name__)


class ConfigurationManager:
    """Interface/service object for interacting with configuration and related data."""

    def __init__(self, app: StructuredApp):
        self._app = app

    def get_configuration(
        self, trans: ProvidesUserContext, serialization_params: SerializationParams
    ) -> Dict[str, Any]:
        is_admin = trans.user_is_admin
        host = getattr(trans, "host", None)
        serializer_class = AdminConfigSerializer if is_admin else ConfigSerializer
        serializer = serializer_class(self._app)
        return serializer.serialize_to_view(self._app.config, host=host, **serialization_params.dict())

    def version(self) -> Dict[str, Any]:
        version_info = {
            "version_major": self._app.config.version_major,
            "version_minor": self._app.config.version_minor,
        }
        if self._app.config.version_extra:
            version_info["extra"] = self._app.config.version_extra
        return version_info

    def decode_id(
        self,
        encoded_id: str,
    ) -> Dict[str, int]:
        # Handle the special case for library folders
        if (len(encoded_id) % 16 == 1) and encoded_id.startswith("F"):
            encoded_id = encoded_id[1:]
        decoded_id = self._app.security.decode_id(encoded_id)
        return {"decoded_id": decoded_id}

    def tool_lineages(self) -> List[Dict[str, Dict]]:
        rval = []
        for id, tool in self._app.toolbox.tools():
            try:
                lineage_dict = tool.lineage.to_dict()
            except AttributeError:
                pass
            else:
                entry = {"id": id, "lineage": lineage_dict}
                rval.append(entry)
        return rval

    def dynamic_tool_confs(self) -> List[Dict[str, str]]:
        # WARNING: If this method is ever changed so as not to require admin privileges, update the nginx proxy
        # documentation, since this path is used as an authentication-by-proxy method for securing other paths on the
        # server. A dedicated endpoint should probably be added to do that instead.
        def tool_conf_to_dict(conf):
            return dict(
                config_filename=conf["config_filename"],
                tool_path=conf["tool_path"],
            )

        confs = self._app.toolbox.dynamic_confs(include_migrated_tool_conf=True)
        return list(map(tool_conf_to_dict, confs))

    def reload_toolbox(self):
        self._app.queue_worker.send_control_task("reload_toolbox")


# TODO: this is a bit of an odd duck. It uses the serializer structure from managers
#   but doesn't have a model like them. It might be better in config.py or a
#   totally new area, but I'm leaving it in managers for now for class consistency.
class ConfigSerializer(base.ModelSerializer):
    """Configuration (galaxy.ini) settings viewable by all users"""

    def __init__(self, app):
        super().__init__(app)

        self.default_view = "all"
        self.add_view("all", list(self.serializers.keys()))

    def default_serializer(self, config, key):
        return getattr(config, key, None)

    def add_serializers(self):
        def _defaults_to(default) -> base.Serializer:
            return lambda item, key, **context: getattr(item, key, default)

        def _use_config(item, key: str, **context):
            """Let config object determine the value for key"""
            assert hasattr(item, key)
            return item.config_value_for_host(key, context.get("host"))

        def _config_is_truthy(item, key, **context):
            return True if item.get(key) else False

        self.serializers: Dict[str, base.Serializer] = {
            # TODO: this is available from user data, remove
            "is_admin_user": lambda *a, **c: False,
            "brand": _use_config,
            "logo_url": _use_config,
            "logo_src": _use_config,
            "logo_src_secondary": _use_config,
            "terms_url": _use_config,
            "wiki_url": _use_config,
            "screencasts_url": _use_config,
            "citation_url": _use_config,
            "support_url": _use_config,
            "quota_url": _use_config,
            "helpsite_url": _use_config,
            "lims_doc_url": _defaults_to("https://usegalaxy.org/u/rkchak/p/sts"),
            "default_locale": _use_config,
            "enable_tool_recommendations": _use_config,
            "enable_account_interface": _use_config,
            "tool_recommendation_model_path": _use_config,
            "admin_tool_recommendations_path": _use_config,
            "overwrite_model_recommendations": _use_config,
            "topk_recommendations": _use_config,
            "allow_user_impersonation": _use_config,
            "allow_user_creation": _defaults_to(False),  # schema default is True
            "use_remote_user": _defaults_to(None),  # schema default is False; or config.single_user
            "single_user": _config_is_truthy,
            "enable_oidc": _use_config,
            "oidc": _use_config,
            "prefer_custos_login": _use_config,
            "enable_quotas": _use_config,
            "remote_user_logout_href": _use_config,
            "post_user_logout_href": _use_config,
            "datatypes_disable_auto": _use_config,
            "allow_user_dataset_purge": _defaults_to(False),  # schema default is True
            "ga_code": _use_config,
            "plausible_server": _use_config,
            "plausible_domain": _use_config,
            "markdown_to_pdf_available": lambda item, key, **context: weasyprint_available(),
            "matomo_server": _use_config,
            "matomo_site_id": _use_config,
            "enable_unique_workflow_defaults": _use_config,
            "enable_beta_markdown_export": _use_config,
            "enable_beacon_integration": _use_config,
            "use_legacy_history": _use_config,
            "simplified_workflow_run_ui": _use_config,
            "simplified_workflow_run_ui_target_history": _use_config,
            "simplified_workflow_run_ui_job_cache": _use_config,
            "has_user_tool_filters": _defaults_to(False),
            # TODO: is there no 'correct' way to get an api url? controller='api', action='tools' is a hack
            # at any rate: the following works with path_prefix but is still brittle
            # TODO: change this to (more generic) upload_path and incorporate config.nginx_upload_path into building it
            "nginx_upload_path": lambda item, key, **context: getattr(item, key, False),
            "chunk_upload_size": _use_config,
            "ftp_upload_site": _use_config,
            "version_major": _defaults_to(None),
            "version_minor": _defaults_to(None),
            "version_extra": _use_config,
            "require_login": _use_config,
            "inactivity_box_content": _use_config,
            "visualizations_visible": _use_config,
            "interactivetools_enable": _use_config,
            "aws_estimate": _use_config,
            "message_box_content": _use_config,
            "message_box_visible": _use_config,
            "message_box_class": _use_config,
            "server_startttime": lambda item, key, **context: server_starttime,
            "mailing_join_addr": _defaults_to("galaxy-announce-join@bx.psu.edu"),  # should this be the schema default?
            "server_mail_configured": lambda item, key, **context: bool(item.smtp_server),
            "registration_warning_message": _use_config,
            "welcome_url": _use_config,
            "show_welcome_with_login": _defaults_to(True),  # schema default is False
            "cookie_domain": _use_config,
            "python": _defaults_to((sys.version_info.major, sys.version_info.minor)),
            "select_type_workflow_threshold": _use_config,
            "file_sources_configured": lambda item, key, **context: self.app.file_sources.custom_sources_configured,
            "toolbox_auto_sort": _use_config,
            "panel_views": lambda item, key, **context: self.app.toolbox.panel_view_dicts(),
            "default_panel_view": _use_config,
            "upload_from_form_button": _use_config,
            "release_doc_base_url": _use_config,
            "expose_user_email": _use_config,
            "enable_tool_source_display": _use_config,
            "enable_celery_tasks": _use_config,
            "user_library_import_dir_available": lambda item, key, **context: bool(item.get("user_library_import_dir")),
            "welcome_directory": _use_config,
            "themes": _use_config,
        }


class AdminConfigSerializer(ConfigSerializer):
    """Configuration attributes viewable only by admin users"""

    def add_serializers(self):
        super().add_serializers()

        def _defaults_to(default):
            return lambda config, key, **context: getattr(config, key, default)

        self.serializers.update(
            {
                # TODO: this is available from user serialization: remove
                "is_admin_user": lambda *a, **context: True,
                "library_import_dir": _defaults_to(None),
                "user_library_import_dir": _defaults_to(None),
                "allow_library_path_paste": _defaults_to(False),
                "allow_user_deletion": _defaults_to(False),
            }
        )
