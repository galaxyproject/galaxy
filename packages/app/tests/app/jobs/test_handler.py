"""Exercise handler polls against real databases, including PostgreSQL's ready window."""

import math
import os
from collections import Counter
from types import SimpleNamespace
from typing import (
    cast,
    TYPE_CHECKING,
)
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url

from galaxy import model
from galaxy.jobs import JobConfigurationLimits
from galaxy.jobs.handler import (
    JOB_ERROR,
    JOB_USER_OVER_TOTAL_WALLTIME,
    JOB_WAIT,
    JobHandlerQueue,
)
from galaxy.jobs.job_destination import JobDestination
from galaxy.jobs.mapper import (
    JobNotReadyException,
    JobRunnerMapper,
    STOCK_RULES,
)
from galaxy.model.database_utils import DbUrl
from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.model.unittest_utils.model_testing_utils import create_and_drop_database

if TYPE_CHECKING:
    from galaxy.jobs import JobWrapper

WINDOW = 2


class HandlerJobWrapper:
    """Keep destination mapping real; replace runner preparation and output handling."""

    def __init__(self, job, queue, **kwds):
        self.job_id = job.id
        self.app = queue.app
        self.tool = SimpleNamespace(
            id="handler_test",
            get_job_destination=lambda params: JobDestination(runner="dynamic", params={"type": "handler_test"}),
        )
        self.job_runner_mapper = JobRunnerMapper(cast("JobWrapper", self), Mock(), self.app.job_config)

    def get_job(self):
        return self.app.model.context.get(model.Job, self.job_id)

    @property
    def job_destination(self):
        return self.job_runner_mapper.get_job_destination({})

    def fail(self, message):
        self.get_job().set_state(model.Job.states.ERROR)

    def pause(self, job, message):
        job.set_state(model.Job.states.PAUSED)

    def is_ready_for_resubmission(self, job):
        return True


class HandlerHarness:
    def __init__(self, app, monkeypatch):
        self.app = app
        self.attempts = []
        self.dispatched = []
        self.deferred = {}
        self.selected: list[tuple[int | None, int | None]] = []
        self.destination = JobDestination(id="local", runner="local")
        app.job_config = SimpleNamespace(
            limits=JobConfigurationLimits(),
            handler_assignment_methods=[],
            handler_ready_window_size=WINDOW,
            dynamic_params=None,
            get_destination=lambda id: self.destination,
        )
        app.config.track_jobs_in_database = True
        app.config.cache_user_job_count = True
        app.config.user_activation_on = False
        app.config.monitor_thread_join_timeout = 0
        app.execution_timer_factory = Mock()
        monkeypatch.setitem(STOCK_RULES, "handler_test", self.map_destination)
        self.queue = JobHandlerQueue(app, SimpleNamespace(put=self.dispatch, url_to_destination=Mock()))
        monkeypatch.setattr(self.queue, "job_wrapper", lambda job, **kwds: HandlerJobWrapper(job, self.queue, **kwds))
        select_ready_jobs = self.queue._select_ready_jobs

        def record_candidates():
            jobs, cursors = select_ready_jobs()
            self.selected = [(job.user_id, job.session_id if job.user_id is None else None) for job in jobs]
            return jobs, cursors

        monkeypatch.setattr(self.queue, "_select_ready_jobs", record_candidates)

    def map_destination(self, job_id):
        self.attempts.append(job_id)
        if job_id in self.deferred:
            raise JobNotReadyException(job_state=self.deferred[job_id])
        return self.destination

    def dispatch(self, wrapper):
        self.dispatched.append(wrapper.job_id)
        job = wrapper.get_job()
        job.set_state(model.Job.states.QUEUED)
        job.destination_id = wrapper.job_destination.id

    def user(self):
        user = model.User(email=f"{uuid4()}@example.org")
        user.password = "unused"
        user.active = True
        self.app.model.context.add(user)
        self.app.model.context.commit()
        return user.id

    def session(self, user_id=None):
        session = model.GalaxySession(user_id=user_id)
        self.app.model.context.add(session)
        self.app.model.context.commit()
        return session.id

    def update_job(self, job_id, **values):
        job = self.app.model.context.get(model.Job, job_id)
        for key, value in values.items():
            setattr(job, key, value)
        self.app.model.context.commit()

    def job(self, user_id=None, session_id=None, handler="main", state="new", input_state="ok"):
        session = self.app.model.context
        dataset = model.Dataset(state=input_state)
        hda = model.HistoryDatasetAssociation(dataset=dataset)
        job = model.Job()
        job.user_id = user_id
        job.session_id = session_id
        job.handler = handler
        job.state = state
        job.tool_id = "handler_test"
        job.add_input_dataset("input", hda)
        session.add_all([dataset, hda, job])
        session.commit()
        return job.id

    def poll(self):
        self.attempts.clear()
        self.selected.clear()
        self.queue._JobHandlerQueue__monitor_step()  # type: ignore[attr-defined]
        if self.queue.track_jobs_in_database and self.app.model.engine.dialect.name == "postgresql":
            per_partition = Counter(self.selected)
            assert all(count <= WINDOW for count in per_partition.values()), f"ready window exceeded: {per_partition}"
            assert len(self.queue.job_wrappers) <= len(self.selected), "wrappers cached for unselected jobs"
        return self.attempts[:]


