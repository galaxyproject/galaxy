import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from galaxy import model
from galaxy.jobs.runners.engagequeue import (
    _normalize_interactive_exit_code,
    EngageQueueJobRunner,
    GRACEFUL_STOP_FILE,
    RECORD_FILE,
    STOP_FILE,
)


def stop_evidence(tmp_path, *, code=143, signal="TERM", oom=None):
    receipt_path = tmp_path / "receipt.json"
    expected = {
        "schema": 1,
        "job_id": "42",
        "key": "galaxy:attempt",
        "name": "tool",
        "label_key": "engagequeue.attempt",
        "label_value": "attempt",
    }
    marker = {
        **expected,
        "execution_id": "execution",
        "container_id": "a" * 64,
        "requested_while_terminal": False,
        "receipt_path": str(receipt_path),
    }
    receipt = {
        **expected,
        "job_id": "execution",
        "container_id": "a" * 64,
        "issued_signal": signal,
        "exit_code": code,
        "oom_killed": oom,
        "job_cancel_requested": False,
        "status": "stopped",
    }
    marker_path, hard_stop = tmp_path / "marker.json", tmp_path / "hard-stop.json"
    marker_path.write_text(json.dumps(marker))
    receipt_path.write_text(json.dumps(receipt))
    return expected, marker_path, hard_stop, marker, receipt


@pytest.mark.parametrize(
    "code,signal,oom,result",
    [
        (143, "TERM", None, 0),
        (143, "TERM", False, 0),
        (137, "KILL", False, 0),
        (137, "KILL", None, 137),
        (137, "KILL", True, 137),
        (137, "TERM", False, 137),
        (143, "KILL", False, 143),
        (143, "TERM", True, 143),
        (1, "TERM", False, 1),
    ],
)
def test_stop_exit_code_requires_matching_signal_and_safe_oom_evidence(tmp_path, code, signal, oom, result):
    expected, marker, hard_stop, _, _ = stop_evidence(tmp_path, code=code, signal=signal, oom=oom)
    assert _normalize_interactive_exit_code(marker, hard_stop, expected, code, timeout=0) == result


@pytest.mark.parametrize(
    "field,value",
    [
        ("container_id", "b" * 64),
        ("key", "galaxy:other"),
        ("name", "metadata"),
        ("job_id", "other"),
        ("label_value", "other"),
        ("job_cancel_requested", True),
        ("status", "pending"),
    ],
)
def test_receipt_with_wrong_identity_or_cancellation_cannot_normalize(tmp_path, field, value):
    expected, marker, hard_stop, data, receipt = stop_evidence(tmp_path)
    receipt[field] = value
    Path(data["receipt_path"]).write_text(json.dumps(receipt))
    assert _normalize_interactive_exit_code(marker, hard_stop, expected, 143, timeout=0) == 143


def test_hard_cancel_or_late_stop_wins_over_a_valid_receipt(tmp_path):
    expected, marker, hard_stop, data, _ = stop_evidence(tmp_path)
    hard_stop.touch()
    assert _normalize_interactive_exit_code(marker, hard_stop, expected, 143, timeout=0) == 143
    hard_stop.unlink()
    data["requested_while_terminal"] = True
    marker.write_text(json.dumps(data))
    assert _normalize_interactive_exit_code(marker, hard_stop, expected, 143, timeout=0) == 143


def test_missing_stop_evidence_retains_original_failure(tmp_path):
    expected, marker, hard_stop, data, _ = stop_evidence(tmp_path)
    Path(data["receipt_path"]).unlink()
    assert _normalize_interactive_exit_code(marker, hard_stop, expected, 143, timeout=0) == 143


def test_verified_receipt_resolves_an_initially_unobserved_container_id(tmp_path):
    expected, marker, hard_stop, data, _ = stop_evidence(tmp_path)
    data["container_id"] = None
    marker.write_text(json.dumps(data))
    assert _normalize_interactive_exit_code(marker, hard_stop, expected, 143, timeout=0) == 0


def test_matching_pending_marker_waits_for_identity_publication(tmp_path):
    expected, marker, hard_stop, data, _ = stop_evidence(tmp_path)
    pending = {**data, "requested_while_terminal": None, "receipt_path": None, "container_id": None}
    marker.write_text(json.dumps(pending))
    writer = threading.Timer(0.05, lambda: marker.write_text(json.dumps(data)))
    writer.start()
    try:
        assert _normalize_interactive_exit_code(marker, hard_stop, expected, 143, timeout=1) == 0
    finally:
        writer.join()


@pytest.mark.parametrize(
    "state,hard_cancel",
    [(model.Job.states.DELETING, False), (model.Job.states.DELETED, False), (model.Job.states.STOPPED, True)],
)
def test_deletion_and_hard_cancel_cannot_enter_graceful_finish(tmp_path, state, hard_cancel):
    record = {"schema": 1, "job_id": "42", "key": "galaxy:attempt", "interactive_container": "tool"}
    marker = {"schema": 1, "job_id": "42", "key": "galaxy:attempt", "name": "tool"}
    (tmp_path / RECORD_FILE).write_text(json.dumps(record))
    (tmp_path / GRACEFUL_STOP_FILE).write_text(json.dumps(marker))
    if hard_cancel:
        (tmp_path / STOP_FILE).touch()
    wrapper = SimpleNamespace(
        job_id=42,
        working_directory=str(tmp_path),
        get_state=lambda: state,
        tool=SimpleNamespace(produces_entry_points=True),
    )
    runner = object.__new__(EngageQueueJobRunner)
    assert runner._graceful_stop(wrapper) is None
