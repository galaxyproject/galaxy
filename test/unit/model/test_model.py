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


@pytest.fixture
def user(model):
    return model.User(email='test@example.com', password='password')


@pytest.fixture
def page(model, user):
    p = model.Page()
    p.user = user
    return p


@pytest.fixture
def visualization(model, user):
    v = model.Visualization()
    v.user = user
    return v


def test_Group_table(model):
    tbl = model.Group.__table__
    assert tbl.name == 'galaxy_group'


def test_Group(model, session):
    cls = model.Group
    name = 'a'
    obj = cls(name)
    persist(session, obj)

    stmt = select(cls)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.create_time
    assert stored_obj.update_time
    assert stored_obj.name == name
    assert stored_obj.deleted is False

    cleanup(session, cls)


def test_PageRevision_table(model):
    tbl = model.PageRevision.__table__
    assert tbl.name == 'page_revision'


def test_PageRevision(model, session, page):
    cls = model.PageRevision
    obj = cls()
    obj.page = page
    persist(session, obj)

    stmt = select(cls)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.create_time
    assert stored_obj.update_time
    assert stored_obj.page_id
    assert stored_obj.title is None
    assert stored_obj.content is None
    assert stored_obj.content_format == model.PageRevision.DEFAULT_CONTENT_FORMAT

    cleanup(session, cls)


def test_Quota_table(model):
    tbl = model.Quota.__table__
    assert tbl.name == 'quota'


def test_Quota(model, session):
    cls = model.Quota
    name, description = 'a', 'b'
    obj = cls(name, description)
    persist(session, obj)

    stmt = select(cls)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.create_time
    assert stored_obj.update_time
    assert stored_obj.name == name
    assert stored_obj.description == description
    assert stored_obj.bytes == 0
    assert stored_obj.operation == '='
    assert stored_obj.deleted is False

    cleanup(session, cls)


def test_Role_table(model):
    tbl = model.Role.__table__
    assert tbl.name == 'role'


def test_Role(model, session):
    cls = model.Role
    name, description = 'a', 'b'
    obj = cls(name, description)
    persist(session, obj)

    stmt = select(cls)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.create_time
    assert stored_obj.update_time
    assert stored_obj.name == name
    assert stored_obj.description == description
    assert stored_obj.type == model.Role.types.SYSTEM
    assert stored_obj.deleted is False

    cleanup(session, cls)


def test_WorkerProcess_table(model):
    tbl = model.WorkerProcess.__table__
    assert tbl.name == 'worker_process'
    assert has_unique_constraint(tbl, ('server_name', 'hostname'))


def test_WorkerProcess(model, session):
    cls = model.WorkerProcess
    server_name, hostname = 'a', 'b'
    obj = cls(server_name, hostname)
    persist(session, obj)

    stmt = select(cls)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.server_name == server_name
    assert stored_obj.hostname == hostname
    assert stored_obj.pid is None
    assert stored_obj.update_time

    cleanup(session, cls)


def test_PSAAssociation_table(model):
    tbl = model.PSAAssociation.__table__
    assert tbl.name == 'psa_association'


def test_PSAAssociation(model, session):
    cls = model.PSAAssociation
    server_url, handle, secret, issued, lifetime, assoc_type = 'a', 'b', 'c', 1, 2, 'd'
    obj = cls(server_url, handle, secret, issued, lifetime, assoc_type)
    persist(session, obj)

    stmt = select(cls)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.server_url == server_url
    assert stored_obj.handle == handle
    assert stored_obj.secret == secret
    assert stored_obj.issued == issued
    assert stored_obj.lifetime == lifetime
    assert stored_obj.assoc_type == assoc_type

    cleanup(session, cls)


def test_PSACode_table(model):
    tbl = model.PSACode.__table__
    assert tbl.name == 'psa_code'
    assert has_unique_constraint(tbl, ('code', 'email'))


def test_PSACode(model, session):
    cls = model.PSACode
    email, code = 'a', 'b'
    obj = cls(email, code)
    persist(session, obj)

    stmt = select(cls)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.email == email
    assert stored_obj.code == code

    cleanup(session, cls)


def test_PSANonce_table(model):
    tbl = model.PSANonce.__table__
    assert tbl.name == 'psa_nonce'


def test_PSANonce(model, session):
    cls = model.PSANonce
    server_url, timestamp, salt = 'a', 1, 'b'
    obj = cls(server_url, timestamp, salt)
    persist(session, obj)

    stmt = select(cls)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.server_url
    assert stored_obj.timestamp == timestamp
    assert stored_obj.salt == salt

    cleanup(session, cls)


def test_PSAPartial_table(model):
    tbl = model.PSAPartial.__table__
    assert tbl.name == 'psa_partial'


def test_PSAPartial(model, session):
    cls = model.PSAPartial
    token, data, next_step, backend = 'a', 'b', 1, 'c'
    obj = cls(token, data, next_step, backend)
    persist(session, obj)

    stmt = select(cls)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.token == token
    assert stored_obj.data == data
    assert stored_obj.next_step == next_step
    assert stored_obj.backend == backend

    cleanup(session, cls)


def test_UserAddress_table(model):
    tbl = model.UserAddress.__table__
    assert tbl.name == 'user_address'


def test_UserAddress(model, session, user):
    cls = model.UserAddress
    desc, name, institution, address, city, state, postal_code, country, phone = \
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'
    obj = cls(user, desc, name, institution, address, city, state, postal_code, country, phone)
    persist(session, obj)

    stmt = select(cls)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.create_time
    assert stored_obj.update_time
    assert stored_obj.user_id == user.id
    assert stored_obj.desc == desc
    assert stored_obj.name == name
    assert stored_obj.institution == institution
    assert stored_obj.address == address
    assert stored_obj.city == city
    assert stored_obj.state == state
    assert stored_obj.postal_code == postal_code
    assert stored_obj.country == country
    assert stored_obj.phone == phone
    assert stored_obj.deleted is False
    assert stored_obj.purged is False
    assert stored_obj.user == user

    cleanup(session, cls)


def test_VisualizationRevision_table(model):
    tbl = model.VisualizationRevision.__table__
    assert tbl.name == 'visualization_revision'
    assert has_index(tbl, ('dbkey',))


def test_VisualizationRevision(model, session, visualization):
    cls = model.VisualizationRevision
    obj = cls()
    obj.visualization = visualization
    persist(session, obj)

    stmt = select(cls)
    stored_obj = session.execute(stmt).scalar_one()
    assert stored_obj.id
    assert stored_obj.create_time
    assert stored_obj.update_time
    assert stored_obj.visualization_id
    assert stored_obj.title is None
    assert stored_obj.dbkey is None
    assert stored_obj.config is None

    cleanup(session, cls)


def persist(session, obj):
    session.add(obj)
    session.flush()
    # Remove from session, so that on a subsequent load we get a *new* obj from the db
    session.expunge(obj)


def cleanup(session, cls):
    session.execute(delete(cls))


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
