import contextlib
import os
import tempfile
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from galaxy import model as m
from galaxy.model.unittest_utils.utils import (
    random_email,
    random_str,
)


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
def make_dataset_collection(session):
    def f(**kwd):
        model = m.DatasetCollection(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_dataset_collection_element(session, make_hda):
    def f(**kwd):
        kwd["element"] = kwd.get("element") or make_hda()
        model = m.DatasetCollectionElement(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_dataset_permissions(session):
    def f(**kwd):
        model = m.DatasetPermissions(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_default_history_permissions(session, make_history, make_role):
    def f(**kwd):
        kwd["history"] = kwd.get("history") or make_history()
        kwd["action"] = kwd.get("action") or random_str()
        kwd["role"] = kwd.get("role") or make_role()
        model = m.DefaultHistoryPermissions(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_default_user_permissions(session, make_user, make_role):
    def f(**kwd):
        kwd["user"] = kwd.get("user") or make_user()
        kwd["action"] = kwd.get("action") or random_str()
        kwd["role"] = kwd.get("role") or make_role()
        model = m.DefaultUserPermissions(**kwd)
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
        kwd["galaxy_session"] = kwd.get("galaxy_session") or make_galaxy_session()
        kwd["history"] = kwd.get("history") or make_history()
        model = m.GalaxySessionToHistoryAssociation(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_group(session):
    def f(**kwd):
        model = m.Group(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_group_role_association(session):
    def f(group, role):
        model = m.GroupRoleAssociation(group, role)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_hda(session, make_history):
    def f(**kwd):
        kwd["history"] = kwd.get("history") or make_history()
        model = m.HistoryDatasetAssociation(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_hdca(session):
    def f(**kwd):
        model = m.HistoryDatasetCollectionAssociation(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_history(session, make_user):
    def f(**kwd):
        kwd["user"] = kwd.get("user") or make_user()
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
        model = m.HistoryDatasetCollectionAssociation(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_history_rating_association(session, make_user, make_history):
    def f(**kwd):
        kwd["user"] = kwd.get("user") or make_user()
        kwd["item"] = kwd.get("item") or make_history()
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
def make_ldca(session):
    def f(**kwd):
        model = m.LibraryDatasetCollectionAssociation(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_ldda(session):
    def f(**kwd):
        model = m.LibraryDatasetDatasetAssociation(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_library(session):
    def f(**kwd):
        model = m.Library(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_library_folder(session):
    def f(**kwd):
        model = m.LibraryFolder(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_library_permissions(session, make_library, make_role):
    def f(**kwd):
        action = kwd.get("action") or random_str()
        library = kwd.get("library") or make_library()
        role = kwd.get("role") or make_role()
        model = m.LibraryPermissions(action, library, role)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_page(session, make_user):
    def f(**kwd):
        kwd["user"] = kwd.get("user") or make_user()
        model = m.Page(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_role(session):
    def f(**kwd):
        # We must specify `name` because after removing the unique constraint
        # from role.name (migration 9a5207190a4d) and setting up a default name
        # generation for roles that do not receive a name argument that does
        # not generate unique names, any migration unit tests that use
        # this fixture AFTER DOWNGRADING (like # test_migrations.py::test_349dd9d9aac9)
        # would break due to violating that constraint (restored via
        # downgrading) without setting name.
        kwd["name"] = kwd.get("name") or random_str()
        model = m.Role(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_stored_workflow(session, make_user):
    def f(**kwd):
        kwd["user"] = kwd.get("user") or make_user()
        model = m.StoredWorkflow(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_task(session, make_job):
    def f(**kwd):
        kwd["job"] = kwd.get("job") or make_job()
        # Assumption: if the following args are needed, a test should supply them
        kwd["working_directory"] = kwd.get("working_directory") or random_str()
        kwd["prepare_files_cmd"] = kwd.get("prepare_files_cmd") or random_str()
        model = m.Task(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_user(session):
    def f(**kwd):
        kwd["username"] = kwd.get("username") or random_str()
        kwd["email"] = kwd.get("email") or random_email()
        kwd["password"] = kwd.get("password") or random_str()
        model = m.User(**kwd)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_user_item_rating_association(session):
    def f(assoc_class, user, item, rating):
        model = assoc_class(user, item, rating)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_user_group_association(session):
    def f(user, group):
        model = m.UserGroupAssociation(user, group)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_user_role_association(session):
    def f(user, role):
        model = m.UserRoleAssociation(user, role)
        write_to_db(session, model)
        return model

    return f


@pytest.fixture
def make_visualization(session, make_user):
    def f(**kwd):
        kwd["user"] = kwd.get("user") or make_user()
        model = m.Visualization(**kwd)
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
        kwd["workflow"] = kwd.get("workflow") or make_workflow()
        model = m.WorkflowInvocation(**kwd)
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


def write_to_db(session, model) -> None:
    with transaction(session):
        session.add(model)
        session.commit()
