import datetime
import tempfile
import time
from functools import lru_cache
from typing import Optional

from celery.result import AsyncResult
from sqlalchemy import (
    select,
    text,
)

from galaxy.celery import galaxy_task
from galaxy.model import CeleryUserActiveTask
from galaxy.model.database_utils import sqlalchemy_engine
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy_test.driver.driver_util import init_database
from galaxy_test.driver.integration_util import (
    IntegrationTestCase,
    skip_unless_postgres,
)


@galaxy_task(action="sleep for concurrency testing")
def mock_sleep_task(
    session: galaxy_scoped_session,
    sleep_seconds: float = 2.0,
    task_user_id: Optional[int] = None,
):
    """Task that sleeps for a configurable duration, used to test concurrency limits."""
    time.sleep(sleep_seconds)
    return task_user_id


@galaxy_task
def mock_fast_task(task_user_id: int):
    """Instant task used to verify cleanup after completion."""
    return task_user_id


@lru_cache
def sqlite_url():
    path = tempfile.NamedTemporaryFile().name
    dburl = f"sqlite:///{path}"
    init_database(dburl)
    return dburl


@lru_cache
def setup_users(dburl: str, num_users: int = 3):
    """
    Setup test users in galaxy_user table with user id's starting from 2.
    """
    expected_user_ids = list(range(2, num_users + 2))
    with sqlalchemy_engine(dburl) as engine:
        with engine.begin() as conn:
            found_user_ids = conn.scalars(
                text("select id from galaxy_user where id between 2 and :high"), {"high": num_users + 1}
            ).all()
            if len(expected_user_ids) > len(found_user_ids):
                user_ids_to_add = set(expected_user_ids).difference(found_user_ids)
                for user_id in user_ids_to_add:
                    conn.execute(
                        text("insert into galaxy_user(id, active, email, password) values (:id, :active, :email, :pw)"),
                        [{"id": user_id, "active": True, "email": f"e{user_id}", "pw": "p"}],
                    )


class TestCeleryUserConcurrencyLimitIntegration(IntegrationTestCase):
    """
    Base class for per-user concurrency limiting tests.
    Does not define test_* methods directly — subclasses call _test_* helpers.
    """

    _concurrency_limit = 2

    def setUp(self):
        super().setUp()

    def _get_active_task_count(self, user_id: int) -> int:
        """Query the tracking table for active tasks for a given user."""
        sa_session = self._app.model.session()
        try:
            count = len(
                sa_session.execute(select(CeleryUserActiveTask.task_id).where(CeleryUserActiveTask.user_id == user_id))
                .scalars()
                .all()
            )
            return count
        finally:
            sa_session.close()

    def _test_concurrency_limit_enforced(self):
        """
        Submit more tasks than the concurrency limit for a single user.
        With concurrency_limit=2 and 4 tasks each sleeping 2s, the tasks
        should take ~4s total (2 batches of 2). Without limits, they'd
        all run in ~2s.
        """
        user_id = 2
        num_tasks = 4
        sleep_seconds = 2.0

        start = datetime.datetime.now(datetime.timezone.utc)
        results: list[AsyncResult] = []
        for _ in range(num_tasks):
            results.append(mock_sleep_task.delay(sleep_seconds=sleep_seconds, task_user_id=user_id))

        # Collect all results
        for result in results:
            val = result.get(timeout=120)
            assert val == user_id

        elapsed = (datetime.datetime.now(datetime.timezone.utc) - start).total_seconds()
        # With concurrency=2, 4 tasks sleeping 2s each should take ~4s
        # (2 execute, finish, then the next 2 execute)
        expected_min = sleep_seconds * (num_tasks / self._concurrency_limit) - 1
        # Allow generous upper bound for scheduling overhead
        expected_max = sleep_seconds * (num_tasks / self._concurrency_limit) + 15
        assert elapsed >= expected_min, (
            f"Tasks completed too fast ({elapsed:.1f}s < {expected_min:.1f}s), "
            f"concurrency limit may not be enforced"
        )
        assert elapsed <= expected_max, f"Tasks took too long ({elapsed:.1f}s > {expected_max:.1f}s)"

    def _test_different_users_independent(self):
        """
        Tasks from different users should run independently.
        User A and User B each submit 2 tasks (at concurrency limit).
        All 4 tasks should complete in ~2s (parallel across users),
        not 4s (if users shared a limit).
        """
        user_a = 2
        user_b = 3
        sleep_seconds = 2.0

        start = datetime.datetime.now(datetime.timezone.utc)
        results: list[AsyncResult] = []
        # Submit concurrency_limit tasks for each user
        for user_id in [user_a, user_b]:
            for _ in range(self._concurrency_limit):
                results.append(mock_sleep_task.delay(sleep_seconds=sleep_seconds, task_user_id=user_id))

        for result in results:
            val = result.get(timeout=120)
            assert val in (user_a, user_b)

        elapsed = (datetime.datetime.now(datetime.timezone.utc) - start).total_seconds()
        # Both users run their tasks concurrently — should take ~2s, not ~4s
        expected_max = sleep_seconds + 15  # generous overhead
        assert elapsed <= expected_max, (
            f"Cross-user tasks took too long ({elapsed:.1f}s > {expected_max:.1f}s), "
            f"users may be sharing a concurrency limit"
        )

    def _test_tracking_rows_cleaned_up(self):
        """
        After tasks complete, their tracking rows should be removed
        from celery_user_active_task.
        """
        user_id = 2
        results = []
        for _ in range(3):
            results.append(mock_fast_task.delay(task_user_id=user_id))

        # Wait for all tasks to complete
        for result in results:
            result.get(timeout=60)

        # Give a moment for after_return to fire
        time.sleep(1)

        active_count = self._get_active_task_count(user_id)
        assert active_count == 0, f"Expected 0 active tracking rows after completion, found {active_count}"

    def _test_tasks_without_user_id_bypass_limit(self):
        """
        Tasks that don't provide task_user_id should bypass concurrency limiting.
        """
        # Submit tasks without task_user_id — they should run immediately
        results = []
        for _ in range(5):
            results.append(mock_fast_task.delay(task_user_id=0))

        # If concurrency limiting incorrectly applied, these would queue up
        for result in results:
            result.get(timeout=30)


