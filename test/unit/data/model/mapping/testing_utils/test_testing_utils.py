"""
This module contains tests for the utility functions in the test_mapping module.
"""
import pytest
from sqlalchemy import (
    Column,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import registry

from galaxy.model import _HasTable
from . import (
    collection_consists_of_objects,
    has_index,
    has_unique_constraint,
)
from ...testing_utils import (
    get_stored_instance_by_id,
    initialize_model,
    persist,
)


def test_has_index(session):
    assert has_index(Bar.__table__, ("field1",))
    assert not has_index(Foo.__table__, ("field1",))


def test_has_unique_constraint(session):
    assert has_unique_constraint(Bar.__table__, ("field2",))
    assert not has_unique_constraint(Foo.__table__, ("field1",))


def test_collection_consists_of_objects(session):
    # create objects
    foo1 = Foo()
    foo2 = Foo()
    foo3 = Foo()
    # store objects
    persist(session, foo1)
    persist(session, foo2)
    persist(session, foo3)

    # retrieve objects from storage
    stored_foo1 = get_stored_instance_by_id(session, Foo, foo1.id)
    stored_foo2 = get_stored_instance_by_id(session, Foo, foo2.id)
    stored_foo3 = get_stored_instance_by_id(session, Foo, foo3.id)

    # verify retrieved objects are not the same python objects as those we stored
    assert stored_foo1 is not foo1
    assert stored_foo2 is not foo2
    assert stored_foo3 is not foo3

    # trivial case
    assert collection_consists_of_objects([stored_foo1, stored_foo2], foo1, foo2)
    # empty collection and no objects
    assert collection_consists_of_objects([])
    # ordering in collection does not matter
    assert collection_consists_of_objects([stored_foo2, stored_foo1], foo1, foo2)
    # contains wrong object
    assert not collection_consists_of_objects([stored_foo1, stored_foo3], foo1, foo2)
    # contains wrong number of objects
    assert not collection_consists_of_objects([stored_foo1, stored_foo1, stored_foo2], foo1, foo2)
    # if an object's primary key is not set, it cannot be equal to another object
    foo1.id, stored_foo1.id = None, None
    assert not collection_consists_of_objects([stored_foo1], foo1)


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
