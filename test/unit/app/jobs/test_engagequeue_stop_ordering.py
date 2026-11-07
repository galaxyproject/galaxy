"""Stop intent remains durable and monotonic across independent callbacks."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from galaxy import model
from galaxy.exceptions import ConfigurationError
from galaxy.jobs.runners import engagequeue as module
from galaxy.jobs.runners.engagequeue import (
    _read_json,
    EngageQueueJobRunner,
    GRACEFUL_STOP_FILE,
    RECORD_FILE,
    STOP_FILE,
)


@pytest.fixture
def attempt(tmp_path, monkeypatch):
    record = {"schema": 1, "job_id": "17", "key": "galaxy:frozen-attempt", "interactive_container": "tool-service"}
    (tmp_path / RECORD_FILE).write_text(json.dumps(record))
    job = SimpleNamespace(job_runner_external_id=None)
    wrapper = SimpleNamespace(
        job_id=17,
        working_directory=str(tmp_path),
        state=model.Job.states.STOPPING,
        tool=SimpleNamespace(produces_entry_points=True),
    )
    wrapper.get_state = lambda: wrapper.state
    wrapper.get_job = lambda: job
    executor = SimpleNamespace(
        lookup=Mock(return_value=SimpleNamespace(id="accepted-execution")),
        status=Mock(return_value=SimpleNamespace(terminal=False)),
        inspect=Mock(
            return_value={
                "spec": {"containers": [{"name": "tool-service"}, {"name": "metadata-service"}]},
                "owned_container_ids": ["a" * 64, "b" * 64],
            }
        ),
        container_stop_receipt_path=Mock(return_value=str(tmp_path / "sdk-receipt.json")),
        stop_container=Mock(),
        cancel=Mock(),
    )
    runner = EngageQueueJobRunner.__new__(EngageQueueJobRunner)
    monkeypatch.setattr(runner, "_executor", Mock(return_value=(executor, str(tmp_path / "sdk"), "interactive")))
    expected = {
        **{key: record[key] for key in ("schema", "job_id", "key")},
        "name": "tool-service",
        "label_key": "engagequeue.attempt",
        "label_value": "frozen-attempt",
    }
    complete = {
        "execution_id": "accepted-execution",
        "receipt_path": str(tmp_path / "sdk-receipt.json"),
        "requested_while_terminal": False,
        "container_id": "a" * 64,
    }
    return SimpleNamespace(
        root=tmp_path, wrapper=wrapper, job=job, executor=executor, runner=runner, expected=expected, complete=complete
    )


@pytest.mark.parametrize("found", [False, True])
def test_normal_stop_without_sql_external_id_keeps_graceful_intent(attempt, found):
    attempt.executor.lookup.return_value = SimpleNamespace(id="accepted-execution") if found else None
    attempt.runner.stop_job(attempt.wrapper)
    marker = _read_json(attempt.root / GRACEFUL_STOP_FILE)
    assert marker is not None
    assert all(marker[key] == value for key, value in attempt.expected.items())
    assert not (attempt.root / STOP_FILE).exists()
    assert attempt.job.job_runner_external_id is None  # No SQL write under stop serialization.
    attempt.executor.cancel.assert_not_called()
    if found:
        assert marker["requested_while_terminal"] is False
        assert marker["container_id"] == "a" * 64
        attempt.executor.stop_container.assert_called_once_with("accepted-execution", "tool-service")
    else:
        assert marker["execution_id"] is None and marker["requested_while_terminal"] is None
        attempt.executor.stop_container.assert_not_called()


@pytest.mark.parametrize("reset_state", [model.Job.states.NEW, model.Job.states.QUEUED])
def test_durable_pending_stop_is_completed_after_startup_state_reset(attempt, reset_state):
    attempt.executor.lookup.return_value = None
    attempt.runner.stop_job(attempt.wrapper)
    attempt.wrapper.state = reset_state
    attempt.executor.lookup.return_value = SimpleNamespace(id="accepted-execution")
    attempt.runner.stop_job(attempt.wrapper)
    marker = _read_json(attempt.root / GRACEFUL_STOP_FILE)
    assert marker is not None
    assert marker["execution_id"] == "accepted-execution" and marker["requested_while_terminal"] is False
    assert marker["container_id"] == "a" * 64
    assert not (attempt.root / STOP_FILE).exists()
    attempt.executor.stop_container.assert_called_once_with("accepted-execution", "tool-service")
    attempt.executor.cancel.assert_not_called()


def test_duplicate_terminal_callback_does_not_reclassify_original_stop_as_late(attempt):
    attempt.runner.stop_job(attempt.wrapper)
    original = _read_json(attempt.root / GRACEFUL_STOP_FILE)
    attempt.executor.status.return_value = SimpleNamespace(terminal=True)
    attempt.executor.inspect.return_value["owned_container_ids"] = [None, None]
    attempt.runner.stop_job(attempt.wrapper)
    assert _read_json(attempt.root / GRACEFUL_STOP_FILE) == original
    attempt.executor.stop_container.assert_called_once()
    attempt.executor.cancel.assert_not_called()


@pytest.mark.parametrize("terminal", [False, True])
def test_late_pending_publication_cannot_downgrade_a_finalized_marker(attempt, terminal):
    finalized = {**attempt.complete, "requested_while_terminal": terminal}
    expected = attempt.runner._publish_graceful_stop(attempt.root, attempt.expected, finalized)
    actual = attempt.runner._publish_graceful_stop(
        attempt.root,
        attempt.expected,
        {
            "execution_id": None,
            "receipt_path": None,
            "container_id": None,
            "requested_while_terminal": None,
        },
    )
    assert actual == expected == _read_json(attempt.root / GRACEFUL_STOP_FILE)


def test_pending_and_completed_publication_are_serialized(attempt, monkeypatch):
    pending_entered, release_pending, completing, completed = Event(), Event(), Event(), Event()
    write = module._write_json

    def gate_first_pending(path, marker):
        if marker["requested_while_terminal"] is None and not pending_entered.is_set():
            pending_entered.set()
            assert release_pending.wait(5)
        write(path, marker)

    def finish_publication():
        completing.set()
        result = attempt.runner._publish_graceful_stop(attempt.root, attempt.expected, attempt.complete)
        completed.set()
        return result

    monkeypatch.setattr(module, "_write_json", gate_first_pending)
    with ThreadPoolExecutor(max_workers=2) as threads:
        pending = threads.submit(attempt.runner._publish_graceful_stop, attempt.root, attempt.expected)
        try:
            assert pending_entered.wait(5)
            finished = threads.submit(finish_publication)
            assert completing.wait(5)
            assert not completed.wait(0.2)
        finally:
            release_pending.set()
        pending.result(timeout=5)
        finished.result(timeout=5)
    marker = _read_json(attempt.root / GRACEFUL_STOP_FILE)
    assert marker is not None
    assert marker["requested_while_terminal"] is False and marker["container_id"] == "a" * 64


def test_a_different_frozen_attempt_cannot_replace_existing_stop_intent(attempt):
    attempt.runner._publish_graceful_stop(attempt.root, attempt.expected, attempt.complete)
    with pytest.raises(ConfigurationError, match="different attempt"):
        attempt.runner._publish_graceful_stop(attempt.root, {**attempt.expected, "key": "galaxy:foreign"})


@pytest.mark.parametrize(
    "state,hard_marker",
    [
        (model.Job.states.DELETING, False),
        (model.Job.states.DELETED, False),
        (model.Job.states.STOPPING, True),
        (model.Job.states.STOPPED, True),
    ],
)
def test_deletion_and_hard_stop_have_priority_over_existing_graceful_intent(attempt, state, hard_marker):
    attempt.runner._publish_graceful_stop(attempt.root, attempt.expected, attempt.complete)
    attempt.wrapper.state = state
    if hard_marker:
        (attempt.root / STOP_FILE).write_text(json.dumps({"job_id": "17"}))
    attempt.runner.stop_job(attempt.wrapper)
    assert (attempt.root / STOP_FILE).exists()
    attempt.executor.cancel.assert_called_once_with("accepted-execution")
    attempt.executor.stop_container.assert_not_called()


@pytest.mark.parametrize("deleting", [False, True])
def test_hard_stop_arriving_during_snapshot_takes_priority_before_targeted_signal(attempt, deleting):
    snapshot = attempt.executor.inspect.return_value

    def hard_request(_):
        if deleting:
            attempt.wrapper.state = model.Job.states.DELETING
        else:
            (attempt.root / STOP_FILE).write_text(json.dumps({"job_id": "17"}))
        return snapshot

    attempt.executor.inspect.side_effect = hard_request
    attempt.runner.stop_job(attempt.wrapper)
    assert (attempt.root / STOP_FILE).exists()
    attempt.executor.cancel.assert_called_once_with("accepted-execution")
    attempt.executor.stop_container.assert_not_called()
