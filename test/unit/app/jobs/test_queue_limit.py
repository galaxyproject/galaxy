from typing import Optional
from unittest.mock import Mock

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

    def get_destinations(self, tag):
        return [create_mock_destination()]


class GalaxyJobConfigApp(GalaxyDataTestApp):

    def __init__(self, config: Optional[GalaxyDataTestConfig] = None, **kwd):
        super().__init__(config, **kwd)
        self.job_config = MockJobConfig()


def create_mock_app():
    return GalaxyJobConfigApp()


def create_job_wrapper(app: GalaxyJobConfigApp, user_id=None, session_id=None):
    if session_id:
        session = GalaxySession(id=session_id)
        app.model.session.add(session)
        app.model.session.commit()
    job = create_mock_job(app, user_id, session_id)
    job_wrapper = MinimalJobWrapper(job, app)  # type: ignore[arg-type]
    return job_wrapper


def create_mock_job(app: GalaxyJobConfigApp, user_id=None, session_id=None, state="new"):
    """Creates a mock job object."""
    job = Job()
    job.user_id = user_id
    job.session_id = session_id
    job.state = state
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
    result = job_wrapper.queue_with_limit(job, job_destination_mock)
    assert result is False


def test_anonymous_user_limit():
    app = create_mock_app()
    job_wrapper = create_job_wrapper(app, session_id=1)
    job = job_wrapper.get_job()
    job_destination_mock = create_mock_destination()

    create_mock_job(app, session_id=1, state="running")

    # Test below limit
    app.job_config.limits.anonymous_user_concurrent_jobs = 2
    result = job_wrapper.queue_with_limit(job, job_destination_mock)
    assert result is True

    # Test at limit
    result = job_wrapper.queue_with_limit(job, job_destination_mock)
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
    result = job_wrapper.queue_with_limit(job, job_destination_mock)
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
    result = job_wrapper.queue_with_limit(job, job_destination_mock)
    assert result is False
