import errno
from types import MethodType
from unittest.mock import Mock

import pytest
from pydantic import TypeAdapter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from galaxy import model
from galaxy.jobs import JobWrapper
from galaxy.jobs.runners import (
    BaseJobRunner,
    JobState,
)
from galaxy.tool_util.output_checker import AnyJobMessage
from galaxy.tool_util.parser.stdio import StdioErrorLevel


class InMemoryJob(model.Job):
    def set_final_state(self, final_state):
        # Keep the state transition without updating workflow/collection rows in a database.
        self.set_state(final_state)


class InMemoryJobState(JobState):
    exit_code = 0
    cleanup_calls = 0

    def read_exit_code(self):
        return self.exit_code

    def cleanup(self):
        self.cleanup_calls += 1


@pytest.fixture
def finishing_job(tmp_path, request):
    job = getattr(request, "param", InMemoryJob)()
    job.id = 1
    job.state = job.states.RUNNING
    wrapper = Mock()
    wrapper.get_job.return_value = job
    wrapper.working_directory = str(tmp_path)
    wrapper.working_directory_exists.return_value = False
    wrapper.cleanup_job = "onsuccess"
    wrapper.outputs_to_working_directory = False
    wrapper.command_line = "tool command"
    wrapper.tool.stdio_regexes = []
    wrapper.tool.stdio_exit_codes = []
    wrapper.check_tool_output = MethodType(JobWrapper.check_tool_output, wrapper)
    wrapper.fail.side_effect = MethodType(JobWrapper.fail, wrapper)
    state = InMemoryJobState(wrapper, wrapper.job_destination)
    runner = object.__new__(BaseJobRunner)
    runner.sa_session = wrapper.sa_session
    runner.app = Mock()
    runner.runner_state_handlers = {"failure": [Mock()]}
    return runner, state, job


def finish(runner, state):
    runner._finish_or_resubmit_job(state, job_stdout="runner stdout", job_stderr="runner stderr")


@pytest.mark.parametrize("missing", [("stdout",), ("stderr",), ("stdout", "stderr")])
@pytest.mark.parametrize("exit_code", [0, 42])
@pytest.mark.parametrize("legacy_directory", [False, True])
def test_missing_streams_fail_with_diagnostics(finishing_job, tmp_path, missing, exit_code, legacy_directory):
    runner, state, job = finishing_job
    wrapper = state.job_wrapper
    state.exit_code = exit_code
    wrapper.tool.stdio_exit_codes = [
        Mock(range_start=1, range_end=255, error_level=StdioErrorLevel.FATAL, desc="Tool failed")
    ]
    output_dir = tmp_path if legacy_directory else tmp_path / "outputs"
    output_dir.mkdir(exist_ok=True)
    for stream in ("stdout", "stderr"):
        if stream not in missing:
            (output_dir / f"tool_{stream}").write_text(f"tool {stream}")

    finish(runner, state)

    assert job.state == job.states.ERROR
    assert job.exit_code == exit_code
    assert job.tool_stdout == ("" if "stdout" in missing else "tool stdout")
    assert job.tool_stderr == ("" if "stderr" in missing else "tool stderr")
    assert job.job_stdout == "runner stdout"
    assert job.job_stderr == "runner stderr"
    messages = job.job_messages
    errors = [message for message in messages if message["type"] == "stdio_read_error"]
    assert [message["stream"] for message in errors] == list(missing)
    for message in errors:
        assert message["errno"] == errno.ENOENT
        assert message["error_level"] == StdioErrorLevel.FATAL
        assert f"Job failed because the tool {message['stream']} file could not be read" in message["desc"]
        assert message["desc"] in job.info
    assert bool([message for message in messages if message["type"] == "exit_code"]) == bool(exit_code)
    # The public API's union must retain the structured fields when serializing.
    assert TypeAdapter(list[AnyJobMessage]).validate_python(messages) == messages
    wrapper.fail.assert_called_once()
    wrapper.finish.assert_not_called()
    assert state.cleanup_calls == 0
    wrapper.cleanup.assert_called_once_with(delete_files=False)
    runner.runner_state_handlers["failure"][0].assert_called_once_with(runner.app, runner, state)


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
@pytest.mark.parametrize("read_error", [False, True])
def test_unreadable_stream(finishing_job, tmp_path, monkeypatch, stream, read_error):
    runner, state, job = finishing_job
    for name in ("stdout", "stderr"):
        (tmp_path / f"tool_{name}").write_text(f"tool {name}")
    original_open = open
    original_read = runner._job_io_for_db

    def open_stream(path, mode):
        if str(path).endswith(f"tool_{stream}"):
            raise PermissionError(errno.EACCES, "Permission denied", path)
        return original_open(path, mode)

    def read_stream(stream_file):
        if stream_file.name.endswith(f"tool_{stream}"):
            raise OSError(errno.EIO, "Input/output error")
        return original_read(stream_file)

    if read_error:
        monkeypatch.setattr(runner, "_job_io_for_db", read_stream)
    else:
        monkeypatch.setattr("galaxy.jobs.runners.open", open_stream, raising=False)
    finish(runner, state)

    assert job.state == job.states.ERROR
    assert job.job_messages[0]["stream"] == stream
    assert job.job_messages[0]["errno"] == (errno.EIO if read_error else errno.EACCES)
    assert ("Input/output error" if read_error else "Permission denied") in job.info
    other_stream = "stderr" if stream == "stdout" else "stdout"
    assert getattr(job, f"tool_{other_stream}") == f"tool {other_stream}"


