import random
from contextlib import contextmanager
from datetime import datetime

import pytest
from sqlalchemy import (
    delete,
    select,
    UniqueConstraint,
)

import galaxy.model.mapping as mapping


def test_CloudAuthz(model, session, user, user_authnz_token):
    cls = model.CloudAuthz
    assert cls.__tablename__ == 'cloudauthz'
    with dbcleanup(session, cls):
        provider, config, description = 'a', 'b', 'c'
        obj = cls(user.id, provider, config, user_authnz_token.id, description)
        obj.user = user
        obj.authn = user_authnz_token
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.user_id == user.id
        assert stored_obj.provider == provider
        assert stored_obj.config == config
        assert stored_obj.authn_id == user_authnz_token.id
        assert stored_obj.description == description
        assert stored_obj.tokens is None
        assert stored_obj.last_update
        assert stored_obj.last_activity
        assert stored_obj.create_time
        assert stored_obj.user == user
        assert stored_obj.authn == user_authnz_token


def test_CustosAuthnzToken(model, session, user):
    cls = model.CustosAuthnzToken
    assert cls.__tablename__ == 'custos_authnz_token'
    assert has_unique_constraint(cls.__table__, ('user_id', 'external_user_id', 'provider'))
    assert has_unique_constraint(cls.__table__, ('external_user_id', 'provider'))
    with dbcleanup(session, cls):
        external_user_id = get_random_string()
        provider = get_random_string()
        access_token = 'c'
        id_token = 'd'
        refresh_token = 'e'
        expiration_time = datetime.now()
        refresh_expiration_time = datetime.now()
        obj = cls(user, external_user_id, provider, access_token, id_token, refresh_token,
            expiration_time, refresh_expiration_time)
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.external_user_id == external_user_id
        assert stored_obj.provider == provider
        assert stored_obj.access_token == access_token
        assert stored_obj.id_token == id_token
        assert stored_obj.refresh_token == refresh_token
        assert stored_obj.expiration_time == expiration_time
        assert stored_obj.refresh_expiration_time == refresh_expiration_time
        assert stored_obj.user == user


def test_PageRevision(model, session, page):
    cls = model.PageRevision
    assert cls.__tablename__ == 'page_revision'
    with dbcleanup(session, cls):
        obj = cls()
        obj.page = page
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.create_time
        assert stored_obj.update_time
        assert stored_obj.page_id
        assert stored_obj.title is None
        assert stored_obj.content is None
        assert stored_obj.content_format == model.PageRevision.DEFAULT_CONTENT_FORMAT


def test_PSAAssociation(model, session):
    cls = model.PSAAssociation
    assert cls.__tablename__ == 'psa_association'
    with dbcleanup(session, cls):
        server_url, handle, secret, issued, lifetime, assoc_type = 'a', 'b', 'c', 1, 2, 'd'
        obj = cls(server_url, handle, secret, issued, lifetime, assoc_type)
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.server_url == server_url
        assert stored_obj.handle == handle
        assert stored_obj.secret == secret
        assert stored_obj.issued == issued
        assert stored_obj.lifetime == lifetime
        assert stored_obj.assoc_type == assoc_type


def test_PSACode(model, session):
    cls = model.PSACode
    assert cls.__tablename__ == 'psa_code'
    assert has_unique_constraint(cls.__table__, ('code', 'email'))
    with dbcleanup(session, cls):
        email, code = 'a', get_random_string()
        obj = cls(email, code)
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.email == email
        assert stored_obj.code == code


def test_PSANonce(model, session):
    cls = model.PSANonce
    assert cls.__tablename__ == 'psa_nonce'
    with dbcleanup(session, cls):
        server_url, timestamp, salt = 'a', 1, 'b'
        obj = cls(server_url, timestamp, salt)
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.server_url
        assert stored_obj.timestamp == timestamp
        assert stored_obj.salt == salt


def test_PSAPartial(model, session):
    cls = model.PSAPartial
    assert cls.__tablename__ == 'psa_partial'
    with dbcleanup(session, cls):
        token, data, next_step, backend = 'a', 'b', 1, 'c'
        obj = cls(token, data, next_step, backend)
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.token == token
        assert stored_obj.data == data
        assert stored_obj.next_step == next_step
        assert stored_obj.backend == backend


def test_Quota(model, session):
    cls = model.Quota
    assert cls.__tablename__ == 'quota'
    with dbcleanup(session, cls):
        name, description = get_random_string(), 'b'
        obj = cls(name, description)
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.create_time
        assert stored_obj.update_time
        assert stored_obj.name == name
        assert stored_obj.description == description
        assert stored_obj.bytes == 0
        assert stored_obj.operation == '='
        assert stored_obj.deleted is False


