"""
Contains the main interface in the Universe class
"""

import logging

from webob.exc import HTTPNotFound

from galaxy import web
from galaxy.managers.histories import (
    HistoryManager,
    HistorySerializer,
)
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.structured_app import StructuredApp
from galaxy.util import unicodify
from galaxy.webapps.base import controller
from ..api import depends

log = logging.getLogger(__name__)


# =============================================================================
class RootController(controller.JSAppLauncher, UsesAnnotations):
    """
    Controller class that maps to the url root of Galaxy (i.e. '/').
    """

    history_manager: HistoryManager = depends(HistoryManager)
    history_serializer: HistorySerializer = depends(HistorySerializer)

    def __init__(self, app: StructuredApp):
        super().__init__(app)

    @web.expose
    def default(self, trans, target1=None, target2=None, **kwd):
        """
        Called on any url that does not match a controller method.
        """
        raise HTTPNotFound("This link may not be followed from within Galaxy.")

    @web.expose
    def index(self, trans, tool_id=None, workflow_id=None, history_id=None, m_c=None, m_a=None, **kwd):
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
    def login(self, trans, redirect=None, is_logout_redirect=False, **kwd):
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
        return self.template(
            trans,
            "login",
            redirect=redirect,
            # an installation may have it's own welcome_url - show it here if they've set that
            welcome_url=web.url_for(controller="root", action="welcome"),
            show_welcome_with_login=trans.app.config.show_welcome_with_login,
        )

    # ---- Tool related -----------------------------------------------------

    @web.expose
    def display_as(self, trans, id=None, display_app=None, **kwd):
        """Returns a file in a format that can successfully be displayed in display_app."""
        # TODO: unencoded id
        data = trans.sa_session.query(self.app.model.HistoryDatasetAssociation).get(id)
        authz_method = "rbac"
        if "authz_method" in kwd:
            authz_method = kwd["authz_method"]
        if data:
            if authz_method == "rbac" and trans.app.security_agent.can_access_dataset(
                trans.get_current_user_roles(), data.dataset
            ):
                trans.response.set_content_type(data.get_mime())
                trans.log_event(f"Formatted dataset id {str(id)} for display at {display_app}")
                return data.as_display_type(display_app, **kwd)
            elif authz_method == "display_at" and trans.app.host_security_agent.allow_action(
                trans.request.remote_addr, data.permitted_actions.DATASET_ACCESS, dataset=data
            ):
                trans.response.set_content_type(data.get_mime())
                return data.as_display_type(display_app, **kwd)
            else:
                return "You are not allowed to access this dataset."
        else:
            return "No data with id=%d" % id

    # ---- History management -----------------------------------------------
    @web.expose
    def clear_history(self, trans):
        """Clears the history for a user."""
        # TODO: unused? (seems to only be used in TwillTestCase)
        history = trans.get_history()
        for dataset in history.datasets:
            dataset.deleted = True
            dataset.clear_associated_files()
        trans.sa_session.flush()
        trans.log_event(f"History id {str(history.id)} cleared")
        trans.response.send_redirect(web.url_for("/index"))

    @web.expose
    def history_import(self, trans, id=None, confirm=False, **kwd):
        # TODO: unused?
        # TODO: unencoded id
        user = trans.get_user()
        user_history = trans.get_history()
        if not id:
            return trans.show_error_message("You must specify a history you want to import.")
        import_history = trans.sa_session.query(trans.app.model.History).get(id)
        if not import_history:
            return trans.show_error_message("The specified history does not exist.")
        if user:
            if import_history.user_id == user.id:
                return trans.show_error_message("You cannot import your own history.")
            new_history = import_history.copy(target_user=trans.user)
            new_history.name = f"imported: {new_history.name}"
            new_history.user_id = user.id
            galaxy_session = trans.get_galaxy_session()
            try:
                association = (
                    trans.sa_session.query(trans.app.model.GalaxySessionToHistoryAssociation)
                    .filter_by(session_id=galaxy_session.id, history_id=new_history.id)
                    .first()
                )
            except Exception:
                association = None
            new_history.add_galaxy_session(galaxy_session, association=association)
            trans.sa_session.add(new_history)
            trans.sa_session.flush()
            if not user_history.datasets:
                trans.set_history(new_history)
            trans.log_event(f"History imported, id: {str(new_history.id)}, name: '{new_history.name}': ")
            return trans.show_ok_message(
                """
                History "{}" has been imported. Click <a href="{}">here</a>
                to begin.""".format(
                    new_history.name, web.url_for("/")
                )
            )
        elif not user_history.datasets or confirm:
            new_history = import_history.copy()
            new_history.name = f"imported: {new_history.name}"
            new_history.user_id = None
            galaxy_session = trans.get_galaxy_session()
            try:
                association = (
                    trans.sa_session.query(trans.app.model.GalaxySessionToHistoryAssociation)
                    .filter_by(session_id=galaxy_session.id, history_id=new_history.id)
                    .first()
                )
            except Exception:
                association = None
            new_history.add_galaxy_session(galaxy_session, association=association)
            trans.sa_session.add(new_history)
            trans.sa_session.flush()
            trans.set_history(new_history)
            trans.log_event(f"History imported, id: {str(new_history.id)}, name: '{new_history.name}': ")
            return trans.show_ok_message(
                """
                History "{}" has been imported. Click <a href="{}">here</a>
                to begin.""".format(
                    new_history.name, web.url_for("/")
                )
            )
        return trans.show_warn_message(
            """
            Warning! If you import this history, you will lose your current
            history. Click <a href="%s">here</a> to confirm.
            """
            % web.url_for(controller="root", action="history_import", id=id, confirm=True)
        )

    @web.expose
    def history_new(self, trans, name=None):
        """Create a new history with the given name
        and refresh the history panel.
        """
        trans.new_history(name=name)
        trans.log_event(f"Created new History, id: {str(trans.history.id)}.")
        return trans.show_message("New history created", refresh_frames=["history"])

    @web.expose
    def history_add_to(
        self,
        trans,
        history_id=None,
        file_data=None,
        name="Data Added to History",
        info=None,
        ext="txt",
        dbkey="?",
        copy_access_from=None,
        **kwd,
    ):
        """Adds a POSTed file to a History."""
        # TODO: unencoded id
        try:
            history = trans.sa_session.query(trans.app.model.History).get(history_id)
            data = trans.app.model.HistoryDatasetAssociation(
                name=name, info=info, extension=ext, dbkey=dbkey, create_dataset=True, sa_session=trans.sa_session
            )
            if copy_access_from:
                copy_access_from = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(
                    copy_access_from
                )
                trans.app.security_agent.copy_dataset_permissions(copy_access_from.dataset, data.dataset)
            else:
                permissions = trans.app.security_agent.history_get_default_permissions(history)
                trans.app.security_agent.set_all_dataset_permissions(data.dataset, permissions)
            trans.sa_session.add(data)
            trans.sa_session.flush()
            data_file = open(data.file_name, "wb")
            file_data.file.seek(0)
            data_file.write(file_data.file.read())
            data_file.close()
            data.state = data.states.OK
            data.set_size()
            data.init_meta()
            data.set_meta()
            trans.sa_session.flush()
            history.add_dataset(data)
            trans.sa_session.flush()
            data.set_peek()
            trans.sa_session.flush()
            trans.log_event("Added dataset %d to history %d" % (data.id, trans.history.id))
            return trans.show_ok_message(f"Dataset {str(data.hid)} added to history {str(history_id)}.")
        except Exception as e:
            msg = f"Failed to add dataset to history: {unicodify(e)}"
            log.error(msg)
            trans.log_event(msg)
            return trans.show_error_message("Adding File to History has Failed")

    @web.expose
    def welcome(self, trans):
        welcome_url = trans.app.config.config_value_for_host("welcome_url", trans.host)
        return trans.response.send_redirect(web.url_for(welcome_url))
