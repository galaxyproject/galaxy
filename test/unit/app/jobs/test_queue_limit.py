from unittest.mock import Mock

import pytest

from galaxy.jobs import (
    JobConfigurationLimits,
    MinimalJobWrapper,
)
from galaxy.model import (
    GalaxySession,
    Job,
)
from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.model.unittest_utils.data_app import GalaxyDataTestConfig


class MockJobConfig:
    def __init__(self) -> None:
        self.limits = JobConfigurationLimits()
        self.destination_tags: dict[str, set[str]] = {"one": {"one"}, "two": {"one"}}

    def get_destination_ids_for_tag(self, tag):
        return self.destination_tags.get(tag, set())


class GalaxyJobConfigApp(GalaxyDataTestApp):
    def __init__(self, config: GalaxyDataTestConfig | None = None, **kwd):
        super().__init__(config, **kwd)
        self.job_config = MockJobConfig()


def create_mock_app():
    return GalaxyJobConfigApp()


def create_job_wrapper(app: GalaxyJobConfigApp, user_id=None, session_id=None, state="new", destination_id=None):
    if session_id and app.model.session.get(GalaxySession, session_id) is None:
        session = GalaxySession(id=session_id)
        app.model.session.add(session)
        app.model.session.commit()
    job = create_mock_job(app, user_id, session_id, state=state, destination_id=destination_id)
    job_wrapper = MinimalJobWrapper(job, app)  # type: ignore[arg-type]
    return job_wrapper


def create_mock_job(app: GalaxyJobConfigApp, user_id=None, session_id=None, state="new", destination_id=None):
    """Creates a mock job object."""
    job = Job()
    job.user_id = user_id
    job.session_id = session_id
    job.state = state
    job.destination_id = destination_id
    app.model.session.add(job)
    app.model.session.commit()
    return job


def create_mock_destination():
    """Creates a mock job destination."""
    job_destination_mock = Mock()
    job_destination_mock.id = "one"
    job_destination_mock.params = {}
    job_destination_mock.runner = "test_runner"
    job_destination_mock.tags = ["one", "two"]
    return job_destination_mock


def test_registered_user_limit():
    app = create_mock_app()
    job_wrapper = create_job_wrapper(app, user_id=1)
    job = job_wrapper.get_job()
    job_destination_mock = create_mock_destination()

    for _ in range(2):
        create_mock_job(app, user_id=1, state="running")

    # Test below limit
    job_wrapper.app.job_config.limits.registered_user_concurrent_jobs = 3
    result = job_wrapper.queue_with_limit(job, job_destination_mock)
    assert result is True

    # Test at limit
    other_job_wrapper = create_job_wrapper(app, user_id=1)
    result = other_job_wrapper.queue_with_limit(other_job_wrapper.get_job(), job_destination_mock)
    assert result is False


def test_anonymous_user_limit():
    app = create_mock_app()
    job_wrapper = create_job_wrapper(app, session_id=1)
    job = job_wrapper.get_job()
    job_destination_mock = create_mock_destination()

    create_mock_job(app, session_id=1, state="running")

    # Test no jobs
    app.job_config.limits.anonymous_user_concurrent_jobs = 0
    result = job_wrapper.queue_with_limit(job, job_destination_mock)
    assert result is False

    # Test below limit
    app.job_config.limits.anonymous_user_concurrent_jobs = 2
    result = job_wrapper.queue_with_limit(job, job_destination_mock)
    assert result is True

    # Test at limit
    other_job_wrapper = create_job_wrapper(app, session_id=1)
    result = other_job_wrapper.queue_with_limit(other_job_wrapper.get_job(), job_destination_mock)
    assert result is False


def test_destination_total_limit():
    app = create_mock_app()
    job_wrapper = create_job_wrapper(app, user_id=1)
    job = job_wrapper.get_job()
    job_destination_mock = create_mock_destination()

    # Test below limit
    app.job_config.limits.destination_total_concurrent_jobs["one"] = 1
    result = job_wrapper.queue_with_limit(job, job_destination_mock)
    assert result is True

    # Test at limit
    other_job_wrapper = create_job_wrapper(app, user_id=1)
    result = other_job_wrapper.queue_with_limit(other_job_wrapper.get_job(), job_destination_mock)
    assert result is False


