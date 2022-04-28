"""
This module contains tests for the utility functions in the test_mapping module.
"""

from contextlib import contextmanager

import pytest
from sqlalchemy import (
    Column,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import registry

from galaxy.model import _HasTable
from . import (
    dbcleanup,
    dbcleanup_wrapper,
    delete_from_database,
    get_stored_instance_by_id,
    get_stored_obj,
    initialize_model,
    persist,
)


def test_persist(session):
    """
    Verify item is stored in database.
    We call persist() with default arg value: `return_id=True`. Passing `False` results
    in the same functionality except the return value of the funtion is `None`.
    """
    instance = Foo()
    instance_id = persist(session, instance)  # store instance in database
    assert instance_id == 1  # id was assigned
    assert instance not in session  # instance was expunged from session

    stored_instance = get_stored_instance_by_id(session, Foo, instance_id)
    assert stored_instance.id == instance.id  # instance can be retrieved by id
    assert stored_instance is not instance  # retrieved instance is not the same object


def test_get_stored_obj_must_have_obj_id_xor_where_clause():
    """
    Verify that function must be called with either obj_id or where_clause, but not both.
    """
    with pytest.raises(AssertionError):
        get_stored_obj(None, None, obj_id=1, where_clause="a")
    with pytest.raises(AssertionError):
        get_stored_obj(None, None, obj_id=None, where_clause=None)


def test_get_stored_obj_by_id(session):
    """Verify item is retrieved from database by id."""
    instance = Foo()
    id = persist(session, instance)

    stored_instance = get_stored_obj(session, Foo, id)
    assert stored_instance.id == instance.id


def test_get_stored_obj_by_where_clause(session):
    """Verify item is retrieved from database by a custom WHERE clause."""
    instance1 = Foo()
    instance2 = Foo()
    id1 = persist(session, instance1)
    id2 = persist(session, instance2)

    where_clause = Foo.__table__.c.id == id1
    stored_instance = get_stored_obj(session, Foo, where_clause=where_clause)
    assert stored_instance.id == instance1.id

    where_clause = Foo.__table__.c.id == id2
    stored_instance = get_stored_obj(session, Foo, where_clause=where_clause)
    assert stored_instance.id == instance2.id


def test_delete_from_database_one_item(session):
    """Verify item is deleted from database."""
    instance = Foo()
    id = persist(session, instance)  # store instance in database

    stored_instance = get_stored_instance_by_id(session, Foo, id)
    assert stored_instance is not None  # instance is present in database

    delete_from_database(session, instance)  # delete instance from database

    with pytest.raises(NoResultFound):  # instance no longer present in database
        stored_instance = get_stored_instance_by_id(session, Foo, id)


def test_delete_from_database_multiple_items(session):
    """Verify multiple items are deleted from database."""
    instance1 = Foo()
    instance2 = Foo()
    id1 = persist(session, instance1)
    id2 = persist(session, instance2)

    delete_from_database(session, [instance1, instance2])

    with pytest.raises(NoResultFound):
        get_stored_instance_by_id(session, Foo, id1)
    with pytest.raises(NoResultFound):
        get_stored_instance_by_id(session, Foo, id2)


def test_dbcleanup_by_id(session):
    instance = Foo()
    with dbcleanup(session, instance) as instance_id:
        stored_instance = get_stored_instance_by_id(session, Foo, instance_id)
        assert stored_instance  # has been stored in the database

    with pytest.raises(NoResultFound):  # has been deleted from the database
        get_stored_instance_by_id(session, Foo, instance_id)


def test_dbcleanup_by_where_clause(session):
    instance = Foo()
    where_clause = Foo.__table__.c.id == 1

    with dbcleanup(session, instance, where_clause):
        stored_instance = get_stored_instance_by_id(session, Foo, where_clause)
        assert stored_instance  # has been stored in the database

    with pytest.raises(NoResultFound):  # has been deleted from the database
        get_stored_instance_by_id(session, Foo, stored_instance.id)


def test_dbcleanup_wrapper(session):
    """
    Verify dbcleanup_wrapper has same effect as dbcleanup context manager,
    and yields the object instance.
    """

    @contextmanager  # we need a context manager to similate scope
    def managed(a, b):
        yield from dbcleanup_wrapper(a, b)

    instance = Foo()
    # this will call dbcleanup_wrapper that stores instance in the database and returns a reference to it
    with managed(session, instance) as instance2:
        assert instance2 is instance  # instance2 should be a reference to instance
        stored_instance = get_stored_instance_by_id(session, Foo, instance.id)
        assert stored_instance  # has been stored in the database

    # on exit we expect the entity to be deleted from the database
    with pytest.raises(NoResultFound):  # has been deleted from the database
        get_stored_instance_by_id(session, Foo, instance.id)


# Test utilities

mapper_registry = registry()


@mapper_registry.mapped
class Foo(_HasTable):
    __tablename__ = "foo"
    id = Column(Integer, primary_key=True)
    field1 = Column(Integer)


@mapper_registry.mapped
class Bar(_HasTable):
    __tablename__ = "bar"
    id = Column(Integer, primary_key=True)
    field1 = Column(Integer)
    field2 = Column(Integer)
    __table_args__ = (
        Index("ix", "field1"),
        UniqueConstraint("field2"),
    )


@pytest.fixture(scope="module")
def init_model(engine):
    """Create model objects in the engine's database."""
    # Must use the same engine as the session fixture used by this module.
    initialize_model(mapper_registry, engine)
