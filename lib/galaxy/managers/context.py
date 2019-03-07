"""
Mixins for transaction-like objects.
"""
import string
from json import dumps

from six import text_type

from galaxy.exceptions import UserActivationRequiredException
from galaxy.util import bunch


class ProvidesAppContext(object):
    """ For transaction-like objects to provide Galaxy convience layer for
    database and event handling.

    Mixed in class must provide `app` property.
    """

    def log_action(self, user=None, action=None, context=None, params=None):
        """
        Application-level logging of user actions.
        """
        if self.app.config.log_actions:
            action = self.app.model.UserAction(action=action, context=context, params=text_type(dumps(params)))
            try:
                if user:
                    action.user = user
                else:
                    action.user = self.user
            except Exception:
                action.user = None
            try:
                action.session_id = self.galaxy_session.id
            except Exception:
                action.session_id = None
            self.sa_session.add(action)
            self.sa_session.flush()

    def log_event(self, message, tool_id=None, **kwargs):
        """
        Application level logging. Still needs fleshing out (log levels and such)
        Logging events is a config setting - if False, do not log.
        """
        if self.app.config.log_events:
            event = self.app.model.Event()
            event.tool_id = tool_id
            try:
                event.message = message % kwargs
            except Exception:
                event.message = message
            try:
                event.history = self.get_history()
            except Exception:
                event.history = None
            try:
                event.history_id = self.history.id
            except Exception:
                event.history_id = None
            try:
                event.user = self.user
            except Exception:
                event.user = None
            try:
                event.session_id = self.galaxy_session.id
            except Exception:
                event.session_id = None
            self.sa_session.add(event)
            self.sa_session.flush()

    @property
    def sa_session(self):
        """
        Returns a SQLAlchemy session -- currently just gets the current
        session from the threadlocal session context, but this is provided
        to allow migration toward a more SQLAlchemy 0.4 style of use.
        """
        return self.app.model.context.current

    def expunge_all(self):
        app = self.app
        context = app.model.context
        context.expunge_all()
        # This is a bit hacky, should refctor this. Maybe refactor to app -> expunge_all()
        if hasattr(app, 'install_model'):
            install_model = app.install_model
            if install_model != app.model:
                install_model.context.expunge_all()

    def get_toolbox(self):
        """Returns the application toolbox"""
        return self.app.toolbox

    @property
    def model(self):
        return self.app.model

    @property
    def install_model(self):
        return self.app.install_model


class ProvidesUserContext(object):
    """ For transaction-like objects to provide Galaxy convience layer for
    reasoning about users.

    Mixed in class must provide `user`, `api_inherit_admin`, and `app`
    properties.
    """

    @property
    def anonymous(self):
        return self.user is None and not self.api_inherit_admin

    def get_current_user_roles(self):
        user = self.user
        if user:
            roles = user.all_roles()
        else:
            roles = []
        return roles

    @property
    def user_is_admin(self):
        if self.api_inherit_admin:
            return True
        return self.user and self.user.email in self.app.config.admin_users_list

    @property
    def user_can_do_run_as(self):
        run_as_users = [user for user in self.app.config.get("api_allow_run_as", "").split(",") if user]
        if not run_as_users:
            return False
        user_in_run_as_users = self.user and self.user.email in run_as_users
        # Can do if explicitly in list or master_api_key supplied.
        can_do_run_as = user_in_run_as_users or self.api_inherit_admin
        return can_do_run_as

    @property
    def user_is_active(self):
        return not self.app.config.user_activation_on or self.user is None or self.user.active

    def check_user_activation(self):
        """If user activation is enabled and the user is not activated throw an exception."""
        if not self.user_is_active:
            raise UserActivationRequiredException()

    @property
    def user_ftp_dir(self):
        base_dir = self.app.config.ftp_upload_dir
        if base_dir is None:
            return None
        else:
            # e.g. 'email' or 'username'
            identifier_attr = self.app.config.ftp_upload_dir_identifier
            identifier_value = getattr(self.user, identifier_attr)
            template = self.app.config.ftp_upload_dir_template
            path = string.Template(template).safe_substitute(dict(
                ftp_upload_dir=base_dir,
                ftp_upload_dir_identifier=identifier_value,
            ))
            return path


class ProvidesHistoryContext(object):
    """ For transaction-like objects to provide Galaxy convience layer for
    reasoning about histories.

    Mixed in class must provide `user`, `history`, and `app`
    properties.
    """

    def db_dataset_for(self, dbkey):
        """
        Returns the db_file dataset associated/needed by `dataset`, or `None`.
        """
        # If no history, return None.
        if self.history is None:
            return None
        # TODO: when does this happen? is it Bunch or util.bunch.Bunch?
        if isinstance(self.history, bunch.Bunch):
            # The API presents a Bunch for a history.  Until the API is
            # more fully featured for handling this, also return None.
            return None
        datasets = self.sa_session.query(self.app.model.HistoryDatasetAssociation) \
                                  .filter_by(deleted=False, history_id=self.history.id, extension="len")
        for ds in datasets:
            if dbkey == ds.dbkey:
                return ds
        return None

    @property
    def db_builds(self):
        """
        Returns the builds defined by galaxy and the builds defined by
        the user (chromInfo in history).
        """
        # FIXME: This method should be removed
        return self.app.genome_builds.get_genome_build_names(trans=self)
