import contextlib
import os
import random
import string
import tempfile
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from galaxy import model as m


@pytest.fixture
def database_name():
    return f"galaxytest_{uuid.uuid4().hex}"


@pytest.fixture
def postgres_url():
    return os.environ.get("GALAXY_TEST_CONNECT_POSTGRES_URI")


@pytest.fixture
def mysql_url():
    return os.environ.get("GALAXY_TEST_CONNECT_MYSQL_URI")


@pytest.fixture
def sqlite_memory_url():
    return "sqlite:///:memory:"


@pytest.fixture(scope="module")
def engine():
    db_uri = "sqlite:///:memory:"
    return create_engine(db_uri)


@pytest.fixture
def session(init_model, engine):
    with Session(engine) as s:
        yield s


@pytest.fixture(scope="module")
def tmp_directory():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


# model fixture factories


@pytest.fixture
def make_cleanup_event_history_association(session):
    def f(**kwd):
        model = m.CleanupEventHistoryAssociation(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_data_manager_history_association(session):
    def f(**kwd):
        model = m.DataManagerHistoryAssociation(**kwd)
        write_to_db(session, model)
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
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_event(session):
    def f(**kwd):
        model = m.Event(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_galaxy_session(session):
    def f(**kwd):
        model = m.GalaxySession(**kwd)
        write_to_db(session, model)
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
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_history(session, make_user):
    def f(**kwd):
        if "user" not in kwd:
            kwd["user"] = make_user()
        model = m.History(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_history_annotation_association(session):
    def f(**kwd):
        model = m.HistoryAnnotationAssociation(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_history_dataset_association(session):
    def f(**kwd):
        model = m.HistoryDatasetAssociation(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_history_dataset_collection_association(session):
    def f(**kwd):
        collection = m.DatasetCollection(collection_type="list")
        model = m.HistoryDatasetCollectionAssociation(**kwd)
        model.collection = collection
        write_to_db(session, model)
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
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_history_tag_association(session):
    def f(**kwd):
        model = m.HistoryTagAssociation(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_history_user_share_association(session):
    def f(**kwd):
        model = m.HistoryUserShareAssociation(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_job(session):
    def f(**kwd):
        model = m.Job(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_job_export_history_archive(session):
    def f(**kwd):
        model = m.JobExportHistoryArchive(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_job_import_history_archive(session):
    def f(**kwd):
        model = m.JobImportHistoryArchive(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_role(session):
    def f(**kwd):
        model = m.Role(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_workflow(session):
    def f(**kwd):
        model = m.Workflow(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_workflow_invocation(session, make_workflow):
    def f(**kwd):
        if "workflow" not in kwd:
            kwd["workflow"] = make_workflow()
        model = m.WorkflowInvocation(**kwd)
        write_to_db(session, model)
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
        write_to_db(session, model)
        return model

    return f


# utility functions


@contextlib.contextmanager
def transaction(session):
    if not session.in_transaction():
        with session.begin():
            yield
    else:
        yield


def random_str() -> str:
    alphabet = string.ascii_lowercase + string.digits
    size = random.randint(5, 10)
    return "".join(random.choices(alphabet, k=size))


def random_email() -> str:
    text = random_str()
    return f"{text}@galaxy.testing"


def write_to_db(session, model) -> None:
    with transaction(session):
        session.add(model)
        session.commit()