def test_Role(model, session):
    cls = model.Role
    assert cls.__tablename__ == 'role'
    with dbcleanup(session, cls):
        name, description = get_random_string(), 'b'
        obj = cls(name, description)
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.create_time
        assert stored_obj.update_time
        assert stored_obj.name == name
        assert stored_obj.description == description
        assert stored_obj.type == model.Role.types.SYSTEM
        assert stored_obj.deleted is False


def testUserAction(model, session, user, galaxy_session):
    cls = model.UserAction
    assert cls.__tablename__ == 'user_action'
    with dbcleanup(session, cls):
        action, params, context = 'a', 'b', 'c'
        obj = cls(user, galaxy_session.id, action, params, context)
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.create_time
        assert stored_obj.user_id == user.id
        assert stored_obj.session_id == galaxy_session.id
        assert stored_obj.action == action
        assert stored_obj.context == context
        assert stored_obj.params == params
        assert stored_obj.user == user


def test_UserAddress(model, session, user):
    cls = model.UserAddress
    assert cls.__tablename__ == 'user_address'
    with dbcleanup(session, cls):
        desc, name, institution, address, city, state, postal_code, country, phone = \
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'
        obj = cls(user, desc, name, institution, address, city, state, postal_code, country, phone)
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
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


def test_UserAuthnzToken(model, session, user, cloud_authz):
    cls = model.UserAuthnzToken
    assert cls.__tablename__ == 'oidc_user_authnz_tokens'
    assert has_unique_constraint(cls.__table__, ('provider', 'uid'))
    with dbcleanup(session, cls):
        provider, uid, extra_data, lifetime, assoc_type = get_random_string(), 'b', 'c', 1, 'd'
        obj = cls(provider, uid, extra_data, lifetime, assoc_type, user)
        obj.cloudauthz.append(cloud_authz)
        obj.user = user
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.user_id == user.id
        assert stored_obj.uid == uid
        assert stored_obj.provider == provider
        assert stored_obj.extra_data == extra_data
        assert stored_obj.lifetime == lifetime
        assert stored_obj.assoc_type == assoc_type
        assert stored_obj.user == user
        assert cloud_authz in stored_obj.cloudauthz


def test_VisualizationRevision(model, session, visualization):
    cls = model.VisualizationRevision
    assert cls.__tablename__ == 'visualization_revision'
    assert has_index(cls.__table__, ('dbkey',))
    with dbcleanup(session, cls):
        obj = cls()
        obj.visualization = visualization
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.create_time
        assert stored_obj.update_time
        assert stored_obj.visualization_id
        assert stored_obj.title is None
        assert stored_obj.dbkey is None
        assert stored_obj.config is None


def test_WorkerProcess(model, session):
    cls = model.WorkerProcess
    assert cls.__tablename__ == 'worker_process'
    assert has_unique_constraint(cls.__table__, ('server_name', 'hostname'))
    with dbcleanup(session, cls):
        server_name, hostname = get_random_string(), 'a'
        obj = cls(server_name, hostname)
        obj_id = persist(session, obj)

        stmt = select(cls).filter(cls.id == obj_id)
        stored_obj = session.execute(stmt).scalar_one()
        assert stored_obj.id == obj_id
        assert stored_obj.server_name == server_name
        assert stored_obj.hostname == hostname
        assert stored_obj.pid is None
        assert stored_obj.update_time


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
def cloud_authz(model, session, user, user_authnz_token):
    ca = model.CloudAuthz(user.id, 'a', 'b', user_authnz_token.id, 'c')
    yield from dbcleanup_wrapper(session, ca)


@pytest.fixture
def galaxy_session(model, session, user):
    s = model.GalaxySession()
    yield from dbcleanup_wrapper(session, s)


@pytest.fixture
def page(model, session, user):
    p = model.Page()
    p.user = user
    yield from dbcleanup_wrapper(session, p)


@pytest.fixture
def user(model, session):
    u = model.User(email='test@example.com', password='password')
    yield from dbcleanup_wrapper(session, u)


@pytest.fixture
def user_authnz_token(model, session, user):
    t = model.UserAuthnzToken('a', 'b', 'c', 1, 'd', user)
    yield from dbcleanup_wrapper(session, t)


@pytest.fixture
def visualization(model, session, user):
    v = model.Visualization()
    v.user = user
    yield from dbcleanup_wrapper(session, v)


@contextmanager
def dbcleanup(session, cls):
    """
    Ensure all records of cls are deleted from the database on exit.
    """
    try:
        yield
    finally:
        session.execute(delete(cls))


def dbcleanup_wrapper(session, obj):
    with dbcleanup(session, type(obj)):
        yield obj


def persist(session, obj):
    session.add(obj)
    session.flush()
    obj_id = obj.id
    # Remove from session, so that on a subsequent load we get a *new* obj from the db
    session.expunge(obj)
    return obj_id


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


def get_random_string():
    """Generate unique values to accommodate unique constraints."""
    return str(random.random())