@skip_unless_postgres()
class TestCeleryUserConcurrencyLimitPostgres(TestCeleryUserConcurrencyLimitIntegration):
    _concurrency_limit = 2

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["celery_user_concurrency_limit"] = cls._concurrency_limit

    def setUp(self):
        super().setUp()
        dburl = self._app.config.database_connection
        setup_users(dburl, num_users=3)

    def test_concurrency_limit_enforced(self):
        self._test_concurrency_limit_enforced()

    def test_different_users_independent(self):
        self._test_different_users_independent()

    def test_tracking_rows_cleaned_up(self):
        self._test_tracking_rows_cleaned_up()

    def test_tasks_without_user_id_bypass_limit(self):
        self._test_tasks_without_user_id_bypass_limit()


class TestCeleryUserConcurrencyLimitSqlite(TestCeleryUserConcurrencyLimitIntegration):
    _concurrency_limit = 2

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["check_migrate_databases"] = False
        config["database_connection"] = sqlite_url()
        if config.get("database_engine_option_pool_size"):
            config.pop("database_engine_option_pool_size")
        if config.get("database_engine_option_max_overflow"):
            config.pop("database_engine_option_max_overflow")
        config["celery_user_concurrency_limit"] = cls._concurrency_limit

    def setUp(self):
        super().setUp()
        dburl = self._app.config.database_connection
        setup_users(dburl, num_users=3)

    def test_concurrency_limit_enforced(self):
        self._test_concurrency_limit_enforced()

    def test_different_users_independent(self):
        self._test_different_users_independent()

    def test_tracking_rows_cleaned_up(self):
        self._test_tracking_rows_cleaned_up()

    def test_tasks_without_user_id_bypass_limit(self):
        self._test_tasks_without_user_id_bypass_limit()


class TestCeleryUserConcurrencyLimitDisabled(IntegrationTestCase):
    """Test that with concurrency_limit=0 (disabled), tasks run without restriction."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["check_migrate_databases"] = False
        config["database_connection"] = sqlite_url()
        if config.get("database_engine_option_pool_size"):
            config.pop("database_engine_option_pool_size")
        if config.get("database_engine_option_max_overflow"):
            config.pop("database_engine_option_max_overflow")

    def test_all_tasks_run_without_restriction(self):
        """With no limit, tasks should complete without concurrency deferral."""
        user_id = 2

        results = []
        for _ in range(5):
            results.append(mock_fast_task.delay(task_user_id=user_id))

        # All tasks should complete — none should be stuck waiting for a slot
        for result in results:
            val = result.get(timeout=30)
            assert val == user_id
