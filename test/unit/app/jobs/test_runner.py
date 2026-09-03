import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from galaxy import model
from galaxy.celery import tasks
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    BaseJobRunner,
)


class RecordingAsynchronousJobRunner(AsynchronousJobRunner):
    def _handle_metadata_externally(self, job_wrapper, resolve_requirements=False):
        self.calls.append(("metadata", job_wrapper, resolve_requirements))

    def _finish_job(self, job_state):
        self.calls.append(("finish", job_state))


@pytest.mark.parametrize(
    ("always_external", "embed_metadata", "expected_call_names"),
    [
        (False, True, ["finish"]),
        (False, False, ["metadata", "finish"]),
        (True, True, ["metadata", "finish"]),
    ],
)
def test_asynchronous_finish_job_metadata_handling(always_external, embed_metadata, expected_call_names):
    runner = object.__new__(RecordingAsynchronousJobRunner)
    runner.always_handle_metadata_externally = always_external
    runner.calls = []
    job_wrapper = SimpleNamespace(job_destination=SimpleNamespace(params={"embed_metadata_in_job": embed_metadata}))
    job_state = SimpleNamespace(job_wrapper=job_wrapper)

    runner.finish_job(job_state)

    assert [call[0] for call in runner.calls] == expected_call_names
    if "metadata" in expected_call_names:
        assert runner.calls[0] == ("metadata", job_wrapper, True)


def test_celery_metadata_dispatch_is_logged(caplog, monkeypatch, tmp_path):
    runner = object.__new__(BaseJobRunner)
    monkeypatch.setattr(runner, "_verify_celery_config", lambda: None)
    async_result = Mock()

    def delay(**kwargs):
        assert "Dispatching external metadata execution to celery for job: 42" in caplog.messages
        assert kwargs == {
            "tool_job_working_directory": str(tmp_path),
            "job_id": 42,
            "extended_metadata_collection": True,
        }
        return async_result

    monkeypatch.setattr(tasks.set_job_metadata, "delay", delay)
    job_wrapper = SimpleNamespace(
        get_state=lambda: model.Job.states.RUNNING,
        setup_external_metadata=lambda **kwargs: "set-metadata",
        job_io=SimpleNamespace(get_output_fnames=lambda: []),
        metadata_strategy="celery_extended",
        working_directory=str(tmp_path),
        job_id=42,
    )

    with caplog.at_level(logging.DEBUG, logger="galaxy.jobs.runners"):
        runner._handle_metadata_externally(job_wrapper)

    async_result.get.assert_called_once_with()