def test_destination_tag_limit():
    app = create_mock_app()
    job_wrapper = create_job_wrapper(app, user_id=1)
    job = job_wrapper.get_job()
    job_destination_mock = create_mock_destination()

    # Test below limit
    app.job_config.limits.destination_total_concurrent_jobs["two"] = 1
    result = job_wrapper.queue_with_limit(job, job_destination_mock)
    assert result is True

    # Test at limit
    other_job_wrapper = create_job_wrapper(app, user_id=1)
    result = other_job_wrapper.queue_with_limit(other_job_wrapper.get_job(), job_destination_mock)
    assert result is False


def test_destination_tag_limit_counts_dynamic_destinations():
    app = create_mock_app()
    app.job_config.destination_tags["two"] = {"one", "dynamic"}
    app.job_config.limits.destination_total_concurrent_jobs["two"] = 2
    create_mock_job(app, user_id=2, state="running", destination_id="dynamic")
    job_destination_mock = create_mock_destination()

    # Test below limit
    job_wrapper = create_job_wrapper(app, user_id=1)
    assert job_wrapper.queue_with_limit(job_wrapper.get_job(), job_destination_mock) is True

    # Test at limit
    job_wrapper = create_job_wrapper(app, user_id=1)
    assert job_wrapper.queue_with_limit(job_wrapper.get_job(), job_destination_mock) is False


def test_destination_user_tag_limit():
    app = create_mock_app()
    app.job_config.destination_tags["two"] = {"one", "dynamic"}
    app.job_config.limits.destination_user_concurrent_jobs["two"] = 3
    for user_id in (1, 2):
        for destination_id in ("one", "dynamic"):
            create_mock_job(app, user_id=user_id, state="running", destination_id=destination_id)
    job_destination_mock = create_mock_destination()

    # Test below limit, other users' jobs in the tagged destinations are not counted
    job_wrapper = create_job_wrapper(app, user_id=1)
    assert job_wrapper.queue_with_limit(job_wrapper.get_job(), job_destination_mock) is True

    # Test at limit
    job_wrapper = create_job_wrapper(app, user_id=1)
    assert job_wrapper.queue_with_limit(job_wrapper.get_job(), job_destination_mock) is False

    job_wrapper = create_job_wrapper(app, user_id=2)
    assert job_wrapper.queue_with_limit(job_wrapper.get_job(), job_destination_mock) is True


def set_registered_user_limit(limits):
    limits.registered_user_concurrent_jobs = 2


def set_anonymous_user_limit(limits):
    limits.anonymous_user_concurrent_jobs = 2


def set_destination_user_limit(limits):
    limits.destination_user_concurrent_jobs["one"] = 2


def set_destination_total_limit(limits):
    limits.destination_total_concurrent_jobs["one"] = 2


def set_destination_tag_limit(limits):
    limits.destination_total_concurrent_jobs["two"] = 2


@pytest.mark.parametrize(
    "set_limit,owner",
    [
        (set_registered_user_limit, {"user_id": 1}),
        (set_anonymous_user_limit, {"session_id": 1}),
        (set_destination_user_limit, {"user_id": 1}),
        (set_destination_total_limit, {"user_id": 1}),
        (set_destination_tag_limit, {"user_id": 1}),
    ],
)
def test_resubmitted_jobs_at_limit(set_limit, owner):
    app = create_mock_app()
    set_limit(app.job_config.limits)
    job_destination_mock = create_mock_destination()
    job_wrappers = [create_job_wrapper(app, state="resubmitted", destination_id="one", **owner) for _ in range(2)]

    # Resubmitted jobs already count towards the limit, they must not block each other
    for job_wrapper in job_wrappers:
        assert job_wrapper.queue_with_limit(job_wrapper.get_job(), job_destination_mock) is True

    new_job_wrapper = create_job_wrapper(app, **owner)
    assert new_job_wrapper.queue_with_limit(new_job_wrapper.get_job(), job_destination_mock) is False


def test_more_resubmitted_jobs_than_destination_user_limit():
    app = create_mock_app()
    app.job_config.limits.destination_user_concurrent_jobs["one"] = 2
    job_destination_mock = create_mock_destination()
    job_wrappers = [create_job_wrapper(app, user_id=1, state="resubmitted", destination_id="one") for _ in range(3)]

    # Resubmitted jobs are queued in order, up to the limit
    results = [
        job_wrapper.queue_with_limit(job_wrapper.get_job(), job_destination_mock) for job_wrapper in job_wrappers
    ]
    assert results == [True, True, False]

    # Once a slot frees up, the remaining resubmitted job can be queued
    finished_job = job_wrappers[0].get_job()
    finished_job.state = "ok"
    app.model.session.commit()
    last_job = job_wrappers[2].get_job()
    assert job_wrappers[2].queue_with_limit(last_job, job_destination_mock) is True
