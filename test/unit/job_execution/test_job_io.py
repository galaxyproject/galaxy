import tempfile

import pytest

from galaxy.files import (
    ConfiguredFileSources,
    DictFileSourcesUserContext,
)
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.job_execution.setup import JobIO
from galaxy.model import (
    DatasetCollectionElement,
    HistoryDatasetAssociation,
    Job,
)
from galaxy.model.unittest_utils import GalaxyDataTestApp

WORKING_DIRECTORY = "/tmp"
VERSION_PATH = "/tmp/version"
GALAXY_URL = "http://galaxy"
USER_CONTEXT = {
    "email": "test@email.com",
    "username": "user",
    "ftp_dir": "tmp/ftp_dir",
    "preferences": {"a": "b"},
    "role_names": ["role1"],
    "group_names": ["group1"],
    "is_admin": False,
}


class FileSourcesMockApp(GalaxyDataTestApp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_sources = ConfiguredFileSources(
            FileSourcePluginsConfig.from_app_config(self.config),
        )


@pytest.fixture
def app() -> FileSourcesMockApp:
    return FileSourcesMockApp()


@pytest.fixture
def job(app: FileSourcesMockApp) -> Job:
    job = Job()
    session = app.model.session
    session.add(job)
    session.commit()
    return job


@pytest.fixture
def job_io(app: FileSourcesMockApp, job: Job) -> JobIO:
    user_context = DictFileSourcesUserContext(**USER_CONTEXT)
    return JobIO(
        sa_session=app.model.session,
        job=job,
        working_directory=WORKING_DIRECTORY,
        outputs_directory=WORKING_DIRECTORY,
        outputs_to_working_directory=True,
        galaxy_url=GALAXY_URL,
        version_path=VERSION_PATH,
        tool_directory=WORKING_DIRECTORY,
        home_directory=WORKING_DIRECTORY,
        tmp_directory=WORKING_DIRECTORY,
        tool_data_path=WORKING_DIRECTORY,
        galaxy_data_manager_data_path=WORKING_DIRECTORY,
        new_file_path=WORKING_DIRECTORY,
        len_file_path=WORKING_DIRECTORY,
        builds_file_path=WORKING_DIRECTORY,
        user_context=USER_CONTEXT,
        file_sources_dict=app.file_sources.to_dict(for_serialization=True, user_context=user_context),
        check_job_script_integrity=False,
        check_job_script_integrity_count=1,
        check_job_script_integrity_sleep=1,
        tool_dir=WORKING_DIRECTORY,
        is_task=False,
    )


def test_job_io_serialization(job_io: JobIO):
    job_io_dict = job_io.to_dict()
    assert isinstance(job_io_dict, dict)
    assert isinstance(job_io_dict["file_sources_dict"], dict)
    assert isinstance(job_io_dict["user_context"], dict)


def test_job_io_deserialization(job_io: JobIO):
    with tempfile.NamedTemporaryFile() as temp:
        job_io.to_json(temp.name)
        new_job_io = JobIO.from_json(temp.name, job_io.sa_session)
    assert isinstance(new_job_io, JobIO)
    assert isinstance(new_job_io.file_sources_dict, dict)
    assert isinstance(new_job_io.file_sources, ConfiguredFileSources)


def _job_with_input(app: FileSourcesMockApp, job: Job, name: str) -> HistoryDatasetAssociation:
    session = app.model.session
    hda = HistoryDatasetAssociation(create_dataset=True, sa_session=session)
    session.add(hda)
    job.add_input_dataset(name, dataset=hda)
    session.commit()
    return hda


def test_get_input_datasets_uses_materialized_dataset(app: FileSourcesMockApp, job: Job, job_io: JobIO):
    _job_with_input(app, job, "input")
    materialized = HistoryDatasetAssociation(create_dataset=True, sa_session=app.model.session)
    assert job_io.get_input_datasets({"input": materialized}) == [materialized]


def test_get_input_datasets_uses_materialized_collection_element(app: FileSourcesMockApp, job: Job, job_io: JobIO):
    # A job mapped over a collection of deferred datasets materializes its input as a
    # collection element. Pulsar stages only what this method returns.
    _job_with_input(app, job, "mode|input")
    materialized = HistoryDatasetAssociation(create_dataset=True, sa_session=app.model.session)
    element = DatasetCollectionElement(element=materialized, element_index=0, element_identifier="forward")
    assert job_io.get_input_datasets({"mode|input": element}) == [materialized]
