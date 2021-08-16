"""
This module contains tests for the utility functions in the test_mapping module.
"""

import pytest
from sqlalchemy import Column, create_engine, Integer, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import registry, Session

from . test_mapping import (
    delete_from_database,
    get_stored_obj,
    persist,
)


mapper_registry = registry()


@mapper_registry.mapped
class Foo:
    __tablename__ = 'foo'
    id = Column(Integer, primary_key=True)


@pytest.fixture(scope='module')
def engine():
    """Create connection engine. (Fixture is module-scoped)."""
    db_uri = 'sqlite:///:memory:'  # We only need sqlite for these tests
    return create_engine(db_uri)


@pytest.fixture(scope='module')
def init(engine):
    """Create database objects. (Fixture is module-scoped)."""
    mapper_registry.metadata.create_all(engine)


@pytest.fixture
def session(init, engine):
    """Provides a basic session object, closed on exit."""
    with Session(engine) as s:
        yield s


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

    stored_instance = _get_stored_instance_by_id(session, Foo, instance_id)
    assert stored_instance.id == instance.id  # instance can be retrieved by id
    assert stored_instance is not instance  # retrieved instance is not the same object


def test_delete_from_database_one_item(session):
    """Verify item is deleted from database."""
    instance = Foo()
    id = persist(session, instance)  # store instance in database

    stored_instance = _get_stored_instance_by_id(session, Foo, id)
    assert stored_instance is not None  # instance is present in database

    delete_from_database(session, instance)  # delete instance from database

    with pytest.raises(NoResultFound):  # instance no longer present in database
        stored_instance = _get_stored_instance_by_id(session, Foo, id)


def test_delete_from_database_multiple_items(session):
    """Verify multiple items are deleted from database."""
    instance1 = Foo()
    instance2 = Foo()
    id1 = persist(session, instance1)
    id2 = persist(session, instance2)

    delete_from_database(session, [instance1, instance2])

    with pytest.raises(NoResultFound):
        _get_stored_instance_by_id(session, Foo, id1)
    with pytest.raises(NoResultFound):
        _get_stored_instance_by_id(session, Foo, id2)


def test_get_stored_obj_must_have_obj_id_xor_where_clause():
    """
    Verify that function must be called with either obj_id or where_clause, but not both.
    """
    with pytest.raises(AssertionError):
        get_stored_obj(None, None, obj_id=1, where_clause='a')
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


def _get_stored_instance_by_id(session, cls_, id):
    statement = select(Foo).where(cls_.__table__.c.id == id)
    return session.execute(statement).scalar_one()
