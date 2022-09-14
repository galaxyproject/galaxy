"""Interfaces/mixins for transaction-like objects.

These objects describe the context around a unit of work. This unit of work
is very broad and can be anything from the response to a web request, the
scheduling of a workflow, the reloading the toolbox, etc.. Traditionally,
Galaxy has simply passed around a GalaxyWebTransaction object through
all layers and large components of the Galaxy app. Having random backend
components define explicit dependencies on this however is inappropriate
because Galaxy may not be used in all sort of non-web contexts. The future
use of message queues and web sockets as well as the decomposition of the
backend into packages only further make this heavy reliance on
GalaxyWebTransaction inappropriate.

A better approach is for components to annotate their reliance on much
narrower, typed views of the GalaxyWebTransaction. This allows explicit
declaration of what is being required in the context of a method or class
and allows the Python type system to ensure the transaction supplied to
the method is appropriate for the context. For instance, an effective
use of the type system in this way can prevent the backend work context
used to schedule workflow from being supplied to a method that requires
an older-style WSGI web response object.

There are various levels of transactions defined in this file - these
include :class:`galaxy.managers.context.ProvidesAppContext`,
:class:`galaxy.managers.context.ProvidesUserContext`,
and :class:`galaxy.managers.context.ProvidesHistoryContext`. Methods
should annotate their dependency on the narrowest context they require.
A method that requires a user but not a history should declare its
``trans`` argument as requiring type :class:`galaxy.managers.context.ProvidesUserContext`.
"""
# TODO: Refactor this class so that galaxy.managers depends on a package
# containing this.
# TODO: Provide different classes for real users and potentially bootstrapped
# users so the framework can provide consistent web exceptions for incorrect
# user being used in that context and so that the type system can provide
# more checks against this issue.
import abc
import string
from json import dumps
from typing import (
    Callable,
    List,
    Optional,
)

from galaxy.exceptions import (
    AuthenticationRequired,
    UserActivationRequiredException,
)
from galaxy.model import (
    Dataset,
    History,
    HistoryDatasetAssociation,
    Role,
)
from galaxy.model.base import ModelMapping
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.tasks import RequestUser
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.security.vault import UserVaultWrapper
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import bunch


class ProvidesAppContext:
    """For transaction-like objects to provide Galaxy convenience layer for
    database and event handling.

    Mixed in class must provide `app` property.
    """

    @abc.abstractproperty
    def app(self) -> MinimalManagerApp:
        """Provide access to the Galaxy ``app`` object."""

    @abc.abstractproperty
    def url_builder(self) -> Optional[Callable[..., str]]:
        """
        Provide access to Galaxy URLs (if available).

        :type   qualified:  bool
        :param  qualified:  if True, the fully qualified URL is returned,
                            else a relative URL is returned (default False).
        """

    @property
    def security(self) -> IdEncodingHelper:
        """Provide access to Galaxy app's id encoding helper.

        :rtype: IdEncodingHelper
        """
        return self.app.security

    def log_action(self, user=None, action=None, context=None, params=None):
        """
        Application-level logging of user actions.
        """
        if self.app.config.log_actions:
            action = self.app.model.UserAction(action=action, context=context, params=str(dumps(params)))
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
    def sa_session(self) -> galaxy_scoped_session:
        """Provide access to Galaxy's SQLAlchemy session.

        :rtype: galaxy.model.scoped_session.galaxy_scoped_session
        """
        return self.app.model.session

    def expunge_all(self):
        """Expunge all the objects in Galaxy's SQLAlchemy sessions."""
        app = self.app
        context = app.model.context
        context.expunge_all()
        # This is a bit hacky, should refctor this. Maybe refactor to app -> expunge_all()
        if hasattr(app, "install_model"):
            install_model = app.install_model
            if install_model != app.model:
                install_model.context.expunge_all()

    def get_toolbox(self):
        """Returns the application toolbox.

        :rtype: galaxy.tools.ToolBox
        """
        return self.app.toolbox

    @property
    def model(self) -> ModelMapping:
        """Provide access to Galaxy's model mapping class.

        This is sometimes used for quick access to classes in
        :mod:`galaxy.model` but this is discouraged. Those classes
        should be imported by the consumer for stronger static
        checking.

        This is more proper use for this is accessing the threadbound
        SQLAlchemy session or engine.

        :rtype: galaxy.model.base.ModelMapping
        """
        return self.app.model

    @property
    def install_model(self) -> ModelMapping:
        """Provide access to Galaxy's install mapping.

        Comments on the ``model`` property apply here also.
        """
        return self.app.install_model


