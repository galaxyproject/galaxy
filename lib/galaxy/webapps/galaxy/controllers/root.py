"""
Contains the main interface in the Universe class
"""

import logging

from webob.exc import HTTPNotFound

from galaxy import (
    exceptions,
    web,
)
from galaxy.managers.histories import HistoryManager
from galaxy.model import HistoryDatasetAssociation
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.structured_app import StructuredApp
from galaxy.webapps.base import controller
from galaxy.webapps.base.webapp import GalaxyWebTransaction
from ..api import depends

log = logging.getLogger(__name__)


# =============================================================================
class RootController(controller.JSAppLauncher, UsesAnnotations):
    """
    Controller class that maps to the url root of Galaxy (i.e. '/').
    """

    app: StructuredApp
    history_manager: HistoryManager = depends(HistoryManager)

    def __init__(self, app: StructuredApp):
        super().__init__(app)

    @web.expose
    def default(self, trans, target1=None, target2=None, **kwd):
        """
        Called on any url that does not match a controller method.
        """
        raise HTTPNotFound("This link may not be followed from within Galaxy.")

    @web.expose
    def index(
        self, trans: GalaxyWebTransaction, tool_id=None, workflow_id=None, history_id=None, m_c=None, m_a=None, **kwd
    ):
        """
        Root and entry point for client-side web app.

        :type       tool_id: str or None
        :param      tool_id: load center panel with given tool if not None
        :type   workflow_id: encoded id or None
        :param  workflow_id: load center panel with given workflow if not None
        :type    history_id: encoded id or None
        :param   history_id: switch current history to given history if not None
        :type           m_c: str or None
        :param          m_c: controller name (e.g. 'user')
        :type           m_a: str or None
        :param          m_a: controller method/action (e.g. 'dbkeys')

        If m_c and m_a are present, the center panel will be loaded using the
        controller and action as a url: (e.g. 'user/dbkeys').
        """

        self._check_require_login(trans)

        # if a history_id was sent, attempt to switch to that history
        history = trans.history
        if history_id:
            unencoded_id = trans.security.decode_id(history_id)
            history = self.history_manager.get_owned(unencoded_id, trans.user)
            trans.set_history(history)
        return self._bootstrapped_client(trans)

    @web.expose
    def login(self, trans: GalaxyWebTransaction, redirect=None, is_logout_redirect=False, **kwd):
        """
        User login path for client-side.
        """
        # directly redirect to oidc provider if 1) enable_oidc is True, 2)
        # there is only one oidc provider, 3) auth_conf.xml has no authenticators
        if (
            trans.app.config.enable_oidc
            and len(trans.app.config.oidc) == 1
            and len(trans.app.auth_manager.authenticators) == 0
            and is_logout_redirect is False
        ):
            provider = next(iter(trans.app.config.oidc.keys()))
            success, message, redirect_uri = trans.app.authnz_manager.authenticate(provider, trans)
            if success:
                return trans.response.send_redirect(redirect_uri)
        return trans.response.send_redirect(web.url_for(controller="login", action="start", redirect=redirect))

    # ---- Tool related -----------------------------------------------------

    @web.expose
    def display_as(self, trans: GalaxyWebTransaction, id=None, display_app=None, **kwd):
        """
        Returns a file in a format that can successfully be displayed in display_app;
        if the file could not be returned, returns a message as a string.
        """
        # TODO: unencoded id
        data = trans.sa_session.query(HistoryDatasetAssociation).get(id)
        authz_method = kwd.get("authz_method", "rbac")
        if data:
            if authz_method == "rbac" and trans.app.security_agent.can_access_dataset(
                trans.get_current_user_roles(), data.dataset
            ):
                pass
            elif authz_method == "display_at" and trans.app.host_security_agent.allow_action(
                trans.request.remote_addr, data.permitted_actions.DATASET_ACCESS, dataset=data
            ):
                pass
            else:
                trans.response.status = 403
                return "You are not allowed to access this dataset."
            try:
                self.app.hda_manager.ensure_dataset_on_disk(trans, data)
            except exceptions.MessageException as e:
                trans.response.status = e.status_code
                return str(e)
            trans.response.set_content_type(data.get_mime())
            trans.log_event(f"Formatted dataset id {str(id)} for display at {display_app}")
            return data.as_display_type(display_app, **kwd)
        else:
            trans.response.status = 400
            return f"No data with id={id}"

    @web.expose
    def welcome(self, trans: GalaxyWebTransaction, **kwargs):
        welcome_url = trans.app.config.config_value_for_host("welcome_url", trans.host)
        return trans.response.send_redirect(web.url_for(welcome_url))
