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

# utility fixtures


@contextlib.contextmanager
def transaction(session):
    if not session.in_transaction():
        with session.begin():
            yield
    else:
        yield


@pytest.fixture(scope="module")
def db_url():
    # for postgresql user must have prigileges to execute stmt in teardown()
    return "sqlite:///:memory:"  # TODO make configurable


@pytest.fixture(scope="module")
def engine(db_url):
    return create_engine(db_url)


@pytest.fixture(autouse=True, scope="module")
def setup(engine):
    m.mapper_registry.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def teardown(engine):
    """Delete all rows from all tables. Called after each test."""
    yield
    with engine.begin() as conn:
        for table in m.mapper_registry.metadata.tables:
            stmt = text(f"ALTER TABLE {table} DISABLE TRIGGER ALL")  # disable fkey constraints to delete out of order
            conn.execute(stmt)
            stmt = text(f"DELETE FROM {table}")
            conn.execute(stmt)


@pytest.fixture
def session(engine):
    engine = engine
    return Session(engine)


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
def make_event(session):
    def f(**kwd):
        model = m.Event(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_galaxy_session(session):
    def f(**kwd):
        model = m.GalaxySession(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_history(session, make_user):
    def f(**kwd):
        if "user" not in kwd:
            kwd["user"] = make_user()
        model = m.History(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_history_annotation_association(session):
    def f(**kwd):
        model = m.HistoryAnnotationAssociation(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_history_tag_association(session):
    def f(**kwd):
        model = m.HistoryTagAssociation(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_job(session):
    def f(**kwd):
        model = m.Job(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_role(session):
    def f(**kwd):
        model = m.Role(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_user(session):
    def f(**kwd):
        if "username" not in kwd:
            kwd["username"] = random_str()
        if "email" not in kwd:
            kwd["email"] = random_email()
        if "password" not in kwd:
            kwd["password"] = random_str()
        model = m.User(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_history_rating_association(session, make_user, make_history):
    def f(**kwd):
        if "user" not in kwd:
            kwd["user"] = make_user()
        if "item" not in kwd:
            kwd["item"] = make_history()
        model = m.HistoryRatingAssociation(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_history_user_share_association(session):
    def f(**kwd):
        model = m.HistoryUserShareAssociation(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_default_history_permissions(session, make_history, make_role):
    def f(**kwd):
        if "history" not in kwd:
            kwd["history"] = make_history()
        if "action" not in kwd:
            kwd["action"] = random_str()
        if "role" not in kwd:
            kwd["role"] = make_role()
        model = m.DefaultHistoryPermissions(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_data_manager_history_association(session):
    def f(**kwd):
        model = m.DataManagerHistoryAssociation(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_cleanup_event_history_association(session):
    def f(**kwd):
        model = m.CleanupEventHistoryAssociation(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_galaxy_session_to_history_association(session, make_history, make_galaxy_session):
    def f(**kwd):
        if "galaxy_session" not in kwd:
            kwd["galaxy_session"] = make_galaxy_session()
        if "history" not in kwd:
            kwd["history"] = make_history()
        model = m.GalaxySessionToHistoryAssociation(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_job_import_history_archive(session):
    def f(**kwd):
        model = m.JobImportHistoryArchive(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_job_export_history_archive(session):
    def f(**kwd):
        model = m.JobExportHistoryArchive(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_workflow(session):
    def f(**kwd):
        model = m.Workflow(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_workflow_invocation(session, make_workflow):
    def f(**kwd):
        if "workflow" not in kwd:
            kwd["workflow"] = make_workflow()
        model = m.WorkflowInvocation(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_history_dataset_collection_association(session):
    def f(**kwd):
        model = m.HistoryDatasetCollectionAssociation(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f


@pytest.fixture
def make_history_dataset_association(session):
    def f(**kwd):
        model = m.HistoryDatasetAssociation(**kwd)
        with transaction(session):
            session.add(model)
            session.commit()
        return model

    return f