@pytest.fixture
def handler(request, tmp_path, monkeypatch):
    backend = getattr(request, "param", "postgresql")
    if backend == "postgresql":
        connection = os.environ.get("GALAXY_TEST_DBURI") or os.environ.get("GALAXY_TEST_CONNECT_POSTGRES_URI")
        if not connection or make_url(connection).get_backend_name() != "postgresql":
            pytest.skip("Set GALAXY_TEST_DBURI to a PostgreSQL URL to exercise the production ranked query")
        url = make_url(connection).set(database=f"galaxytest_handler_{uuid4().hex}")
        connection = url.render_as_string(hide_password=False)
    else:
        connection = f"sqlite:///{tmp_path / 'handler.sqlite'}"
    with create_and_drop_database(DbUrl(connection)):
        app = GalaxyDataTestApp(root=str(tmp_path), database_connection=connection)
        assert app.model.engine.dialect.name == backend
        try:
            yield HandlerHarness(app, monkeypatch)
        finally:
            app.model.context.remove()
            app.model.engine.dispose()


@pytest.mark.parametrize("backlog", [5, 21])
def test_mapper_deferral_does_not_starve_later_jobs(handler, backlog):
    user = handler.user()
    deferred = [handler.job(user) for _ in range(backlog)]
    handler.deferred.update(dict.fromkeys(deferred))
    ready = handler.job(user)
    other_user_job = handler.job(handler.user())

    for poll in range(math.ceil(backlog / WINDOW) + 1):
        attempts = handler.poll()
        assert len(set(attempts) - {other_user_job}) <= WINDOW
        if poll == 0:
            assert attempts[:WINDOW] == deferred[:WINDOW]
            assert other_user_job in handler.dispatched
    assert ready in handler.dispatched
    assert not set(deferred).intersection(handler.dispatched)

    handler.deferred.clear()
    for _ in range(backlog + 2):
        handler.poll()
    assert Counter(handler.dispatched) == Counter([*deferred, ready, other_user_job])


def test_new_arrivals_do_not_postpone_retry(handler):
    user = handler.user()
    original = [handler.job(user) for _ in range(6)]
    handler.deferred.update(dict.fromkeys(original))
    assert handler.poll() == original[:WINDOW]
    handler.deferred.clear()
    # Grow the tail faster than it can be drained. The original sweep must end
    # and retry the prefix anyway, without dispatching any job twice.
    for _ in range(3):
        for _ in range(3):
            job = handler.job(user)
            handler.deferred[job] = None
        assert len(handler.poll()) <= WINDOW
    assert Counter(handler.dispatched) == Counter(original)


