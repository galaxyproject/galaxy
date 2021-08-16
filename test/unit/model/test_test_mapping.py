"""
This module contains tests for the utility functions in the test_mapping module.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

import galaxy.model.mapping as mapping
from . test_mapping import (
    delete_from_database,
    persist,
)


@pytest.fixture(scope='module')
def model():
    db_uri = 'sqlite:///:memory:'
    return mapping.init('/tmp', db_uri, create_tables=True)


@pytest.fixture
def session(model):
    Session = model.session
    yield Session()
    Session.remove()  # Ensures we get a new session for each test


def test_persist(session, model):
    """
    Verify item is stored in database.
    We call persist() with default arg value: `return_id=True`. Passing `False` results
    in the same functionality except the return value of the funtion is `None`.
    """
    cls_ = model.CleanupEvent
    instance = cls_()
    instance_id = persist(session, instance)  # store instance in database
    assert instance_id == 1  # id was assigned
    assert instance not in session  # instance was expunged from session

    stored_instance = _get_stored_instance_by_id(session, cls_, instance_id)
    assert stored_instance.id == instance.id  # instance can be retrieved by id
    assert stored_instance is not instance  # retrieved instance is not the same object


def test_delete_from_database_one_item(session, model):
    """Verify item is deleted from database."""
    cls_ = model.CleanupEvent
    instance = cls_()
    id = persist(session, instance)  # store instance in database

    stored_instance = _get_stored_instance_by_id(session, cls_, id)
    assert stored_instance is not None  # instance is present in database

    delete_from_database(session, instance)  # delete instance from database

    with pytest.raises(NoResultFound):  # instance no longer present in database
        stored_instance = _get_stored_instance_by_id(session, cls_, id)


def test_delete_from_database_multiple_items(session, model):
    """Verify multiple items are deleted from database."""
    cls_ = model.CleanupEvent
    instance1 = cls_()
    instance2 = cls_()
    id1 = persist(session, instance1)
    id2 = persist(session, instance2)

    delete_from_database(session, [instance1, instance2])

    with pytest.raises(NoResultFound):
        _get_stored_instance_by_id(session, cls_, id1)
    with pytest.raises(NoResultFound):
        _get_stored_instance_by_id(session, cls_, id2)


def _get_stored_instance_by_id(session, cls_, id):
    statement = select(cls_).where(cls_.__table__.c.id == id)
    return session.execute(statement).scalar_one()
