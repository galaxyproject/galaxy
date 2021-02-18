"""
Shared model and mapping code between Galaxy and Tool Shed, trying to
generalize to generic database connections.
"""
import threading
from inspect import (
    getmembers,
    isclass
)

from sqlalchemy import event
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker
)
try:
    from starlette_context import context as request_context
except ImportError:
    request_context = None

from galaxy.util.bunch import Bunch


def get_current_request():
    try:
        return request_context.data['X-Request-ID']
    except RuntimeError:
        return threading.get_ident()


# TODO: Refactor this to be a proper class, not a bunch.
class ModelMapping(Bunch):

    def __init__(self, model_modules, engine):
        self.engine = engine
        SessionLocal = sessionmaker(autoflush=False, autocommit=True)
        versioned_session(SessionLocal)
        context = scoped_session(SessionLocal, scopefunc=get_current_request if request_context is not None else None)
        # For backward compatibility with "context.current"
        # deprecated?
        context.current = context
        self._SessionLocal = SessionLocal
        self.session = context
        self.local_session = None

        model_classes = {}
        for module in model_modules:
            m_obs = getmembers(module, isclass)
            m_obs = dict([m for m in m_obs if m[1].__module__ == module.__name__])
            model_classes.update(m_obs)

        super().__init__(**model_classes)

        context.remove()
        context.configure(bind=engine)

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
