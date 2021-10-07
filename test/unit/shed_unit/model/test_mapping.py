from contextlib import contextmanager
from uuid import uuid4

import pytest
from sqlalchemy import (
    delete,
    select,
    UniqueConstraint,
)

import tool_shed.webapp.model.mapping as mapping


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


class TestUser(BaseTest):
    pass  # TODO


class TestPasswordResetToken(BaseTest):
    pass  # TODO


class TestAPIKeys(BaseTest):
    pass  # TODO


class TestGroup(BaseTest):
    pass  # TODO


class TestRole(BaseTest):
    pass  # TODO


class TestRepositoryRoleAssociation(BaseTest):
    pass  # TODO


class TestUserGroupAssociation(BaseTest):
    pass  # TODO


class TestUserRoleAssociation(BaseTest):
    pass  # TODO


class TestGroupRoleAssociation(BaseTest):
    pass  # TODO


class TestGalaxySession(BaseTest):
    pass  # TODO


class TestTag(BaseTest):
    pass  # TODO


class TestCategory(BaseTest):
    pass  # TODO


class TestRepository(BaseTest):
    pass  # TODO


class TestRepositoryMetadata(BaseTest):
    pass  # TODO


class TestRepositoryReview(BaseTest):
    pass  # TODO


class TestComponentReview(BaseTest):
    pass  # TODO


class TestComponent(BaseTest):
    pass  # TODO


class TestRepositoryRatingAssociation(BaseTest):
    pass  # TODO


class TestRepositoryCategoryAssociation(BaseTest):
    pass  # TODO


# Misc. helper fixtures.

@pytest.fixture(scope='module')
def model():
    db_uri = 'sqlite:///:memory:'
    return mapping.init('/tmp', db_uri, create_tables=True)


@pytest.fixture
def session(model):
    Session = model.session
    yield Session()
    Session.remove()  # Ensures we get a new session for each test


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
    where_clause = cls.table.c.id == obj_id
    return where_clause


def has_unique_constraint(table, fields):
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            col_names = {c.name for c in constraint.columns}
            if set(fields) == col_names:
                return True


def get_unique_value():
    """Generate unique values to accommodate unique constraints."""
    return uuid4().hex
