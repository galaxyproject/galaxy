"""Missing-ID recovery preserves Stop and each runner's admission contract."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from galaxy import model
from galaxy.jobs.handler import JobHandlerQueue
from galaxy.jobs.runners.engagequeue import (
    EngageQueueJobRunner,
    RECORD_FILE,
)


def setup_handler(runner_name, state, monkeypatch):
    job = model.Job()
    job.tool_id = "legacy_stop_test"
    job.state = state
    job.job_runner_name = runner_name
    job.job_runner_external_id = None
    wrapper = object()
    runner = SimpleNamespace(recovers_without_external_id=False, put=Mock(), stop_job=Mock())
    # Actual DRMAA, CLI and Kubernetes recovery takes this admission path when
    # no external ID exists. A generic startup fix must not invoke it on Stop.
    runner.recover = Mock(side_effect=lambda job, wrapper: runner.put(wrapper))
    dispatcher = SimpleNamespace(
        job_runners={runner_name: runner},
        recover=Mock(side_effect=lambda job, wrapper: runner.recover(job, wrapper)),
        stop=Mock(side_effect=lambda job, wrapper: runner.stop_job(wrapper)),
    )
    handler = JobHandlerQueue.__new__(JobHandlerQueue)
    monkeypatch.setattr(
        handler, "app", SimpleNamespace(toolbox=SimpleNamespace(has_tool=Mock(return_value=True))), raising=False
    )
    monkeypatch.setattr(handler, "dispatcher", dispatcher, raising=False)
    handler.track_jobs_in_database = True
    handler.queue = Mock()
    monkeypatch.setattr(handler, "job_wrapper", Mock(return_value=wrapper))
    monkeypatch.setattr(handler, "_JobHandlerQueue__recover_job_wrapper", Mock(return_value=wrapper), raising=False)
    return job, handler, dispatcher, runner, wrapper


@pytest.mark.parametrize("runner_name", ["drmaa", "cli", "k8s"])
@pytest.mark.parametrize("state", [model.Job.states.STOPPING, model.Job.states.STOPPED])
def test_legacy_no_id_stop_dispatches_stop_without_recovery_or_new_admission(runner_name, state, monkeypatch):
    job, handler, dispatcher, runner, wrapper = setup_handler(runner_name, state, monkeypatch)
    handler._check_job_at_startup(job)
    assert job.state == model.Job.states.STOPPED
    assert job.job_runner_name == runner_name
    dispatcher.recover.assert_not_called()
    runner.recover.assert_not_called()
    runner.put.assert_not_called()
    handler.queue.put.assert_not_called()
    dispatcher.stop.assert_called_once_with(job, wrapper)
    runner.stop_job.assert_called_once_with(wrapper)


def test_legacy_queued_job_keeps_existing_no_id_startup_fallback(monkeypatch):
    job, handler, dispatcher, runner, _ = setup_handler("drmaa", model.Job.states.QUEUED, monkeypatch)
    handler._check_job_at_startup(job)
    assert job.state == model.Job.states.NEW and job.job_runner_name is None
    dispatcher.recover.assert_not_called()
    dispatcher.stop.assert_not_called()
    runner.put.assert_not_called()


@pytest.mark.parametrize("state", [model.Job.states.QUEUED, model.Job.states.RUNNING, model.Job.states.FINISHING])
def test_native_assigned_no_id_recovery_queues_frozen_lookup_without_fresh_admission(tmp_path, state, monkeypatch):
    job = model.Job()
    job.id = 17
    job.state = state
    job.job_runner_external_id = None
    wrapper = SimpleNamespace(job_id=17, working_directory=str(tmp_path), get_job=lambda: job)
    (tmp_path / RECORD_FILE).write_text(json.dumps({"schema": 1, "job_id": "17", "key": "galaxy:frozen"}))
    runner = EngageQueueJobRunner.__new__(EngageQueueJobRunner)
    runner.work_queue = Mock()
    put = Mock()
    monkeypatch.setattr(runner, "put", put)
    runner.recover(job, wrapper)
    put.assert_not_called()
    runner.work_queue.put.assert_called_once_with((runner.queue_job, wrapper))
    assert job.state == state


@pytest.mark.parametrize("state", [model.Job.states.NEW, model.Job.states.RESUBMITTED])
def test_native_genuinely_new_attempt_retains_fresh_admission_path(tmp_path, state, monkeypatch):
    job = model.Job()
    job.state = state
    job.job_runner_external_id = None
    wrapper = SimpleNamespace(job_id=17, working_directory=str(tmp_path), get_job=lambda: job)
    runner = EngageQueueJobRunner.__new__(EngageQueueJobRunner)
    runner.work_queue = Mock()
    put = Mock()
    monkeypatch.setattr(runner, "put", put)
    runner.recover(job, wrapper)
    put.assert_called_once_with(wrapper)
    runner.work_queue.put.assert_not_called()
