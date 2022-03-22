from abc import (
    ABC,
    abstractmethod,
)
from contextlib import contextmanager
from uuid import uuid4

import pytest
from sqlalchemy import (
    delete,
    select,
    UniqueConstraint,
)


class AbstractBaseTest(ABC):
    @pytest.fixture
    def cls_(self):
        """
        Return class under test.
        Assumptions: if the class under test is Foo, then the class grouping
        the tests should be a subclass of BaseTest, named TestFoo.
        """
        prefix = len("Test")
        class_name = self.__class__.__name__[prefix:]
        return getattr(self.get_model(), class_name)

    @abstractmethod
    def get_model(self):
        pass


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
        table = obj.__table__
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


def delete_from_database(session, objects):
    """
    Delete each object in objects from database.
    May be called at the end of a test if use of a context manager is impractical.
    (Assume all objects have the id field as their primary key.)
    """
    # Ensure we have a list of objects (check for list explicitly: a model can be iterable)
    if not isinstance(objects, list):
        objects = [objects]

    for obj in objects:
        table = obj.__table__
        stmt = delete(table).where(table.c.id == obj.id)
        session.execute(stmt)


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


def has_unique_constraint(table, fields):
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            col_names = {c.name for c in constraint.columns}
            if set(fields) == col_names:
                return True


def has_index(table, fields):
    for index in table.indexes:
        col_names = {c.name for c in index.columns}
        if set(fields) == col_names:
            return True


def collection_consists_of_objects(collection, *objects):
    """
    Returns True iff list(collection) == list(objects), where object equality is determined
    by primary key equality: object1.id == object2.id.
    """
    if len(collection) != len(objects):  # False if lengths are different
        return False
    if not collection:  # True if both are empty
        return True

    # Sort, then compare each member by its 'id' attribute, which must be its primary key.
    collection.sort(key=lambda item: item.id)
    objects_l = list(objects)
    objects_l.sort(key=lambda item: item.id)

    for item1, item2 in zip(collection, objects_l):
        if item1.id is None or item2.id is None or item1.id != item2.id:
            return False
    return True


def get_unique_value():
    """Generate unique values to accommodate unique constraints."""
    return uuid4().hex


def _get_default_where_clause(cls, obj_id):
    where_clause = cls.__table__.c.id == obj_id
    return where_clause
