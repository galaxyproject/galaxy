from types import SimpleNamespace
from typing import cast
from unittest.mock import (
    Mock,
    patch,
)

import pytest

from galaxy import model
from galaxy.jobs import JobWrapper
from galaxy.jobs.handler import (
    DefaultJobDispatcher,
    JobHandlerQueue,
)
from galaxy.jobs.runners.engagequeue import EngageQueueJobRunner
from galaxy.managers.jobs import get_jobs_to_check_at_startup
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.model.unittest_utils import (
    GalaxyDataTestApp,
    GalaxyDataTestConfig,
)
from galaxy.structured_app import MinimalManagerApp


@pytest.mark.parametrize("state", [model.Job.states.STOPPING, model.Job.states.STOPPED])
def test_tracked_startup_includes_both_stop_phases(tmp_path, state):
    app = GalaxyDataTestApp(GalaxyDataTestConfig(root=str(tmp_path / "app")))
    session = cast(galaxy_scoped_session, app.model.session)
    try:
        job = model.Job()
        job.tool_id = "interactive_test"
        job.handler = "main.1"
        job.state = state
        session.add(job)
        session.commit()
        config = SimpleNamespace(server_name="main.1", user_activation_on=False)
        assert job in get_jobs_to_check_at_startup(session, True, config)
    finally:
        session.remove()
        app.model.engine.dispose()


@pytest.mark.parametrize("state", [model.Job.states.STOPPING, model.Job.states.STOPPED])
@pytest.mark.parametrize("assigned", [False, True])
@pytest.mark.parametrize("copied", [False, True])
def test_startup_does_not_readmit_stopping_jobs_without_sql_external_id(state, assigned, copied, monkeypatch):
    job = model.Job()
    job.tool_id = "interactive_test"
    job.state = state
    job.copied_from_job_id = 42 if copied else None
    job.job_runner_name = "engagequeue" if assigned else None
    handler = object.__new__(JobHandlerQueue)
    handler.app = Mock(spec=MinimalManagerApp, toolbox=Mock(has_tool=Mock(return_value=True)))
    recover = Mock()
    handler.dispatcher = Mock(
        spec=DefaultJobDispatcher,
        recover=recover,
        job_runners={"engagequeue": SimpleNamespace(recovers_without_external_id=True)},
    )
    handler.queue = Mock()
    wrapper = Mock(spec=JobWrapper)
    monkeypatch.setattr(handler, "_JobHandlerQueue__recover_job_wrapper", Mock(return_value=wrapper))
    handler._check_job_at_startup(job)
    handler.queue.put.assert_not_called()
    if assigned:
        assert job.state == state
        recover.assert_called_once_with(job, wrapper)
    else:
        assert job.state == model.Job.states.STOPPED
        recover.assert_not_called()


@pytest.mark.parametrize("found", [False, True])
def test_native_stopping_recovery_resolves_acceptance_without_fresh_admission(found, monkeypatch):
    job = model.Job()
    job.state = model.Job.states.STOPPING
    job.job_runner_external_id = None
    wrapper = SimpleNamespace(set_external_id=Mock())
    executor = SimpleNamespace(lookup=Mock(return_value=SimpleNamespace(id="accepted") if found else None))
    runner = EngageQueueJobRunner.__new__(EngageQueueJobRunner)
    stop_job, put, monitor_job, work_queue = Mock(), Mock(), Mock(), Mock()
    monkeypatch.setattr(runner, "stop_job", stop_job)
    monkeypatch.setattr(runner, "_record", Mock(return_value={"key": "galaxy:frozen"}))
    monkeypatch.setattr(runner, "_executor", Mock(return_value=(executor, "state", "interactive")))
    monkeypatch.setattr(runner, "put", put)
    runner.work_queue = work_queue
    monkeypatch.setattr(runner, "monitor_job", monitor_job)
    with patch("galaxy.jobs.runners.engagequeue.EngageQueueJobState") as state:
        runner.recover(job, wrapper)
        stop_job.assert_called_once_with(wrapper)
        executor.lookup.assert_called_once_with("galaxy:frozen")
        put.assert_not_called()
        work_queue.put.assert_not_called()
        if found:
            wrapper.set_external_id.assert_called_once_with("accepted")
            state.assert_called_once_with(wrapper, "accepted")
            monitor_job.assert_called_once_with(state.return_value)
        else:
            wrapper.set_external_id.assert_not_called()
            monitor_job.assert_not_called()
