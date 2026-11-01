import os
from types import SimpleNamespace
from typing import cast

import pytest

from galaxy import exceptions
from galaxy.config import GalaxyAppConfiguration
from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.managers.job_files import JobFilesManager
from galaxy.model import (
    DynamicTool,
    Job,
    MetadataFile,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.objectstore import BaseObjectStore
from galaxy.security.idencoding import IdEncodingHelper

JOB_ID = 42


class FakeSession:
    def __init__(self, *jobs: Job):
        self.jobs = {job.id: job for job in jobs}

    def get(self, model_class, id):
        assert model_class is Job
        return self.jobs.get(id)


@pytest.fixture
def security():
    return IdEncodingHelper(id_secret="job-files-test-secret")


@pytest.fixture
def job(tmp_path):
    job = Job()
    job.id = JOB_ID
    job.state = Job.states.RUNNING
    # A custom working directory resolves without the object store.
    job.working_directory = str(tmp_path / "jobs")
    return job


@pytest.fixture
def manager(tmp_path, security, job):
    config = SimpleNamespace(
        new_file_path=str(tmp_path / "new_files"),
        nginx_upload_job_files_store=str(tmp_path / "nginx"),
        job_files_tus_upload_dir=str(tmp_path / "tus"),
    )
    return JobFilesManager(
        cast(GalaxyAppConfiguration, config),
        security,
        cast(BaseObjectStore, None),
        cast(galaxy_scoped_session, FakeSession(job)),
    )


def _keys(security, job_id=JOB_ID):
    return security.encode_id(job_id), security.encode_id(job_id, kind="jobs_files")


def _working_directory(job):
    return JobWorkingDirectory(job, cast(BaseObjectStore, None)).resolve()


def test_authorize_write_in_working_directory(manager, security, job):
    job_id, job_key = _keys(security)
    working_directory = _working_directory(job)
    assert manager.authorize_write(job_id, os.path.join(working_directory, "out"), job_key) == working_directory


def test_authorize_write_outside_job_files(manager, security, tmp_path):
    job_id, job_key = _keys(security)
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.authorize_write(job_id, str(tmp_path / "outside"), job_key)


def test_invalid_job_key(manager, security, job):
    job_id, _ = _keys(security)
    path = os.path.join(_working_directory(job), "out")
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.authorize_write(job_id, path, "invalid")
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.readable_path(job_id, path, "invalid")


def test_job_key_for_another_job(manager, security, job):
    job_id, _ = _keys(security)
    _, other_job_key = _keys(security, JOB_ID + 1)
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.authorize_write(job_id, os.path.join(_working_directory(job), "out"), other_job_key)


def test_unknown_job(manager, security, job):
    job_id, job_key = _keys(security, JOB_ID + 1)
    with pytest.raises(exceptions.ObjectNotFound):
        manager.authorize_write(job_id, os.path.join(_working_directory(job), "out"), job_key)


@pytest.mark.parametrize("state", [Job.states.OK, Job.states.ERROR, Job.states.DELETED])
def test_completed_job(manager, security, job, state):
    job_id, job_key = _keys(security)
    path = os.path.join(_working_directory(job), "out")
    assert manager.authorize_write(job_id, path, job_key)
    manager.assert_job_active(job_id)
    # The endpoint re-checks the job after the body arrives, so a job that finished mid-upload is rejected.
    job.state = state
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.assert_job_active(job_id)
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.authorize_write(job_id, path, job_key)
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.readable_path(job_id, path, job_key)


def test_missing_params(manager, security, job):
    job_id, job_key = _keys(security)
    path = os.path.join(_working_directory(job), "out")
    with pytest.raises(exceptions.ObjectAttributeMissingException):
        manager.authorize_write(job_id, None, job_key)
    with pytest.raises(exceptions.ObjectAttributeMissingException):
        manager.authorize_write(job_id, path, None)


def test_empty_path(manager, security, job):
    job_id, job_key = _keys(security)
    with pytest.raises(exceptions.RequestParameterInvalidException):
        manager.authorize_write(job_id, "", job_key)
    with pytest.raises(exceptions.RequestParameterInvalidException):
        manager.readable_path(job_id, "", job_key)


def _dataset(file_name, extra_files_path=None, metadata_file_name=None):
    metadata = {}
    if metadata_file_name:
        metadata_file = MetadataFile()
        metadata_file.__dict__["get_file_name"] = lambda sync_cache=True: metadata_file_name
        metadata["bam_index"] = metadata_file
    return SimpleNamespace(
        get_file_name=lambda sync_cache=True: file_name,
        extra_files_path=extra_files_path,
        metadata=metadata,
        dataset=SimpleNamespace(purged=not file_name),
    )


def _set_datasets(job, inputs=(), outputs=()):
    # Bypass the relationships' backref machinery, which stand-in datasets can't satisfy.
    job.__dict__["input_datasets"] = [SimpleNamespace(dataset=dataset) for dataset in inputs]
    job.__dict__["input_library_datasets"] = []
    job.__dict__["output_datasets"] = [SimpleNamespace(dataset=dataset) for dataset in outputs]
    job.__dict__["output_library_datasets"] = []


def test_purged_output_dataset_does_not_authorize_the_process_cwd(manager, security, job):
    job_id, job_key = _keys(security)
    # ``get_file_name()`` is empty for a purged dataset and ``abspath("")`` is the cwd.
    _set_datasets(job, outputs=[_dataset("")])
    assert manager._output_dataset_path(job, os.getcwd()) is None
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.authorize_write(job_id, os.getcwd(), job_key)


@pytest.fixture(params=["user_defined_tool", "strict_destination"])
def restricted_job(request, job):
    if request.param == "user_defined_tool":
        job.dynamic_tool = DynamicTool(tool_format="GalaxyUserTool")
    else:
        job.destination_params = {"job_files_policy": "strict"}
    return job


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return str(path)


@pytest.fixture
def job_files(tmp_path, job):
    datasets = tmp_path / "objects"
    input_extra_files = datasets / "dataset_1_files"
    files = SimpleNamespace(
        outside=_write(tmp_path / "galaxy.yml", "secret"),
        input=_write(datasets / "dataset_1.dat", "input"),
        input_extra_file=_write(input_extra_files / "index.html", "extra"),
        input_metadata_file=_write(datasets / "_metadata_files" / "metadata_1.dat", "bai"),
        output=_write(datasets / "dataset_2.dat"),
        output_extra_files=str(datasets / "dataset_2_files"),
    )
    _set_datasets(
        job,
        inputs=[_dataset(files.input, str(input_extra_files), files.input_metadata_file)],
        outputs=[_dataset(files.output, files.output_extra_files)],
    )
    return files


def _job_path(job, *parts):
    return os.path.join(_working_directory(job), *parts)


@pytest.fixture
def outside_link(restricted_job, job_files):
    link = _job_path(restricted_job, "working", "link")
    os.makedirs(os.path.dirname(link))
    os.symlink(job_files.outside, link)
    return link


def test_restricted_job_reads_its_own_files(manager, security, restricted_job, job_files):
    job_id, job_key = _keys(security)
    paths = [
        _write(_job_path(restricted_job, "tool_script.sh")),
        _write(_job_path(restricted_job, "configs", "tmp_config")),
        _write(_job_path(restricted_job, "inputs", "materialized.dat")),
        job_files.input,
        job_files.input_extra_file,
        job_files.input_metadata_file,
    ]
    for path in paths:
        assert manager.readable_path(job_id, path, job_key) == path


def test_restricted_job_reads_nothing_else(manager, security, restricted_job, job_files, outside_link, tmp_path):
    job_id, job_key = _keys(security)
    object_store_conf = _write(_job_path(restricted_job, "metadata", "object_store_conf.json"))
    for path in [job_files.outside, outside_link, object_store_conf, str(tmp_path / "missing")]:
        with pytest.raises(exceptions.ItemAccessibilityException):
            manager.readable_path(job_id, path, job_key)


def test_unrestricted_job_reads_any_file(manager, security, job, job_files):
    job_id, job_key = _keys(security)
    assert manager.readable_path(job_id, job_files.outside, job_key) == job_files.outside


def test_restricted_job_purged_input_does_not_match_the_process_cwd(manager, security, restricted_job):
    job_id, job_key = _keys(security)
    _set_datasets(restricted_job, inputs=[_dataset("")])
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.readable_path(job_id, os.getcwd(), job_key)


def test_restricted_job_purged_input_is_reported(manager, security, restricted_job, tmp_path):
    job_id, job_key = _keys(security)
    _set_datasets(restricted_job, inputs=[_dataset("")])
    with pytest.raises(exceptions.ItemDeletionException):
        manager.readable_path(job_id, str(tmp_path / "dataset_1.dat"), job_key)


@pytest.mark.parametrize(
    "relative",
    [
        "working/out.txt",
        "working/sub/dir/galaxy.json",
        "outputs/tool_stdout",
        "outputs/COMMAND_VERSION",
        "outputs/dataset_2.dat",
        "metadata/metadata_out_HistoryDatasetAssociation_2",
        "metadata/__instrument_core_galaxy_slots",
    ],
)
def test_restricted_job_writes_staged_results(manager, security, restricted_job, relative):
    job_id, job_key = _keys(security)
    working_directory = _working_directory(restricted_job)
    assert manager.authorize_write(job_id, _job_path(restricted_job, relative), job_key) == working_directory


def test_restricted_job_writes_its_outputs(manager, security, restricted_job, job_files):
    job_id, job_key = _keys(security)
    output_directory = os.path.dirname(job_files.output)
    assert manager.authorize_write(job_id, job_files.output, job_key) == output_directory
    extra_file = os.path.join(job_files.output_extra_files, "child.txt")
    assert manager.authorize_write(job_id, extra_file, job_key) == output_directory


@pytest.mark.parametrize(
    "relative",
    [
        "tool_script.sh",
        "command.sh",
        "container_runtime.json",
        "configs/tmp_config",
        "inputs/materialized.dat",
        "metadata/outputs_populated/collection.json",
        "metadata/outputs_populated",
        "working",
        "working/../tool_script.sh",
    ],
)
def test_restricted_job_refuses_other_job_directory_writes(manager, security, restricted_job, relative):
    job_id, job_key = _keys(security)
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.authorize_write(job_id, _job_path(restricted_job, relative), job_key)


def test_restricted_job_refuses_writes_outside_the_job(manager, security, restricted_job, job_files):
    job_id, job_key = _keys(security)
    for path in [job_files.outside, job_files.input, job_files.input_metadata_file]:
        with pytest.raises(exceptions.ItemAccessibilityException):
            manager.authorize_write(job_id, path, job_key)


def test_restricted_job_refuses_writes_through_symlinks(manager, security, restricted_job, job_files, outside_link):
    job_id, job_key = _keys(security)
    linked_directory = _job_path(restricted_job, "outputs")
    os.symlink(os.path.dirname(job_files.outside), linked_directory)
    for path in [outside_link, os.path.join(linked_directory, "galaxy.yml")]:
        with pytest.raises(exceptions.ItemAccessibilityException):
            manager.authorize_write(job_id, path, job_key)