class ProvidesUserContext(ProvidesAppContext):
    """For transaction-like objects to provide Galaxy convenience layer for
    reasoning about users.

    Mixed in class must provide `user` and `app`
    properties.
    """

    @property
    def async_request_user(self) -> RequestUser:
        if self.user is None:
            raise AuthenticationRequired("The async task requires user authentication.")
        return RequestUser(user_id=self.user.id)

    @abc.abstractproperty
    def user(self):
        """Provide access to the user object."""

    @property
    def user_vault(self):
        """Provide access to a user's personal vault."""
        return UserVaultWrapper(self.app.vault, self.user)

    @property
    def anonymous(self) -> bool:
        return self.user is None

    def get_current_user_roles(self) -> List[Role]:
        user = self.user
        if user:
            roles = user.all_roles()
        else:
            roles = []
        return roles

    @property
    def user_is_admin(self) -> bool:
        return self.app.config.is_admin_user(self.user)

    @property
    def user_is_bootstrap_admin(self) -> bool:
        """Master key provided so there is no real user"""
        return not self.anonymous and self.user.bootstrap_admin_user

    @property
    def user_can_do_run_as(self) -> bool:
        return self.app.user_manager.user_can_do_run_as(self.user)

    @property
    def user_is_active(self) -> bool:
        return not self.app.config.user_activation_on or self.user is None or self.user.active

    def check_user_activation(self):
        """If user activation is enabled and the user is not activated throw an exception."""
        if not self.user_is_active:
            raise UserActivationRequiredException()

    @property
    def user_ftp_dir(self) -> Optional[str]:
        base_dir = self.app.config.ftp_upload_dir
        if base_dir is None or self.user is None:
            return None
        else:
            # e.g. 'email' or 'username'
            identifier_attr = self.app.config.ftp_upload_dir_identifier
            identifier_value = getattr(self.user, identifier_attr)
            template = self.app.config.ftp_upload_dir_template
            path = string.Template(template).safe_substitute(
                dict(
                    ftp_upload_dir=base_dir,
                    ftp_upload_dir_identifier=identifier_value,
                )
            )
            return path


class ProvidesHistoryContext(ProvidesUserContext):
    """For transaction-like objects to provide Galaxy convenience layer for
    reasoning about histories.

    Mixed in class must provide `user`, `history`, and `app`
    properties.
    """

    @abc.abstractproperty
    def history(self) -> Optional[History]:
        """Provide access to the user's current history model object.

        :rtype: Optional[galaxy.model.History]
        """

    def db_dataset_for(self, dbkey) -> Optional[HistoryDatasetAssociation]:
        """Optionally return the db_file dataset associated/needed by `dataset`."""
        # If no history, return None.
        if self.history is None:
            return None
        # TODO: when does this happen? is it Bunch or util.bunch.Bunch?
        if isinstance(self.history, bunch.Bunch):
            # The API presents a Bunch for a history.  Until the API is
            # more fully featured for handling this, also return None.
            return None
        non_ready_or_ok = set(Dataset.non_ready_states)
        non_ready_or_ok.add(HistoryDatasetAssociation.states.OK)
        datasets = (
            self.sa_session.query(HistoryDatasetAssociation)
            .filter_by(deleted=False, history_id=self.history.id, extension="len")
            .filter(
                HistoryDatasetAssociation.table.c._state.in_(non_ready_or_ok),
            )
        )
        valid_ds = None
        for ds in datasets:
            if ds.dbkey == dbkey:
                if ds.state == HistoryDatasetAssociation.states.OK:
                    return ds
                valid_ds = ds
        return valid_ds

    @property
    def db_builds(self):
        """
        Returns the builds defined by galaxy and the builds defined by
        the user (chromInfo in history).
        """
        # FIXME: This method should be removed
        return self.app.genome_builds.get_genome_build_names(trans=self)
