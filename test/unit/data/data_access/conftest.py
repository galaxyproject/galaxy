import contextlib
import random
import string

import pytest
from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.orm import Session

from galaxy import model as m
from galaxy.datatypes.registry import Registry as DatatypesRegistry
from . import MockObjectStore

# utility fixtures


@contextlib.contextmanager
def transaction(session):
    if not session.in_transaction():
        with session.begin():
            yield
    else:
        yield


@pytest.fixture(scope="module")
def engine():
    db_uri = "sqlite:///:memory:"
    return create_engine(db_uri)


@pytest.fixture(autouse=True, scope="module")
def setup(engine):
    m.mapper_registry.metadata.create_all(engine)
    m.Dataset.object_store = MockObjectStore()  # type:ignore[assignment]
    datatypes_registry = DatatypesRegistry()
    datatypes_registry.load_datatypes()
    m.set_datatypes_registry(datatypes_registry)
    print("\nSETUP CALLED")


@pytest.fixture(autouse=True)
def teardown(engine):
    """Delete all rows from all tables. Called after each test."""
    yield
    with engine.begin() as conn:
        for table in m.mapper_registry.metadata.tables:
            stmt = text(f"DELETE FROM {table}")
            conn.execute(stmt)


@pytest.fixture
def session(engine):
    engine = engine
    return Session(engine)


@pytest.fixture
def make_random_users(session, make_user):
    def f(count):
        return [make_user() for _ in range(count)]

    return f


# utility functions


def random_str():
    alphabet = string.ascii_lowercase + string.digits
    size = random.randint(5, 10)
    return "".join(random.choices(alphabet, k=size))


def random_email():
    text = random_str()
    return f"{text}@galaxy.testing"


# model fixture factories


@pytest.fixture
def make_dataset_collection(session):
    def f(**kwd):
        dc = m.DatasetCollection(**kwd)
        with transaction(session):
            session.add(dc)
            session.commit()
        return dc

    return f


@pytest.fixture
def make_dataset_collection_element(session, make_hda):
    def f(**kwd):
        if "element" not in kwd:
            kwd["element"] = make_hda()
        dce = m.DatasetCollectionElement(**kwd)
        with transaction(session):
            session.add(dce)
            session.commit()
        return dce

    return f


@pytest.fixture
def make_dataset_permissions(session):
    def f(**kwd):
        dp = m.DatasetPermissions(**kwd)
        with transaction(session):
            session.add(dp)
            session.commit()
        return dp

    return f


@pytest.fixture
def make_history(session, make_user):
    def f(**kwd):
        if "user" not in kwd:
            kwd["user"] = make_user()
        history = m.History(**kwd)
        with transaction(session):
            session.add(history)
            session.commit()
        return history

    return f


@pytest.fixture
def make_hda(session, make_history):
    def f(**kwd):
        if "history" not in kwd:
            kwd["history"] = make_history()
        hda = m.HistoryDatasetAssociation(**kwd)
        with transaction(session):
            session.add(hda)
            session.commit()
        return hda

    return f


@pytest.fixture
def make_hdca(session):
    def f(**kwd):
        hdca = m.HistoryDatasetCollectionAssociation(**kwd)
        with transaction(session):
            session.add(hdca)
            session.commit()
        return hdca

    return f


@pytest.fixture
def make_ldca(session):
    def f(**kwd):
        ldca = m.LibraryDatasetCollectionAssociation(**kwd)
        with transaction(session):
            session.add(ldca)
            session.commit()
        return ldca

    return f


@pytest.fixture
def make_library(session):
    def f(**kwd):
        lib = m.Library(**kwd)
        with transaction(session):
            session.add(lib)
            session.commit()
        return lib

    return f


@pytest.fixture
def make_library_folder(session):
    def f(**kwd):
        lib_folder = m.LibraryFolder(**kwd)
        with transaction(session):
            session.add(lib_folder)
            session.commit()
        return lib_folder

    return f


@pytest.fixture
def make_library_permissions(session, make_library, make_role):
    def f(**kwd):
        action = kwd.get("action") or random_str()
        library = kwd.get("library") or make_library()
        role = kwd.get("role") or make_role()
        lp = m.LibraryPermissions(action, library, role)
        with transaction(session):
            session.add(lp)
            session.commit()
        return lp

    return f


@pytest.fixture
def make_page(session, make_user):
    def f(**kwd):
        if "user" not in kwd:
            kwd["user"] = make_user()
        page = m.Page(**kwd)
        with transaction(session):
            session.add(page)
            session.commit()
        return page

    return f


@pytest.fixture
def make_role(session):
    def f(**kwd):
        role = m.Role(**kwd)
        with transaction(session):
            session.add(role)
            session.commit()
        return role

    return f


@pytest.fixture
def make_stored_workflow(session, make_user):
    def f(**kwd):
        if "user" not in kwd:
            kwd["user"] = make_user()
        sw = m.StoredWorkflow(**kwd)
        with transaction(session):
            session.add(sw)
            session.commit()
        return sw

    return f


@pytest.fixture
def make_user(session):
    def f(**kwd):
        if "username" not in kwd:
            kwd["username"] = random_email()
        if "email" not in kwd:
            kwd["email"] = random_email()
        if "password" not in kwd:
            kwd["password"] = random_str()
        user = m.User(**kwd)
        with transaction(session):
            session.add(user)
            session.commit()
        return user

    return f


@pytest.fixture
def make_user_item_rating_association(session):
    def f(assoc_class, user, item, rating):
        assoc = assoc_class(user, item, rating)
        with transaction(session):
            session.add(assoc)
            session.commit()
        return assoc

    return f


@pytest.fixture
def make_user_role_association(session):
    def f(user, role):
        assoc = m.UserRoleAssociation(user, role)
        with transaction(session):
            session.add(assoc)
            session.commit()
        return assoc

    return f


@pytest.fixture
def make_visualization(session, make_user):
    def f(**kwd):
        if "user" not in kwd:
            kwd["user"] = make_user()
        vis = m.Visualization(**kwd)
        with transaction(session):
            session.add(vis)
            session.commit()
        return vis

    return f