@pytest.mark.parametrize("job_state", [model.Job.states.DELETING, model.Job.states.DELETED])
def test_cancelled_job_without_streams(finishing_job, job_state):
    runner, state, job = finishing_job
    job.state = job_state

    finish(runner, state)

    assert job.state == job_state
    assert not job.job_messages
    state.job_wrapper.fail.assert_not_called()
    state.job_wrapper.finish.assert_called_once()
    assert state.job_wrapper.finish.call_args.args[:2] == ("", "Job cancelled")


def test_readable_empty_streams_finish_successfully(finishing_job, tmp_path):
    runner, state, job = finishing_job
    for stream in ("stdout", "stderr"):
        (tmp_path / f"tool_{stream}").touch()

    finish(runner, state)

    assert not job.job_messages
    state.job_wrapper.fail.assert_not_called()
    state.job_wrapper.finish.assert_called_once()
    assert state.cleanup_calls == 1
    runner.runner_state_handlers["failure"][0].assert_not_called()


def test_missing_stream_preserves_oom_resubmission(finishing_job, tmp_path):
    runner, state, job = finishing_job
    (tmp_path / "tool_stderr").write_text("Out of memory")
    state.job_wrapper.tool.stdio_regexes = [
        Mock(
            match="Out of memory",
            stderr_match=True,
            stdout_match=False,
            error_level=StdioErrorLevel.FATAL_OOM,
            desc=None,
        )
    ]

    def resubmit(app, runner, job_state):
        assert job_state.runner_state == JobState.runner_states.MEMORY_LIMIT_REACHED
        assert [message["type"] for message in job.job_messages] == ["regex", "stdio_read_error"]
        job_state.runner_state_handled = True

    runner.runner_state_handlers["failure"] = [resubmit]
    finish(runner, state)

    state.job_wrapper.fail.assert_not_called()
    state.job_wrapper.finish.assert_not_called()
    assert state.cleanup_calls == 0


@pytest.mark.parametrize("finishing_job", [model.Job], indirect=True)
def test_failure_diagnostics_survive_database_refresh(finishing_job, tmp_path):
    runner, state, job = finishing_job
    (tmp_path / "tool_stderr").write_text("Container failed to start")
    state.exit_code = 127
    engine = create_engine("sqlite:///:memory:")
    try:
        model.Base.metadata.create_all(engine)
        with Session(engine) as session:
            runner.sa_session = state.job_wrapper.sa_session = session
            session.add(job)
            session.commit()

            finish(runner, state)
            session.expire_all()

            assert job.state == job.states.ERROR
            assert job.exit_code == 127
            assert job.tool_stderr == "Container failed to start"
            assert job.job_stdout == "runner stdout"
            assert job.job_stderr == "runner stderr"
            assert job.job_messages[0]["type"] == "stdio_read_error"
            assert job.job_messages[0]["errno"] == errno.ENOENT
            assert job.job_messages[0]["desc"] == job.info
    finally:
        engine.dispose()
