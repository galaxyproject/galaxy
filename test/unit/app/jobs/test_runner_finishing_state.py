"""Tests for the FINISHING job state opt-in on job runners.

``_handle_metadata_externally`` is shared by every runner, but only runners whose
``recover()`` understands FINISHING may mark a job with it - otherwise
``get_jobs_to_check_at_startup`` hands the job back to a ``recover()`` that drops it
on the floor, wedging it out of every non-terminal state.
"""

from types import SimpleNamespace
from unittest.mock import patch

from galaxy import model
from galaxy.jobs.runners import BaseJobRunner
from galaxy.jobs.runners.local import LocalJobRunner
from galaxy.jobs.runners.pulsar import (
    PulsarCoexecutionJobRunner,
    PulsarEmbeddedJobRunner,
    PulsarJobRunner,
    PulsarKubernetesJobRunner,
    PulsarLegacyJobRunner,
    PulsarMQJobRunner,
    PulsarRESTJobRunner,
    PulsarTesJobRunner,
)

PULSAR_RUNNERS = [
    PulsarJobRunner,
    PulsarLegacyJobRunner,
    PulsarMQJobRunner,
    PulsarCoexecutionJobRunner,
    PulsarKubernetesJobRunner,
    PulsarTesJobRunner,
    PulsarRESTJobRunner,
    PulsarEmbeddedJobRunner,
]


class MockJobWrapper:
    """Only the surface ``_handle_metadata_externally`` touches on the celery path."""

    def __init__(self):
        self.job_id = 1
        self.working_directory = "/tmp/job_working_directory"
        self.metadata_strategy = "extended_celery"
        self.job_io = SimpleNamespace(get_output_fnames=lambda: [])
        self.states_set = []
        self.failures = []

    def get_state(self):
        return model.Job.states.RUNNING

    def setup_external_metadata(self, **kwds):
        return "set_metadata.sh"

    def change_state(self, state, **kwds):
        self.states_set.append(state)

    def fail(self, message, **kwds):
        self.failures.append(message)


def _runner(runner_class):
    # Bypass __init__ - it wants a full app - and supply only what
    # _verify_celery_config reads.
    runner = object.__new__(runner_class)
    runner.app = SimpleNamespace(
        config=SimpleNamespace(enable_celery_tasks=True, celery_conf={"result_backend": "redis://localhost"})
    )
    return runner


def test_base_job_runner_does_not_recover_finishing_jobs():
    assert BaseJobRunner.recovers_finishing_jobs is False


def test_local_job_runner_does_not_recover_finishing_jobs():
    # LocalJobRunner.recover() has no FINISHING branch; it must inherit the opt-out.
    assert LocalJobRunner.recovers_finishing_jobs is False


def test_pulsar_job_runners_recover_finishing_jobs():
    for runner_class in PULSAR_RUNNERS:
        assert runner_class.recovers_finishing_jobs is True, runner_class.__name__


@patch("galaxy.celery.tasks.set_job_metadata")
def test_handle_metadata_externally_skips_finishing_for_non_recovering_runner(set_job_metadata):
    job_wrapper = MockJobWrapper()
    BaseJobRunner._handle_metadata_externally(_runner(BaseJobRunner), job_wrapper)
    assert job_wrapper.states_set == []


@patch("galaxy.celery.tasks.set_job_metadata")
def test_handle_metadata_externally_marks_finishing_for_recovering_runner(set_job_metadata):
    job_wrapper = MockJobWrapper()
    BaseJobRunner._handle_metadata_externally(_runner(PulsarJobRunner), job_wrapper)
    assert job_wrapper.states_set == [model.Job.states.FINISHING]


class RecordingQueue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


def test_recover_queues_the_tail_not_the_whole_finish_job():
    """The remote job is already cleaned by the time FINISHING is set, so re-entering
    finish_job would query a job Pulsar no longer has."""
    runner = _runner(PulsarJobRunner)
    runner.work_queue = RecordingQueue()
    job = SimpleNamespace(
        id=1,
        get_state=lambda: model.Job.states.FINISHING,
        get_command_line=lambda: "echo hello",
    )
    job_wrapper = MockJobWrapper()
    job_state = object()
    with patch.object(PulsarJobRunner, "_job_state", return_value=job_state):
        PulsarJobRunner.recover(runner, job, job_wrapper)
    assert runner.work_queue.items == [(runner._finish_staged_job, job_state)]


def test_finish_staged_job_recovers_inputs_from_working_directory(tmp_path):
    runner = _runner(PulsarJobRunner)
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "tool_stdout").write_text("the stdout")
    (tmp_path / "outputs" / "tool_stderr").write_text("the stderr")
    (tmp_path / "galaxy_1.ec").write_text("0\n")
    job_wrapper = MockJobWrapper()
    job_wrapper.working_directory = str(tmp_path)
    completed = []
    with patch.object(PulsarJobRunner, "_complete_staged_job", lambda self, *args, **kwds: completed.append(args)):
        runner._finish_staged_job(SimpleNamespace(job_wrapper=job_wrapper))
    assert completed == [(job_wrapper, "the stdout", "the stderr", 0)]
    assert job_wrapper.failures == []


def test_finish_staged_job_fails_loudly_without_an_exit_code(tmp_path):
    """The exit code file is written immediately before the metadata step, so its absence
    means the job never reached FINISHING - finishing on a guessed code would be worse."""
    runner = _runner(PulsarJobRunner)
    job_wrapper = MockJobWrapper()
    job_wrapper.working_directory = str(tmp_path)
    completed = []
    with patch.object(PulsarJobRunner, "_complete_staged_job", lambda self, *args, **kwds: completed.append(args)):
        runner._finish_staged_job(SimpleNamespace(job_wrapper=job_wrapper))
    assert completed == []
    assert job_wrapper.failures == ["Unable to recover job interrupted while setting metadata"]
