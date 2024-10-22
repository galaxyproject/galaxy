import datetime
import tempfile
from functools import lru_cache
from typing import (
    Dict,
    List,
)

from celery.result import AsyncResult
from sqlalchemy import text

from galaxy.celery import galaxy_task
from galaxy.model.database_utils import sqlalchemy_engine
from galaxy.util import ExecutionTimer
from galaxy_test.driver.driver_util import init_database
from galaxy_test.driver.integration_util import (
    IntegrationTestCase,
    skip_unless_postgres,
)


@galaxy_task
def mock_user_id_task(task_user_id: int):
    return task_user_id


@lru_cache
def sqlite_url():
    path = tempfile.NamedTemporaryFile().name
    dburl = f"sqlite:///{path}"
    init_database(dburl)
    return dburl


@lru_cache
def setup_users(dburl: str, num_users: int = 2):
    """
    Setup test users in galaxy_user table with user id's starting from 2.
    This is because the new celery_user_rate_limit table has
    a user_id with a foreign key pointing to galaxy_user table.
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


class TestCeleryUserRateLimitIntegration(IntegrationTestCase):
    """
    Test feature that limits the number of celery task executions
    per user per second. This is implemented by the celery_user_rate_limit
    config parameter whose default value is 0.0 meaning no rate limit.
    For each of a set of users it submits runs a task num_calls times.
    For the test to succeed the total duration of completion of all task
    executions should be equal to the tasks_per_user_per_sec times
    num_calls-1. This is because tasks for different users should be
    executed in parallel. In addition, we verify that the total
    duration for execution of tasks for each user equals the total
    task duration, again because tasks for different users should
    run in parallel.
    """

    def setUp(self):
        super().setUp()

    def _test_mock_pass_user_id_task(self, num_users: int, num_calls: int, tasks_per_user_per_sec: float):
        users = list(range(2, num_users + 2))
        expected_duration: float
        if tasks_per_user_per_sec == 0.0:
            expected_duration = 0.0
            expected_duration_lbound = 0.0
        else:
            secs_between_tasks_per_user = 1 / tasks_per_user_per_sec
            expected_duration = secs_between_tasks_per_user * (num_calls - 1)
            expected_duration_lbound = expected_duration - 4
        expected_duration_hbound = expected_duration + 4
        start_time = datetime.datetime.now(datetime.timezone.utc)
        timer = ExecutionTimer()
        #  Invoke test task num_calls times for each user
        results: Dict[int, List[AsyncResult]] = {}
        for user in users:
            user_results: List[AsyncResult] = []
            for _ in range(num_calls):
                user_results.append(mock_user_id_task.delay(task_user_id=user))
            results[user] = user_results
        #  Collect results of each call
        for user, user_results in results.items():
            for result in user_results:
                val = result.get(timeout=1000)
                assert val == user
        elapsed = timer.elapsed
        #  Verify that total elapsed time for all executions match expection
        #  of num_calls * scheduling delay between task executions
        assert elapsed >= expected_duration_lbound and elapsed <= expected_duration_hbound
        #  Verify that total elapsed time for execution of all tasks for
        #  an individual user is the same as total expected duration.
        #  Tasks run for different users run in parallel.
        for user_results in results.values():
            last_task_end_time = start_time
            for result in user_results:
                if result.date_done > last_task_end_time:
                    last_task_end_time = result.date_done
            user_elapsed = (last_task_end_time - start_time).total_seconds()
            assert user_elapsed >= expected_duration_lbound and user_elapsed <= expected_duration_hbound


@skip_unless_postgres()
class TestCeleryUserRateLimitIntegrationPostgres(TestCeleryUserRateLimitIntegration):
    _user_rate_limit = 0.1

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["celery_user_rate_limit"] = cls._user_rate_limit

    def setUp(self):
        super().setUp()
        dburl = self._app.config.database_connection  # that's how you get to galaxy app instance
        setup_users(dburl)

    def test_mock_pass_user_id_task(self):
        self._test_mock_pass_user_id_task(2, 3, self._user_rate_limit)


class TestCeleryUserRateLimitIntegrationSqlite(TestCeleryUserRateLimitIntegration):
    _user_rate_limit = 0.1

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["check_migrate_databases"] = False
        config["database_connection"] = sqlite_url()
        if config.get("database_engine_option_pool_size"):
            config.pop("database_engine_option_pool_size")
        if config.get("database_engine_option_max_overflow"):
            config.pop("database_engine_option_max_overflow")
        config["celery_user_rate_limit"] = cls._user_rate_limit

    def setUp(self):
        super().setUp()
        dburl = self._app.config.database_connection  # that's how you get to galaxy app instance
        setup_users(dburl)

    def test_mock_pass_user_id_task(self):
        self._test_mock_pass_user_id_task(2, 3, self._user_rate_limit)


class TestCeleryUserRateLimitIntegrationNoLimit(TestCeleryUserRateLimitIntegration):
    _user_rate_limit = 0.0

    def test_mock_pass_user_id_task(self):
        self._test_mock_pass_user_id_task(2, 3, self._user_rate_limit)
