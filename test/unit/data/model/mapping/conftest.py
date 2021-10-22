import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


@pytest.fixture(scope='module')
def engine():
    db_uri = 'sqlite:///:memory:'
    return create_engine(db_uri)


@pytest.fixture
def session(init_model, engine):
    """
    init_model is a fixture that must be defined in the test module using the
    session fixture (or in any other discoverable location). Ideally, it will
    have module scope and will initialize the models in the database. It must
    use the same engine as this fixture. For example:

    @pytest.fixture(scope='module')
    def init_model(engine):
        model.mapper_registry.metadata.create_all(engine)
    """
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)
    yield Session()
    Session.remove()
