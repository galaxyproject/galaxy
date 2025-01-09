"""
Shared model and mapping code between Galaxy and Tool Shed, trying to
generalize to generic database connections.
"""

import contextlib
import logging
import os
import threading
from contextvars import ContextVar
from inspect import (
    getmembers,
    isclass,
)
from typing import (
    Dict,
    Type,
    TYPE_CHECKING,
    Union,
)

from sqlalchemy import event
from sqlalchemy.orm import (
    object_session,
    scoped_session,
    Session,
    sessionmaker,
)

from galaxy.util.bunch import Bunch

if TYPE_CHECKING:
    from galaxy.model.store import SessionlessContext

log = logging.getLogger(__name__)

# Create a ContextVar with mutable state, this allows sync tasks in the context
# of a request (which run within a threadpool) to see changes to the ContextVar
# state. See https://github.com/tiangolo/fastapi/issues/953#issuecomment-586006249
# for details
REQUEST_ID: ContextVar[Union[Dict[str, str], None]] = ContextVar("request_id", default=None)


@contextlib.contextmanager
def transaction(session: Union[scoped_session, Session, "SessionlessContext"]):
    """Start a new transaction only if one is not present."""
    # TODO The `session.begin` code has been removed. Once we can verify this does not break SQLAlchemy transactions, remove this helper + all references (561)
    # temporary hack; need to fix access to scoped_session callable, not proxy
    if isinstance(session, scoped_session):
        session = session()
    # hack: this could be model.store.SessionlessContext; then we don't need to do anything
    elif not isinstance(session, Session):
        yield
        return  # exit: can't use as a Session

    yield


def check_database_connection(session):
    """
    In the event of a database disconnect, if there exists an active database
    transaction, that transaction becomes invalidated. Accessing the database
    will raise sqlalchemy.exc.PendingRollbackError. This handles this situation
    by rolling back the invalidated transaction.
    Ref: https://docs.sqlalchemy.org/en/14/errors.html#can-t-reconnect-until-invalid-transaction-is-rolled-back
    """
    assert session
    if isinstance(session, scoped_session):
        session = session()
    trans = session.get_transaction()
    if (trans and not trans.is_active) or session.connection().invalidated:
        session.rollback()
        log.error("Database transaction rolled back due to inactive session transaction or invalid connection state.")


# TODO: Refactor this to be a proper class, not a bunch.
class ModelMapping(Bunch):
    def __init__(self, model_modules, engine):
        self.engine = engine
        self._SessionLocal = sessionmaker(autoflush=False)
        versioned_session(self._SessionLocal)
        context = scoped_session(self._SessionLocal, scopefunc=self.request_scopefunc)
        # For backward compatibility with "context.current"
        # deprecated?
        context.current = context
        self.session = context
        self.scoped_registry = context.registry

        model_classes = {}
        for module in model_modules:
            m_obs = getmembers(module, isclass)
            m_obs = dict([m for m in m_obs if m[1].__module__ == module.__name__])
            model_classes.update(m_obs)

        super().__init__(**model_classes)

        context.remove()
        context.configure(bind=engine)

    def new_session(self):
        """
        Return a new non-scoped Session object.

        Use this when we need to operate on ORM entities, so a Connection object would be
        insufficient; yet the operation must be independent of the main session (self.session).
        """
        return self._SessionLocal()

    def request_scopefunc(self):
        """
        Return a value that is used as dictionary key for SQLAlchemy's ScopedRegistry.

        This ensures that threads or request contexts will receive a single identical session
        from the ScopedRegistry.
        """
        return REQUEST_ID.get({}).get("request") or threading.get_ident()

    @staticmethod
    def set_request_id(request_id):
        # Set REQUEST_ID to a new dict.
        # This new ContextVar value will only be seen by the current asyncio context
        # and descendant threadpools, but not other threads or asyncio contexts.
        return REQUEST_ID.set({"request": request_id})

    def unset_request_id(self, request_id):
        # Unconditionally calling self.gx_app.model.session.remove()
        # would create a new session if the session was not accessed
        # in a request, so we check if there is a sqlalchemy session
        # for the current request in the registry.
        if request_id in self.scoped_registry.registry:
            self.scoped_registry.registry[request_id].close()
            del self.scoped_registry.registry[request_id]

    @property
    def context(self) -> scoped_session:
        return self.session

    @property
    def Session(self):
        """
        For backward compat., deprecated.
        """
        return self.context


class SharedModelMapping(ModelMapping):
    """Model mapping containing references to classes shared between Galaxy and ToolShed.

    Generally things can be more strongly typed when importing models directly, but we need
    a way to do app.model.<CLASS> for common code shared by the tool shed and Galaxy.
    """

    User: Type
    GalaxySession: Type
    APIKeys: Type
    PasswordResetToken: Type


def versioned_objects(iter):
    for obj in iter:
        if hasattr(obj, "__create_version__"):
            yield obj


def versioned_objects_strict(iter):
    for obj in iter:
        if hasattr(obj, "__strict_check_before_flush__"):
            obj.__strict_check_before_flush__()
        if hasattr(obj, "__create_version__"):
            yield obj


def get_before_flush_handler():
    if os.environ.get("GALAXY_TEST_RAISE_EXCEPTION_ON_HISTORYLESS_HDA"):
        log.debug("Using strict flush checks")

        def before_flush(session, flush_context, instances):
            for obj in session.new:
                if hasattr(obj, "__strict_check_before_flush__"):
                    obj.__strict_check_before_flush__()
            for obj in versioned_objects_strict(session.dirty):
                obj.__create_version__(session)
            for obj in versioned_objects_strict(session.deleted):
                obj.__create_version__(session, deleted=True)

    else:

        def before_flush(session, flush_context, instances):
            for obj in versioned_objects(session.dirty):
                obj.__create_version__(session)
            for obj in versioned_objects(session.deleted):
                obj.__create_version__(session, deleted=True)

    return before_flush


def versioned_session(session):
    event.listens_for(session, "before_flush")(get_before_flush_handler())


def ensure_object_added_to_session(object_to_add, *, object_in_session=None, session=None) -> bool:
    """
    This function is intended as a safeguard to mimic pre-SQLAlchemy 2.0 behavior.
    `object_to_add` was implicitly merged into a Session prior to SQLAlchemy 2.0, which was indicated
    by `RemovedIn20Warning` warnings logged while running Galaxy's tests. (See https://github.com/galaxyproject/galaxy/issues/12541)
    As part of the upgrade to 2.0, the `cascade_backrefs=False` argument was added to the relevant relationships that turned off this behavior.
    This function is called from the code that triggered these warnings, thus emulating the cascading behavior.
    The intention is to remove all such calls, as well as this function definition, after the move to SQLAlchemy 2.0.
    # Ref: https://docs.sqlalchemy.org/en/14/changelog/migration_14.html#cascade-backrefs-behavior-deprecated-for-removal-in-2-0
    """
    if session:
        session.add(object_to_add)
        return True
    if object_in_session:
        session = object_session(object_in_session)
        if session:
            session.add(object_to_add)
            return True
    return False
