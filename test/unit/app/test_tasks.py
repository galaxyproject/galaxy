import os
from datetime import (
    datetime,
    timedelta,
)
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from galaxy import model
from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.celery.tasks import (
    _cleanup_jwds,
    clean_object_store_caches,
)
from galaxy.exceptions import ObjectNotFound
from galaxy.model.unittest_utils.model_testing_utils import initialize_model
from galaxy.objectstore import BaseObjectStore
from galaxy.objectstore.caching import CacheTarget


class MockObjectStore:
    def __init__(self, cache_targets: list[CacheTarget]):
        self._cache_targets = cache_targets

    def cache_targets(self) -> list[CacheTarget]:
        return self._cache_targets


def test_clean_object_store_caches(tmp_path):
    container = MockApp()
    cache_targets: list[CacheTarget] = []
    container[BaseObjectStore] = MockObjectStore(cache_targets)  # type: ignore[assignment]

    # similar code used in object store unit tests
    cache_dir = tmp_path
    path = cache_dir / "a_file_0"
    path.write_text("this is an example file")

    # works fine on an empty list of cache targets...
    clean_object_store_caches()

    assert path.exists()

    # place the file in mock object store's cache targets and
    # run the task again and the above file should be gone.
    cache_targets.append(CacheTarget(cache_dir, 1, 0.000000001))
    # works fine on an empty list of cache targets...
    clean_object_store_caches()

    assert not path.exists()


@pytest.fixture
def sa_session():
    engine = create_engine("sqlite:///:memory:")
    initialize_model(model.mapper_registry, engine)
    with Session(engine) as session:
        yield session


def _make_job(state: str, age_days: int) -> model.Job:
    job = model.Job()
    job.state = state
    job.update_time = datetime.now() - timedelta(days=age_days)
    job.object_store_id = "mock_store"
    return job


class TestCleanupJwds:
    """Tests for _cleanup_jwds using a real in-memory database with actual Job model instances."""

    def test_no_failed_jobs_returns_zero(self, sa_session):
        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)
        assert result == 0
        object_store.delete.assert_not_called()

    def test_deletes_jwd_for_old_failed_jobs(self, sa_session):
        """Legacy job (working_directory=None): object_store.delete is called."""
        job = _make_job(state="error", age_days=10)
        sa_session.add(job)
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 1
        object_store.delete.assert_called_once()
        call_args = object_store.delete.call_args
        assert isinstance(call_args[0][0], model.Job)
        assert call_args[1]["base_dir"] == "job_work"
        assert call_args[1]["entire_dir"] is True

    def test_deletes_multiple_old_failed_jobs(self, sa_session):
        jobs = [_make_job(state="error", age_days=10) for _ in range(3)]
        sa_session.add_all(jobs)
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 3
        assert object_store.delete.call_count == 3

    def test_skips_jobs_not_old_enough(self, sa_session):
        job = _make_job(state="error", age_days=1)
        sa_session.add(job)
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 0
        object_store.delete.assert_not_called()

    def test_skips_non_failed_jobs(self, sa_session):
        job = _make_job(state="ok", age_days=30)
        sa_session.add(job)
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 0
        object_store.delete.assert_not_called()

    def test_deletes_jwd_for_jobs_without_object_store_id(self, sa_session):
        """Jobs using the default object store have object_store_id=None but should still be cleaned up."""
        job = _make_job(state="error", age_days=10)
        job.object_store_id = None
        sa_session.add(job)
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 1
        object_store.delete.assert_called_once()

    def test_only_deletes_matching_jobs_when_mixed(self, sa_session):
        """With both matching and non-matching jobs in the DB, only matching ones are deleted.

        This catches the 'Query is always truthy' bug: without .all(), the `if not failed_jobs`
        check never triggers, and iterating a Query that should be empty may yield wrong rows.
        """
        # Matching: old + failed + has object_store_id
        old_failed = _make_job(state="error", age_days=10)
        # Matching: old + failed but no object_store_id (default object store)
        no_store = _make_job(state="error", age_days=10)
        no_store.object_store_id = None
        # Non-matching: old + ok
        old_ok = _make_job(state="ok", age_days=10)
        # Non-matching: recent + failed
        recent_failed = _make_job(state="error", age_days=1)
        sa_session.add_all([old_failed, no_store, old_ok, recent_failed])
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 2
        assert object_store.delete.call_count == 2

    def test_handles_already_deleted_jwd(self, sa_session):
        """When object_store.delete raises ObjectNotFound, the job is skipped."""
        job = _make_job(state="error", age_days=10)
        sa_session.add(job)
        sa_session.commit()

        object_store = MagicMock()
        object_store.delete.side_effect = ObjectNotFound("JWD not found")

        result = _cleanup_jwds(sa_session, object_store, days=7)
        assert result == 0

    def test_deletes_custom_path_jwd(self, sa_session, tmp_path):
        """Custom-path job (working_directory set): shutil.rmtree is used on the custom path."""
        job = _make_job(state="error", age_days=10)
        jwd_path = tmp_path / "custom_jwd" / str(job.id)
        jwd_path.mkdir(parents=True)
        (jwd_path / "some_file.txt").write_text("job output")
        job.working_directory = str(jwd_path)
        sa_session.add(job)
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 1
        object_store.delete.assert_not_called()
        assert not jwd_path.exists()

    def test_handles_os_error_on_delete(self, sa_session, tmp_path):
        """OSError during delete is logged and the job is skipped."""
        job = _make_job(state="error", age_days=10)
        jwd_path = tmp_path / "custom_jwd" / str(job.id)
        jwd_path.mkdir(parents=True)
        job.working_directory = str(jwd_path)
        sa_session.add(job)
        sa_session.commit()

        object_store = MagicMock()
        # Make shutil.rmtree fail by making the directory read-only
        os.chmod(jwd_path, 0o000)

        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 0
        object_store.delete.assert_not_called()
        # Restore permissions for cleanup
        os.chmod(jwd_path, 0o755)