@pytest.mark.parametrize("change", ["deleted", "error", "ok", "move", "remove", "inactive", "input"])
def test_sweep_cleans_up_unavailable_jobs(handler, change):
    user = handler.user()
    jobs = [handler.job(user) for _ in range(6)]
    handler.deferred.update(dict.fromkeys(jobs))
    handler.poll()
    assert len(handler.queue._ready_job_cursors) == 1
    session = handler.app.model.context
    for job_id in jobs:
        job = session.get(model.Job, job_id)
        if change == "move":
            job.handler = "other_handler"
        elif change == "remove":
            session.delete(job)
        elif change == "inactive":
            handler.app.config.user_activation_on = True
            job.user.active = False
        elif change == "input":
            job.input_datasets[0].dataset.dataset.state = model.Dataset.states.NEW
        else:
            job.state = change
    session.commit()
    assert handler.poll() == []
    assert handler.queue._ready_job_cursors == {}
    assert handler.queue._mapper_waiting_partitions == set()
    assert handler.queue.job_wrappers == {}
    assert handler.dispatched == []


def test_cancelling_sweep_tail_restarts_at_prefix(handler):
    user = handler.user()
    jobs = [handler.job(user) for _ in range(6)]
    handler.deferred.update(dict.fromkeys(jobs))
    handler.poll()
    handler.deferred.clear()
    for job in jobs[WINDOW:]:
        handler.update_job(job, state=model.Job.states.DELETED)
    assert handler.poll() == []
    assert handler.poll() == jobs[:WINDOW]
    assert handler.dispatched == jobs[:WINDOW]


def test_anonymous_sessions_have_independent_windows(handler):
    user = handler.user()
    anonymous = handler.session()
    assert anonymous == user  # Separate database sequences deliberately overlap.
    other_anonymous = handler.session()
    signed_in_sessions = [handler.session(user) for _ in range(2)]
    user_jobs = [handler.job(user, signed_in_sessions[i % 2]) for i in range(6)]
    anonymous_jobs = [handler.job(session_id=anonymous) for _ in range(6)]
    other_jobs = [handler.job(session_id=other_anonymous) for _ in range(6)]
    handler.deferred.update(dict.fromkeys([*user_jobs, *anonymous_jobs]))
    for i in range(3):
        attempts = handler.poll()
        window = slice(WINDOW * i, WINDOW * (i + 1))
        assert attempts == user_jobs[window] + anonymous_jobs[window] + other_jobs[window]
    assert handler.dispatched == other_jobs


@pytest.mark.parametrize("limit", ["destination", "user"])
def test_ordinary_limits_keep_front_window_and_cached_destinations(handler, limit):
    user = handler.user()
    jobs = [handler.job(user) for _ in range(4)]
    limits = handler.app.job_config.limits
    if limit == "destination":
        limits.destination_total_concurrent_jobs["local"] = 0
    else:
        handler.job(user, state="running")
        limits.registered_user_concurrent_jobs = 1
    assert handler.poll() == jobs[:WINDOW]
    assert handler.poll() == []  # Successful mappings are cached during ordinary waits.
    assert handler.queue._ready_job_cursors == {}
    assert handler.dispatched == []
    limits.destination_total_concurrent_jobs.clear()
    limits.registered_user_concurrent_jobs = None
    handler.poll()
    assert handler.dispatched == jobs[:WINDOW]
    handler.poll()
    assert handler.dispatched == jobs


def test_sweep_advances_through_ordinary_waits(handler):
    user = handler.user()
    jobs = [handler.job(user) for _ in range(6)]
    handler.deferred.update(dict.fromkeys(jobs[:WINDOW]))
    handler.app.job_config.limits.destination_total_concurrent_jobs["local"] = 0
    assert handler.poll() == jobs[:WINDOW]
    assert handler.poll() == jobs[WINDOW : 2 * WINDOW]
    handler.app.job_config.limits.destination_total_concurrent_jobs.clear()
    assert handler.poll() == jobs[2 * WINDOW :]
    assert handler.dispatched == jobs[2 * WINDOW :]


