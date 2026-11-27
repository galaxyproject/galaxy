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
    cached_create_tool_from_representation,
    clean_object_store_caches,
    queue_jobs,
)
from galaxy.exceptions import ObjectNotFound
from galaxy.model.unittest_utils.model_testing_utils import initialize_model
from galaxy.objectstore import BaseObjectStore
from galaxy.objectstore.caching import CacheTarget
from galaxy.schema.tasks import (
    QueueJobs,
    RequestUser,
    ToolSource,
)


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

    @pytest.fixture
    def mock_jwd_delete(self, mocker):
        """Patch ``JobWorkingDirectory.delete`` and return the mock.

        The patched method returns ``True`` by default (simulating a successful
        deletion); individual tests can configure side effects to simulate errors.
        """
        mock = mocker.patch("galaxy.celery.tasks.JobWorkingDirectory.delete")
        mock.return_value = True
        return mock

    def test_no_failed_jobs_returns_zero(self, sa_session, mock_jwd_delete):
        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)
        assert result == 0
        mock_jwd_delete.assert_not_called()

    def test_deletes_jwd_for_old_failed_jobs(self, sa_session, mock_jwd_delete):
        """A matching job is delegated to JobWorkingDirectory.delete and counted."""
        job = _make_job(state="error", age_days=10)
        sa_session.add(job)
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 1
        mock_jwd_delete.assert_called_once()

    def test_deletes_multiple_old_failed_jobs(self, sa_session, mock_jwd_delete):
        jobs = [_make_job(state="error", age_days=10) for _ in range(3)]
        sa_session.add_all(jobs)
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 3
        assert mock_jwd_delete.call_count == 3

    def test_skips_jobs_not_old_enough(self, sa_session, mock_jwd_delete):
        job = _make_job(state="error", age_days=1)
        sa_session.add(job)
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 0
        mock_jwd_delete.assert_not_called()

    def test_skips_non_failed_jobs(self, sa_session, mock_jwd_delete):
        job = _make_job(state="ok", age_days=30)
        sa_session.add(job)
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 0
        mock_jwd_delete.assert_not_called()

    def test_deletes_jwd_for_jobs_without_object_store_id(self, sa_session, mock_jwd_delete):
        """Jobs using the default object store have object_store_id=None but should still be cleaned up."""
        job = _make_job(state="error", age_days=10)
        job.object_store_id = None
        sa_session.add(job)
        sa_session.commit()

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 1
        mock_jwd_delete.assert_called_once()

    def test_only_deletes_matching_jobs_when_mixed(self, sa_session, mock_jwd_delete):
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
        assert mock_jwd_delete.call_count == 2

    def test_handles_already_deleted_jwd(self, sa_session, mock_jwd_delete):
        """When JobWorkingDirectory.delete raises ObjectNotFound, the job is skipped."""
        job = _make_job(state="error", age_days=10)
        sa_session.add(job)
        sa_session.commit()

        mock_jwd_delete.side_effect = ObjectNotFound("JWD not found")

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)
        assert result == 0

    def test_delete_returning_false_is_not_counted(self, sa_session, mock_jwd_delete):
        """When JobWorkingDirectory.delete returns False (nothing deleted), the job is not counted."""
        job = _make_job(state="error", age_days=10)
        sa_session.add(job)
        sa_session.commit()

        mock_jwd_delete.return_value = False

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)
        assert result == 0

    def test_handles_os_error_on_delete(self, sa_session, mock_jwd_delete):
        """OSError from JobWorkingDirectory.delete is logged and the job is skipped."""
        job = _make_job(state="error", age_days=10)
        sa_session.add(job)
        sa_session.commit()

        mock_jwd_delete.side_effect = OSError("disk failure")

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 0

    def test_continues_after_error_on_one_job(self, sa_session, mock_jwd_delete):
        """An error deleting one job's JWD does not prevent deleting subsequent jobs."""
        jobs = [_make_job(state="error", age_days=10) for _ in range(3)]
        sa_session.add_all(jobs)
        sa_session.commit()

        # The second job fails; the first and third should still be counted.
        mock_jwd_delete.side_effect = [True, OSError("disk failure"), True]

        object_store = MagicMock()
        result = _cleanup_jwds(sa_session, object_store, days=7)

        assert result == 2
        assert mock_jwd_delete.call_count == 3


SIMPLE_TOOL = """<tool id="cache_key_tool" name="Cache key tool" version="1.0">
    <command>echo hi > '$out'</command>
    <inputs/>
    <outputs><data name="out" format="txt"/></outputs>
</tool>"""


@pytest.fixture
def clean_tool_cache():
    cached_create_tool_from_representation.cache_clear()
    yield
    cached_create_tool_from_representation.cache_clear()


def _queue_jobs_request(dynamic_tool_id):
    return QueueJobs(
        tool_source=ToolSource(raw_tool_source=SIMPLE_TOOL, tool_source_class="XmlToolSource"),
        tool_request_id=1,
        user=RequestUser(user_id=1),
        use_cached_jobs=True,
        rerun_remap_job_id=None,
        dynamic_tool_id=dynamic_tool_id,
    )


def test_queue_jobs_uses_a_tool_per_dynamic_tool_revision(clean_tool_cache):
    # JobSubmitter.queue_jobs sets per-revision state on the cached tool, so revisions with
    # identical source must not share one object between concurrent tasks.
    # MockApp registers itself as the app the task wrapper injects.
    MockApp()
    job_submitter = MagicMock()
    for dynamic_tool_id in (1, 2, None, 1):
        queue_jobs(request=_queue_jobs_request(dynamic_tool_id), job_submitter=job_submitter)
    revision_a, revision_b, not_dynamic, again_a = (call.args[0] for call in job_submitter.queue_jobs.call_args_list)
    assert len({id(revision_a), id(revision_b), id(not_dynamic)}) == 3
    assert revision_a is again_a
