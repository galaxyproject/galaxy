import pytest

from galaxy.model import tool_shed_install as model
from ...common import dbcleanup_wrapper

# Fixtures yielding persisted instances of models, deleted from the database on test exit.


@pytest.fixture(scope="module")
def init_model(engine):
    """
    This fixture initialized the models in the database. It should use the same
    `engine` as the `session` used by the model fixtures defined in this module.
    """
    # `model` is defined in this module, which is why this fixture should not be
    # factored out into conftest.py (Even though it would work, it would be very easy
    # to overwrite the `model` variable by importing a different module as `model`.)
    model.mapper_registry.metadata.create_all(engine)


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
