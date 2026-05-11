"""Unit tests for the PulsarByocResource model."""

import uuid

import pytest
from sqlalchemy import (
    create_engine,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from galaxy import model
from galaxy.model.unittest_utils.model_testing_utils import persist


@pytest.fixture(scope="module")
def engine():
    return create_engine("sqlite:///:memory:")


@pytest.fixture(scope="module")
def init_model(engine):
    model.mapper_registry.metadata.create_all(engine)


@pytest.fixture
def session(init_model, engine):
    with Session(engine) as s:
        yield s


def _make_user(session):
    suffix = uuid.uuid4().hex[:8]
    user = model.User(
        username=f"byoc_user_{suffix}",
        email=f"byoc_{suffix}@example.test",
        password="password123",
    )
    persist(session, user)
    return user


def test_create_resource_applies_defaults(session):
    user = _make_user(session)
    suffix = uuid.uuid4().hex[:8]
    resource = model.PulsarByocResource(
        user_id=user.id,
        manager_name=f"byoc_{user.id}_{suffix}",
        relay_url="https://relay.example.test",
    )
    persist(session, resource)

    fetched = session.get(model.PulsarByocResource, resource.id)
    assert fetched is not None
    assert fetched.status == "pending"
    assert fetched.create_time is not None
    assert fetched.update_time is not None
    assert fetched.last_seen_time is None
    assert fetched.relay_topic_prefix is None


def test_manager_name_unique(session):
    user = _make_user(session)
    suffix = uuid.uuid4().hex[:8]
    manager_name = f"byoc_{user.id}_{suffix}"
    first = model.PulsarByocResource(
        user_id=user.id,
        manager_name=manager_name,
        relay_url="https://relay.example.test",
    )
    persist(session, first)

    duplicate = model.PulsarByocResource(
        user_id=user.id,
        manager_name=manager_name,
        relay_url="https://relay.example.test",
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_user_can_have_multiple_resources(session):
    """Uniqueness is on manager_name, not on (user_id, status); the API enforces
    'one active per user', not the schema."""
    user = _make_user(session)
    suffix = uuid.uuid4().hex
    r1 = model.PulsarByocResource(
        user_id=user.id,
        manager_name=f"byoc_{user.id}_{suffix[:8]}",
        relay_url="https://relay.example.test",
    )
    r2 = model.PulsarByocResource(
        user_id=user.id,
        manager_name=f"byoc_{user.id}_{suffix[8:16]}",
        relay_url="https://relay.example.test",
    )
    persist(session, r1)
    persist(session, r2)

    rows = session.scalars(select(model.PulsarByocResource).where(model.PulsarByocResource.user_id == user.id)).all()
    assert len(rows) >= 2


def test_status_lifecycle_is_a_plain_string(session):
    """The status column is a free-form string; lifecycle is enforced by the
    manager layer, not the schema."""
    user = _make_user(session)
    suffix = uuid.uuid4().hex[:8]
    resource = model.PulsarByocResource(
        user_id=user.id,
        manager_name=f"byoc_{user.id}_{suffix}",
        relay_url="https://relay.example.test",
        status="active",
    )
    persist(session, resource)

    resource.status = "disabled"
    persist(session, resource)
    assert session.get(model.PulsarByocResource, resource.id).status == "disabled"
