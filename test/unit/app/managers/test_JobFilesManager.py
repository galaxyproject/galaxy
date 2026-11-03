import os
from types import SimpleNamespace
from typing import cast

import pytest

from galaxy import exceptions
from galaxy.config import GalaxyAppConfiguration
from galaxy.job_execution.setup import (
    JobWorkingDirectory,
    write_job_files_manifest,
)
from galaxy.managers.job_files import JobFilesManager
from galaxy.model import Job
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
def config(tmp_path):
    return SimpleNamespace(
        new_file_path=str(tmp_path / "new_files"),
        nginx_upload_job_files_store=str(tmp_path / "nginx"),
        job_files_tus_upload_dir=str(tmp_path / "tus"),
        job_files_strict_access=False,
    )


@pytest.fixture
def strict(config):
    config.job_files_strict_access = True


@pytest.fixture
def manager(config, security, job):
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


def _dataset(file_name, extra_files_path=None):
    return SimpleNamespace(
        get_file_name=lambda sync_cache=True: file_name,
        extra_files_path=extra_files_path,
        purged=not file_name,
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


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return str(path)


def _job_path(job, *parts):
    return os.path.join(_working_directory(job), *parts)


def _write_manifest(job, readable_paths, remote_extended_metadata=False):
    os.makedirs(_working_directory(job), exist_ok=True)
    write_job_files_manifest(_working_directory(job), readable_paths, remote_extended_metadata=remote_extended_metadata)


@pytest.fixture
def job_files(tmp_path, job):
    datasets = tmp_path / "objects"
    files = SimpleNamespace(
        outside=_write(tmp_path / "galaxy.yml", "secret"),
        input=_write(datasets / "dataset_1.dat", "input"),
        input_extra_file=_write(datasets / "dataset_1_files" / "index.html", "extra"),
        input_metadata_file=_write(datasets / "_metadata_files" / "metadata_1.dat", "bai"),
        output=_write(datasets / "dataset_2.dat"),
        output_extra_files=str(datasets / "dataset_2_files"),
    )
    _set_datasets(job, inputs=[_dataset(files.input)], outputs=[_dataset(files.output, files.output_extra_files)])
    return files


@pytest.fixture
def outside_link(job, job_files):
    link = _job_path(job, "working", "link")
    os.makedirs(os.path.dirname(link))
    os.symlink(job_files.outside, link)
    return link


def test_strict_job_reads_its_manifest(manager, security, job, job_files, outside_link, strict):
    job_id, job_key = _keys(security)
    tool_script = _write(_job_path(job, "tool_script.sh"))
    # A symlinked reference file is staged by its link's path.
    paths = [tool_script, job_files.input, job_files.input_extra_file, job_files.input_metadata_file, outside_link]
    _write_manifest(job, paths)
    for path in paths:
        assert manager.readable_path(job_id, path, job_key) == path


def test_strict_job_reads_nothing_outside_its_manifest(manager, security, job, job_files, strict, tmp_path):
    job_id, job_key = _keys(security)
    _write_manifest(job, [job_files.input])
    paths = [
        job_files.outside,
        _write(_job_path(job, "tool_script.sh")),
        _write(_job_path(job, "metadata", "object_store_conf.json")),
        # The manifest holds the exact paths Pulsar requests.
        os.path.join(os.path.dirname(job_files.input), "..", "objects", "dataset_1.dat"),
        str(tmp_path / "missing"),
    ]
    for path in paths:
        with pytest.raises(exceptions.ItemAccessibilityException):
            manager.readable_path(job_id, path, job_key)


def test_strict_job_without_manifest_reads_nothing(manager, security, job, job_files, strict):
    job_id, job_key = _keys(security)
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.readable_path(job_id, job_files.input, job_key)


def test_job_reads_outside_its_manifest_with_a_warning(manager, security, job, job_files, caplog):
    job_id, job_key = _keys(security)
    _write_manifest(job, [job_files.input])
    assert manager.readable_path(job_id, job_files.input, job_key) == job_files.input
    assert "job_files_strict_access" not in caplog.text
    assert manager.readable_path(job_id, job_files.outside, job_key) == job_files.outside
    assert "job_files_strict_access" in caplog.text


def test_strict_job_purged_input_is_reported(manager, security, job, strict, tmp_path):
    job_id, job_key = _keys(security)
    purged_input = str(tmp_path / "dataset_1.dat")
    _set_datasets(job, inputs=[_dataset("")])
    _write_manifest(job, [purged_input])
    with pytest.raises(exceptions.ItemDeletionException):
        manager.readable_path(job_id, purged_input, job_key)


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
def test_strict_job_writes_staged_results(manager, security, job, strict, relative):
    job_id, job_key = _keys(security)
    assert manager.authorize_write(job_id, _job_path(job, relative), job_key) == _working_directory(job)


def test_strict_job_writes_its_outputs(manager, security, job, job_files, strict):
    job_id, job_key = _keys(security)
    output_directory = os.path.dirname(job_files.output)
    assert manager.authorize_write(job_id, job_files.output, job_key) == output_directory
    extra_file = os.path.join(job_files.output_extra_files, "child.txt")
    assert manager.authorize_write(job_id, extra_file, job_key) == output_directory


@pytest.mark.parametrize(
    "relative",
    [
        "job_files_manifest.json",
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
def test_strict_job_refuses_other_job_directory_writes(manager, security, job, strict, relative):
    job_id, job_key = _keys(security)
    _write_manifest(job, [])
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.authorize_write(job_id, _job_path(job, relative), job_key)


def test_strict_job_with_remote_extended_metadata_writes_the_model_store(manager, security, job, strict):
    job_id, job_key = _keys(security)
    _write_manifest(job, [], remote_extended_metadata=True)
    path = _job_path(job, "metadata", "outputs_populated", "collection.json")
    assert manager.authorize_write(job_id, path, job_key) == _working_directory(job)


def test_strict_job_refuses_writes_outside_the_job(manager, security, job, job_files, strict):
    job_id, job_key = _keys(security)
    for path in [job_files.outside, job_files.input, job_files.input_metadata_file]:
        with pytest.raises(exceptions.ItemAccessibilityException):
            manager.authorize_write(job_id, path, job_key)


def test_strict_job_refuses_writes_through_symlinks(manager, security, job, job_files, outside_link, strict):
    job_id, job_key = _keys(security)
    linked_directory = _job_path(job, "outputs")
    os.symlink(os.path.dirname(job_files.outside), linked_directory)
    for path in [outside_link, os.path.join(linked_directory, "galaxy.yml")]:
        with pytest.raises(exceptions.ItemAccessibilityException):
            manager.authorize_write(job_id, path, job_key)


def test_strict_job_appends_only_its_tool_streams(manager, security, job, strict, tmp_path):
    job_id, _ = _keys(security)
    for relative in ["outputs/tool_stdout", "working/tool_stdout"]:
        path = _write(_job_path(job, relative), "first ")
        manager.write(job_id, path, _write(tmp_path / "upload", "second"))
        with open(path) as f:
            assert f.read() == ("first second" if relative.startswith("outputs") else "second")


STRICT_ACCESS_WARNING = "job_files_strict_access"


@pytest.mark.parametrize("relative", ["working/out.txt", "outputs/tool_stdout", "metadata/metadata_out_2"])
def test_job_writes_staged_results_without_a_warning(manager, security, job, caplog, relative):
    job_id, job_key = _keys(security)
    assert manager.authorize_write(job_id, _job_path(job, relative), job_key) == _working_directory(job)
    assert STRICT_ACCESS_WARNING not in caplog.text


def test_job_writes_its_outputs_without_a_warning(manager, security, job, job_files, caplog):
    job_id, job_key = _keys(security)
    assert manager.authorize_write(job_id, job_files.output, job_key) == os.path.dirname(job_files.output)
    assert STRICT_ACCESS_WARNING not in caplog.text


@pytest.mark.parametrize(
    "relative", ["tool_script.sh", "configs/tmp_config", "inputs/materialized.dat", "metadata/outputs_populated/c.json"]
)
def test_job_writes_other_job_directory_files_with_a_warning(manager, security, job, caplog, relative):
    job_id, job_key = _keys(security)
    _write_manifest(job, [])
    assert manager.authorize_write(job_id, _job_path(job, relative), job_key) == _working_directory(job)
    assert STRICT_ACCESS_WARNING in caplog.text


def test_job_writes_symlinks_inside_the_job_directory_with_a_warning(manager, security, job, caplog):
    job_id, job_key = _keys(security)
    link = _job_path(job, "working", "link")
    os.makedirs(os.path.dirname(link))
    os.symlink(_write(_job_path(job, "working", "target")), link)
    assert manager.authorize_write(job_id, link, job_key) == _working_directory(job)
    assert STRICT_ACCESS_WARNING in caplog.text


def test_job_appends_to_other_files_with_a_warning(manager, security, job, caplog, tmp_path):
    job_id, _ = _keys(security)
    stream = _write(_job_path(job, "outputs", "tool_stdout"), "first ")
    manager.write(job_id, stream, _write(tmp_path / "upload", "second"))
    assert STRICT_ACCESS_WARNING not in caplog.text
    other = _write(_job_path(job, "working", "tool_stdout"), "first ")
    manager.write(job_id, other, _write(tmp_path / "upload", "second"))
    assert STRICT_ACCESS_WARNING in caplog.text
    for path in [stream, other]:
        with open(path) as f:
            assert f.read() == "first second"
