"""
Shared model and mapping code between Galaxy and Tool Shed, trying to
generalize to generic database connections.
"""
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


# TODO: Refactor this to be a proper class, not a bunch.
class ModelMapping(Bunch):

    def __init__(self, model_modules, engine):
        self.engine = engine
        SessionLocal = sessionmaker(autoflush=False, autocommit=True)
        versioned_session(SessionLocal)
        context = scoped_session(SessionLocal)
        # For backward compatibility with "context.current"
        # deprecated?
        context.current = context
        self._SessionLocal = SessionLocal
        self._session = context
        self.local_session = None

        model_classes = {}
        for module in model_modules:
            m_obs = getmembers(module, isclass)
            m_obs = dict([m for m in m_obs if m[1].__module__ == module.__name__])
            model_classes.update(m_obs)

        super().__init__(**model_classes)

        context.remove()
        context.configure(bind=engine)

    def set_local_session(self):
        self.session = self._SessionLocal()

    def dispose_local_session(self):
        self.session = None

    @property
    def session(self):
        return self.local_session or self._session

    @session.setter
    def session(self, session):
        # For backward compatibility with "context.current"
        if session:
            session.current = session
        self.local_session = session

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
