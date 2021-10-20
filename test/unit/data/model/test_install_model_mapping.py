from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import (
    delete,
    select,
)

import galaxy.model.tool_shed_install.mapping as mapping


class BaseTest:
    @pytest.fixture
    def cls_(self, model):
        """
        Return class under test.
        Assumptions: if the class under test is Foo, then the class grouping
        the tests should be a subclass of BaseTest, named TestFoo.
        """
        prefix = len('Test')
        class_name = self.__class__.__name__[prefix:]
        return getattr(model, class_name)


class TestToolShedRepository(BaseTest):

    def test_table(self, cls_):
        assert cls_.table.name == 'tool_shed_repository'
        # assert cls_.__tablename__ == 'tool_shed_repository'  # TODO

    def test_columns(self, session, cls_, repository):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        tool_shed = 'a'
        name = 'b'
        description = 'c'
        owner = 'd'
        installed_changeset_revision = 'e'
        changeset_revision = 'f'
        ctx_rev = 'g'
        metadata = 'h'
        includes_datatypes = True
        tool_shed_status = 'i'
        deleted = True
        uninstalled = True
        dist_to_shed = True
        status = 'j'
        error_message = 'k'

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.tool_shed = tool_shed
        obj.name = name
        obj.description = description
        obj.owner = owner
        obj.installed_changeset_revision = installed_changeset_revision
        obj.changeset_revision = changeset_revision
        obj.ctx_rev = ctx_rev
        obj.metadata = metadata
        obj.includes_datatypes = includes_datatypes
        obj.tool_shed_status = tool_shed_status
        obj.deleted = deleted
        obj.uninstalled = uninstalled
        obj.dist_to_shed = dist_to_shed
        obj.status = status
        obj.error_message = error_message

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.tool_shed == tool_shed
            assert stored_obj.name == name
            assert stored_obj.description == description
            assert stored_obj.owner == owner
            assert stored_obj.installed_changeset_revision == installed_changeset_revision
            assert stored_obj.changeset_revision == changeset_revision
            assert stored_obj.ctx_rev == ctx_rev
            assert stored_obj.metadata == metadata
            assert stored_obj.includes_datatypes == includes_datatypes
            assert stored_obj.tool_shed_status == tool_shed_status
            assert stored_obj.deleted == deleted
            assert stored_obj.uninstalled == uninstalled
            assert stored_obj.dist_to_shed == dist_to_shed
            assert stored_obj.status == status
            assert stored_obj.error_message == error_message

    def test_relationships(
        self,
        session, cls_,
        repository,
        tool_version,
        tool_dependency,
        repository_repository_dependency_association,
    ):
        obj = cls_()
        obj.tool_versions.append(tool_version)
        obj.tool_dependencies.append(tool_dependency)
        obj.required_repositories.append(repository_repository_dependency_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.tool_versions == [tool_version]
            assert stored_obj.tool_dependencies == [tool_dependency]
            assert stored_obj.required_repositories == [repository_repository_dependency_association]


class TestRepositoryRepositoryDependencyAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.table.name == 'repository_repository_dependency_association'
        # assert cls_.__tablename__ == 'repository_dependency'  # TODO

    def test_columns(self, session, cls_, repository, repository_dependency):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.repository = repository
        obj.repository_dependency = repository_dependency

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.tool_shed_repository_id == repository.id
            assert stored_obj.repository_dependency_id == repository_dependency.id

    def test_relationships(self, session, cls_, repository, repository_dependency):
        obj = cls_()
        obj.repository = repository
        obj.repository_dependency = repository_dependency

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repository.id == repository.id
            assert stored_obj.repository_dependency.id == repository_dependency.id


class TestRepositoryDependency(BaseTest):

    def test_table(self, cls_):
        assert cls_.table.name == 'repository_dependency'
        # assert cls_.__tablename__ == 'repository_dependency'  # TODO

    def test_columns(self, session, cls_, repository):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.repository = repository

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.tool_shed_repository_id == repository.id

    def test_relationships(self, session, cls_, repository):
        obj = cls_()
        obj.repository = repository

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repository.id == repository.id


class TestToolDependency(BaseTest):

    def test_table(self, cls_):
        assert cls_.table.name == 'tool_dependency'
        # assert cls_.__tablename__ == 'tool_dependency'  # TODO

    def test_columns(self, session, cls_, repository):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        name, version, type, status, error_message = 'a', 'b', 'c', 'd', 'e'
        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.tool_shed_repository_id = repository.id
        obj.name = name
        obj.version = version
        obj.type = type
        obj.status = status
        obj.error_message = error_message

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.tool_shed_repository_id == repository.id
            assert stored_obj.name == name
            assert stored_obj.version == version
            assert stored_obj.type == type
            assert stored_obj.status == status
            assert stored_obj.error_message == error_message

    def test_relationships(self, session, cls_, repository):
        obj = cls_()
        obj.tool_shed_repository = repository
        obj.status = 'a'

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.tool_shed_repository.id == repository.id


class TestToolVersion(BaseTest):

    def test_table(self, cls_):
        assert cls_.table.name == 'tool_version'
        # assert cls_.__tablename__ == 'tool_version'  # TODO

    def test_columns(self, session, cls_, repository):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        tool_id = 'a'
        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.tool_id = tool_id
        obj.tool_shed_repository = repository

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.tool_id == tool_id
            assert stored_obj.tool_shed_repository_id == repository.id

    def test_relationships(self, session, cls_, repository):
        obj = cls_()
        obj.tool_shed_repository = repository
        # TODO
        # parent_tool_association
        # child_tool_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.tool_shed_repository.id == repository.id


class TestToolVersionAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.table.name == 'tool_version_association'
        # assert cls_.__tablename__ == 'tool_version_association'  # TODO

    def test_columns(self, session, cls_, tool_version_factory):
        tool_version = tool_version_factory()
        parent_tool_version = tool_version_factory()

        session.add(tool_version)
        session.add(parent_tool_version)
        session.flush()

        # TODO: why are these not mapped as relationships?
        obj = cls_()
        obj.tool_id = tool_version.id
        obj.parent_id = parent_tool_version.id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.tool_id == tool_version.id
            assert stored_obj.parent_id == parent_tool_version.id


# Misc. helper fixtures.

@pytest.fixture(scope='module')
def model():
    db_uri = 'sqlite:///:memory:'
    return mapping.init(db_uri, create_tables=True)


@pytest.fixture
def session(model):
    Session = model.session
    yield Session()
    Session.remove()  # Ensures we get a new session for each test


# Fixtures yielding persisted instances of models, deleted from the database on test exit.

@pytest.fixture
def repository(model, session):
    instance = model.ToolShedRepository()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def repository_repository_dependency_association(model, session):
    instance = model.RepositoryRepositoryDependencyAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def repository_dependency(model, session, repository):
    instance = model.RepositoryDependency()
    instance.repository = repository
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def tool_dependency(model, session, repository):
    instance = model.ToolDependency()
    instance.tool_shed_repository = repository
    instance.status = 'a'
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def tool_version(model, session):
    instance = model.ToolVersion()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def tool_version_factory(model):
    def make_instance(*args, **kwds):
        return model.ToolVersion(*args, **kwds)
    return make_instance


# Test utilities

def dbcleanup_wrapper(session, obj, where_clause=None):
    with dbcleanup(session, obj, where_clause):
        yield obj


@contextmanager
def dbcleanup(session, obj, where_clause=None):
    """
    Use the session to store obj in database; delete from database on exit, bypassing the session.

    If obj does not have an id field, a SQLAlchemy WHERE clause should be provided to construct
    a custom select statement.
    """
    return_id = where_clause is None

    try:
        obj_id = persist(session, obj, return_id)
        yield obj_id
    finally:
        # table = obj.__table__  # TODO
        table = obj.table
        if where_clause is None:
            where_clause = _get_default_where_clause(type(obj), obj_id)
        stmt = delete(table).where(where_clause)
        session.execute(stmt)


def persist(session, obj, return_id=True):
    """
    Use the session to store obj in database, then remove obj from session,
    so that on a subsequent load from the database we get a clean instance.
    """
    session.add(obj)
    session.flush()
    obj_id = obj.id if return_id else None  # save this before obj is expunged
    session.expunge(obj)
    return obj_id


def get_stored_obj(session, cls, obj_id=None, where_clause=None, unique=False):
    # Either obj_id or where_clause must be provided, but not both
    assert bool(obj_id) ^ (where_clause is not None)
    if where_clause is None:
        where_clause = _get_default_where_clause(cls, obj_id)
    stmt = select(cls).where(where_clause)
    result = session.execute(stmt)
    # unique() is required if result contains joint eager loads against collections
    # https://gerrit.sqlalchemy.org/c/sqlalchemy/sqlalchemy/+/2253
    if unique:
        result = result.unique()
    return result.scalar_one()


def _get_default_where_clause(cls, obj_id):
    # where_clause = cls.__table__.c.id == obj_id  # TODO
    where_clause = cls.table.c.id == obj_id
    return where_clause
