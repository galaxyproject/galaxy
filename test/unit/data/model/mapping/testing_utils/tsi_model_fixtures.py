import pytest

from galaxy.model import tool_shed_install as model
from ...testing_utils import (
    dbcleanup_wrapper,
    initialize_model,
)


@pytest.fixture(scope="module")
def init_model(engine):
    """Create model objects in the engine's database."""
    # Must use the same engine as the session fixture used by this module.
    initialize_model(model.mapper_registry, engine)


# Fixtures yielding persisted instances of models, deleted from the database on test exit.


@pytest.fixture
def repository(session):
    instance = model.ToolShedRepository()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def repository_repository_dependency_association(session):
    instance = model.RepositoryRepositoryDependencyAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def repository_dependency(session, repository):
    instance = model.RepositoryDependency(repository.id)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def tool_dependency(session, repository):
    instance = model.ToolDependency()
    instance.tool_shed_repository = repository
    instance.status = "a"
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def tool_version(session):
    instance = model.ToolVersion()
    yield from dbcleanup_wrapper(session, instance)


# Fixtures yielding factory functions.


@pytest.fixture
def tool_version_association_factory():
    def make_instance(*args, **kwds):
        return model.ToolVersionAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def tool_version_factory():
    def make_instance(*args, **kwds):
        return model.ToolVersion(*args, **kwds)

    return make_instance
