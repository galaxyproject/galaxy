import os
from types import SimpleNamespace
from typing import cast

import pytest

from galaxy import exceptions
from galaxy.config import GalaxyAppConfiguration
from galaxy.job_execution.setup import JobWorkingDirectory
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
