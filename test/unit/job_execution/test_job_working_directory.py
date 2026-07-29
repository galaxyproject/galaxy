"""Unit tests for `JobWorkingDirectory` per-job isolation of custom paths.

These tests verify that a custom ``job.working_directory`` (set from the
``job_working_directory`` destination param) is treated as a parent/base and
that Galaxy appends ``<directory_hash_id(job.id)>/<job.id>/`` for per-job
isolation, mirroring the object-store layout.
"""

import os
from unittest.mock import MagicMock

import pytest

from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.model import Job
from galaxy.util import directory_hash_id


def _make_job(job_id: int) -> Job:
    job = Job()
    job.id = job_id
    return job


def _expected_per_job_path(base: str, job_id: int) -> str:
    return os.path.join(base, *directory_hash_id(job_id), str(job_id))


def _expected_cleared_path(base: str, job_id: int) -> str:
    return os.path.join(base, "_cleared_contents", *directory_hash_id(job_id), str(job_id))


@pytest.fixture
def object_store() -> MagicMock:
    return MagicMock()


class TestJobWorkingDirectoryCustomPath:
    """Custom-path branch (``job.working_directory`` set)."""

    def test_resolve_returns_per_job_path(self, tmp_path, object_store):
        base = str(tmp_path / "jobs")
        job = _make_job(100)
        job.working_directory = base
        jwd = JobWorkingDirectory(job, object_store)

        assert jwd.resolve() == _expected_per_job_path(base, 100)

    def test_resolve_uses_hash_for_large_ids(self, tmp_path, object_store):
        base = str(tmp_path / "jobs")
        job = _make_job(777777777)
        job.working_directory = base
        jwd = JobWorkingDirectory(job, object_store)

        assert jwd.resolve() == _expected_per_job_path(base, 777777777)
        # Sanity check the sharding for a large numeric id.
        assert directory_hash_id(777777777) == ["000", "777", "777"]

    def test_create_makes_per_job_dir(self, tmp_path, object_store):
        base = str(tmp_path / "jobs")
        job = _make_job(100)
        job.working_directory = base
        jwd = JobWorkingDirectory(job, object_store)

        path = jwd.create()
        assert path == _expected_per_job_path(base, 100)
        assert os.path.isdir(path)
        # The base must exist too (as parent of the per-job dir).
        assert os.path.isdir(base)

    def test_create_raises_on_preexisting_per_job_dir(self, tmp_path, object_store):
        base = str(tmp_path / "jobs")
        job = _make_job(100)
        job.working_directory = base
        jwd = JobWorkingDirectory(job, object_store)

        jwd.create()
        with pytest.raises(FileExistsError, match="already exists for job 100"):
            jwd.create()

    def test_exists_reflects_per_job_dir(self, tmp_path, object_store):
        base = str(tmp_path / "jobs")
        job = _make_job(100)
        job.working_directory = base
        jwd = JobWorkingDirectory(job, object_store)

        assert not jwd.exists()
        jwd.create()
        assert jwd.exists()

    def test_delete_removes_per_job_dir_only(self, tmp_path, object_store):
        base = str(tmp_path / "jobs")
        job = _make_job(100)
        job.working_directory = base
        jwd = JobWorkingDirectory(job, object_store)

        path = jwd.create()
        with open(os.path.join(path, "output.txt"), "w") as f:
            f.write("data")

        assert jwd.delete() is True
        assert not os.path.exists(path)
        # The base must survive — other jobs may share it.
        assert os.path.isdir(base)

    def test_delete_is_noop_when_per_job_dir_missing(self, tmp_path, object_store):
        base = str(tmp_path / "jobs")
        os.makedirs(base)
        job = _make_job(100)
        job.working_directory = base
        jwd = JobWorkingDirectory(job, object_store)

        # Should not raise even though the per-job dir was never created.
        assert jwd.delete() is False
        assert os.path.isdir(base)

    def test_cleared_contents_base_returns_root_divergent_path(self, tmp_path, object_store):
        base = str(tmp_path / "jobs")
        job = _make_job(100)
        job.working_directory = base
        jwd = JobWorkingDirectory(job, object_store)

        cleared = jwd.cleared_contents_base()
        assert cleared == _expected_cleared_path(base, 100)
        assert os.path.isdir(cleared)
        # The cleared path must NOT be inside the per-job JWD path.
        jwd_path = _expected_per_job_path(base, 100)
        assert not cleared.startswith(jwd_path + os.sep)

    def test_cleared_contents_base_is_sibling_of_jwd(self, tmp_path, object_store):
        """Both the JWD and the archive are rooted at <base>; neither contains the other."""
        base = str(tmp_path / "jobs")
        job = _make_job(777777777)
        job.working_directory = base
        jwd = JobWorkingDirectory(job, object_store)

        jwd_path = jwd.resolve()
        cleared = jwd.cleared_contents_base()

        # Both share the base as a common ancestor and diverge below it.
        assert os.path.commonpath([jwd_path, cleared]) == base

    def test_two_jobs_sharing_base_get_distinct_paths(self, tmp_path, object_store):
        base = str(tmp_path / "jobs")
        job_a = _make_job(100)
        job_a.working_directory = base
        job_b = _make_job(101)
        job_b.working_directory = base

        jwd_a = JobWorkingDirectory(job_a, object_store)
        jwd_b = JobWorkingDirectory(job_b, object_store)

        assert jwd_a.resolve() != jwd_b.resolve()
        assert jwd_a.cleared_contents_base() != jwd_b.cleared_contents_base()


class TestJobWorkingDirectoryObjectStore:
    """Object-store branch (``job.working_directory`` unset) delegates unchanged."""

    def test_resolve_delegates_to_object_store(self, object_store):
        job = _make_job(100)
        job.working_directory = None
        jwd = JobWorkingDirectory(job, object_store)

        object_store.get_filename.return_value = "/data/job_work/000/100"
        assert jwd.resolve() == "/data/job_work/000/100"
        object_store.get_filename.assert_called_once()
