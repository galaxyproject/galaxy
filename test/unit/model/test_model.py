import pytest
from sqlalchemy import (
    delete,
    select,
    UniqueConstraint,
)

import galaxy.model.mapping as mapping


@pytest.fixture(scope='module')
def model():
    db_uri = 'sqlite:///:memory:'
    return mapping.init('/tmp', db_uri, create_tables=True)


@pytest.fixture
def session(model):
    Session = model.session
    yield Session()
    Session.remove()  # Ensures we get a new session for each test


def test_Group_table(model):
    tbl = model.Group.__table__
    assert tbl.name == 'galaxy_group'


def test_Group(model, session):
    name = 'a'
    obj = model.Group(name)
    persist(session, obj)

    stmt = select(model.Group)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.create_time
    assert stored_obj.update_time
    assert stored_obj.name == name
    assert stored_obj.deleted is False

    cleanup(session, model.WorkerProcess)


def test_WorkerProcess_table(model):
    tbl = model.WorkerProcess.__table__
    assert tbl.name == 'worker_process'
    assert has_unique_constraint(tbl, ('server_name', 'hostname'))


def test_WorkerProcess(model, session):
    server_name, hostname = 'a', 'b'
    obj = model.WorkerProcess(server_name, hostname)
    persist(session, obj)

    stmt = select(model.WorkerProcess)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.server_name == server_name
    assert stored_obj.hostname == hostname
    assert stored_obj.pid is None
    assert stored_obj.update_time

    cleanup(session, model.WorkerProcess)


def test_PSAAssociation_table(model):
    tbl = model.PSAAssociation.__table__
    assert tbl.name == 'psa_association'


def test_PSAAssociation(model, session):
    server_url, handle, secret, issued, lifetime, assoc_type = 'a', 'b', 'c', 1, 2, 'd'
    obj = model.PSAAssociation(server_url, handle, secret, issued, lifetime, assoc_type)
    persist(session, obj)

    stmt = select(model.PSAAssociation)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.server_url == server_url
    assert stored_obj.handle == handle
    assert stored_obj.secret == secret
    assert stored_obj.issued == issued
    assert stored_obj.lifetime == lifetime
    assert stored_obj.assoc_type == assoc_type

    cleanup(session, model.PSAAssociation)


def test_PSACode_table(model):
    tbl = model.PSACode.__table__
    assert tbl.name == 'psa_code'
    assert has_unique_constraint(tbl, ('code', 'email'))


def test_PSACode(model, session):
    email, code = 'a', 'b'
    obj = model.PSACode(email, code)
    persist(session, obj)

    stmt = select(model.PSACode)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.email == email
    assert stored_obj.code == code

    cleanup(session, model.PSACode)


def test_PSANonce_table(model):
    tbl = model.PSANonce.__table__
    assert tbl.name == 'psa_nonce'


def test_PSANonce(model, session):
    server_url, timestamp, salt = 'a', 1, 'b'
    obj = model.PSANonce(server_url, timestamp, salt)
    persist(session, obj)

    stmt = select(model.PSANonce)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.server_url
    assert stored_obj.timestamp == timestamp
    assert stored_obj.salt == salt

    cleanup(session, model.PSANonce)


def test_PSAPartial_table(model):
    tbl = model.PSAPartial.__table__
    assert tbl.name == 'psa_partial'


def test_PSAPartial(model, session):
    token, data, next_step, backend = 'a', 'b', 1, 'c'
    obj = model.PSAPartial(token, data, next_step, backend)
    persist(session, obj)

    stmt = select(model.PSAPartial)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.token == token
    assert stored_obj.data == data
    assert stored_obj.next_step == next_step
    assert stored_obj.backend == backend

    cleanup(session, model.PSACode)


def persist(session, obj):
    session.add(obj)
    session.flush()


def cleanup(session, cls):
    session.execute(delete(cls))


def has_unique_constraint(table, fields):
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            col_names = {c.name for c in constraint.columns}
            if set(fields) == col_names:
                return True
