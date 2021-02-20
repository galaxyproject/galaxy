"""
Shared model and mapping code between Galaxy and Tool Shed, trying to
generalize to generic database connections.
"""
import threading
from contextvars import ContextVar
from inspect import (
    getmembers,
    isclass
)

from sqlalchemy import event
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker
)

from galaxy.util.bunch import Bunch

REQUEST_ID = ContextVar('request_id', default=None)


# TODO: Refactor this to be a proper class, not a bunch.
class ModelMapping(Bunch):

    def __init__(self, model_modules, engine):
        self.engine = engine
        SessionLocal = sessionmaker(autoflush=False, autocommit=True)
        versioned_session(SessionLocal)
        context = scoped_session(SessionLocal, scopefunc=self.request_scopefunc)
        # For backward compatibility with "context.current"
        # deprecated?
        context.current = context
        self._SessionLocal = SessionLocal
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

    def request_scopefunc(self):
        """
        Return a value that is used as dictionary key for sqlalchemy's ScopedRegistry.

        This ensures that threads or request contexts will receive a single identical session
        from the ScopedRegistry.
        """
        return REQUEST_ID.get() or threading.get_ident()

    def set_request_id(self, request_id):
        REQUEST_ID.set(request_id)

    def unset_request_id(self, request_id):
        # Unconditionally calling self.gx_app.model.session.remove()
        # would create a new session if the session was not accessed
        # in a request, so we check if there is a sqlalchemy session
        # for the current request in the registry.
        if request_id in self.scoped_registry.registry:
            self.session.remove()

    @property
    def context(self):
        return self.session

    @property
    def Session(self):
        """
        For backward compat., deprecated.
        """
        return self.context


def versioned_objects(iter):
    for obj in iter:
        if hasattr(obj, '__create_version__'):
            yield obj


def versioned_session(session):
    @event.listens_for(session, 'before_flush')
    def before_flush(session, flush_context, instances):
        for obj in versioned_objects(session.dirty):
            obj.__create_version__(session)
        for obj in versioned_objects(session.deleted):
            obj.__create_version__(session, deleted=True)
