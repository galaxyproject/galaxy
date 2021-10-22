import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


@pytest.fixture(scope='module')
def engine():
    db_uri = 'sqlite:///:memory:'
    return create_engine(db_uri)


@pytest.fixture
def session(init_model, engine):
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)
    yield Session()
    Session.remove()