@pytest.mark.parametrize(
    "state,expected", [(None, JOB_WAIT), (JOB_WAIT, JOB_WAIT), (JOB_ERROR, JOB_ERROR), ("custom", "custom")]
)
def test_exception_state_is_preserved(handler, state, expected):
    job_id = handler.job(handler.user())
    handler.deferred[job_id] = state
    job = handler.app.model.context.get(model.Job, job_id)
    wrapper = handler.queue.job_wrapper(job)
    assert handler.queue._JobHandlerQueue__verify_job_ready(job, wrapper) == (expected, None)
    assert bool(handler.queue._mapper_waiting_partitions) == (expected == JOB_WAIT)


def test_nondefault_exception_state_uses_existing_poll_handling(handler):
    user = handler.user()
    jobs = [handler.job(user) for _ in range(3)]
    handler.deferred.update(dict.fromkeys(jobs[:WINDOW], JOB_USER_OVER_TOTAL_WALLTIME))
    handler.poll()
    session = handler.app.model.context
    assert [session.get(model.Job, job).state for job in jobs] == ["paused", "paused", "new"]
    assert handler.queue._ready_job_cursors == {}
    handler.poll()
    assert handler.dispatched == jobs[WINDOW:]


def test_input_validity_activation_and_handler_ownership(handler):
    user = handler.user()
    jobs = [handler.job(user) for _ in range(6)]
    handler.deferred.update(dict.fromkeys(jobs[:WINDOW]))
    foreign = handler.job(user, handler="other_handler")
    unready = handler.job(user, input_state="new")
    invalid = handler.job(user, input_state="error")
    inactive_user = handler.user()
    inactive = handler.job(inactive_user)
    handler.app.model.context.get(model.User, inactive_user).active = False
    handler.app.model.context.commit()
    handler.app.config.user_activation_on = True
    for _ in range(5):
        handler.poll()
    assert handler.dispatched == jobs[WINDOW:]
    session = handler.app.model.context
    assert session.get(model.Job, invalid).state == "paused"
    assert [session.get(model.Job, job).state for job in (foreign, unready, inactive)] == ["new"] * 3


def test_resubmitted_jobs_bypass_ready_window(handler):
    user = handler.user()
    jobs = [handler.job(user) for _ in range(6)]
    handler.deferred.update(dict.fromkeys(jobs))
    handler.poll()
    resubmit = handler.job(user, state="resubmitted")
    handler.update_job(resubmit, destination_id="local", job_runner_name="local")
    handler.poll()
    assert handler.dispatched == [resubmit]


def test_restart_retries_prefix_and_handler_transfer_starts_fresh(handler, monkeypatch):
    user = handler.user()
    jobs = [handler.job(user) for _ in range(6)]
    handler.deferred.update(dict.fromkeys(jobs[: 2 * WINDOW]))
    handler.poll()
    restarted = HandlerHarness(handler.app, monkeypatch)
    restarted.deferred.update(handler.deferred)
    assert restarted.poll() == jobs[:WINDOW]
    for job in jobs:
        restarted.update_job(job, handler="other_handler")
    assert restarted.poll() == []
    assert restarted.queue._ready_job_cursors == {}
    other = HandlerHarness(handler.app, monkeypatch)
    other.app.config.server_name = "other_handler"
    other.deferred.update(handler.deferred)
    assert other.poll() == jobs[:WINDOW]
    assert other.poll() == jobs[WINDOW : 2 * WINDOW]
    assert other.poll() == jobs[2 * WINDOW :]
    assert other.dispatched == jobs[2 * WINDOW :]


@pytest.mark.parametrize("handler", ["sqlite"], indirect=True)
@pytest.mark.parametrize("database_queue", [True, False])
def test_unwindowed_queues_still_retry_deferred_jobs(handler, database_queue):
    handler.queue.track_jobs_in_database = database_queue
    user = handler.user()
    jobs = [handler.job(user) for _ in range(6)]
    handler.deferred.update(dict.fromkeys(jobs[:5]))
    if not database_queue:
        for job in jobs:
            handler.queue.put(job, "handler_test")
    assert handler.poll() == jobs
    assert handler.dispatched == jobs[5:]
    handler.deferred.clear()
    assert handler.poll() == jobs[:5]
    assert Counter(handler.dispatched) == Counter(jobs)
    assert handler.queue._ready_job_cursors == {}
