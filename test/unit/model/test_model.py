import pytest
from sqlalchemy import (
    delete,
    select,
)

import galaxy.model.mapping as mapping


@pytest.fixture(scope='module')
def model():
    db_uri = 'sqlite:///:memory:'
    return mapping.init('/tmp', db_uri, create_tables=True)


@pytest.fixture
def session(model, request):
    Session = model.session
    yield Session()
    Session.remove()  # Ensures we get a new session for each test


def test_workerprocess(model, session):
    server_name, hostname = 'a', 'b'
    wp = model.WorkerProcess(server_name, hostname)
    persist(session, wp)

    stmt = select(model.WorkerProcess)
    stored_wp = session.execute(stmt).scalar_one()
    assert stored_wp.id
    assert stored_wp.server_name == server_name
    assert stored_wp.hostname == hostname
    assert stored_wp.pid is None
    assert stored_wp.update_time

    cleanup(session, model.WorkerProcess)


def persist(session, obj):
    session.add(obj)
    session.flush()


def cleanup(session, cls):
    session.execute(delete(cls))
