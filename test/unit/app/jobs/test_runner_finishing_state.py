"""Focused unit coverage for the Pulsar FINISHING recovery boundary."""

import os
from queue import Queue
from typing import (
    cast,
    TYPE_CHECKING,
)

from galaxy import model
from galaxy.app_unittest_utils.job_runner_support import MockJobWrapper
from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.jobs import MinimalJobWrapper
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
from galaxy.util.unittest import TestCase

if TYPE_CHECKING:
    from queue import Queue as TypedQueue

    from galaxy.jobs.runners import AsynchronousJobState


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


def test_only_pulsar_runners_opt_into_finishing_recovery():
    assert BaseJobRunner.recovers_finishing_jobs is False
    assert LocalJobRunner.recovers_finishing_jobs is False
    for runner_class in PULSAR_RUNNERS:
        assert runner_class.recovers_finishing_jobs is True, runner_class.__name__


class TestPulsarFinishingRecovery(TestCase, UsesTools):
    def setUp(self):
        self.setup_app()
        self._init_tool()
        self.job_wrapper = MockJobWrapper(self.app, self.test_directory, self.tool)
        self.runner = object.__new__(PulsarJobRunner)
        self.runner.app = self.app
        self.runner.work_queue = cast("TypedQueue[tuple]", Queue())

    def tearDown(self):
        self.tear_down_app()

    def test_recover_queues_only_the_already_staged_tail(self):
        job = self.job_wrapper.job
        job.state = model.Job.states.FINISHING

        self.runner.recover(job, cast(MinimalJobWrapper, self.job_wrapper))

        method, job_state = self.runner.work_queue.get_nowait()
        assert method == self.runner._finish_staged_job
        assert job_state.job_wrapper is self.job_wrapper

    def test_finish_staged_job_uses_local_exit_code_and_streams(self):
        outputs_directory = os.path.join(self.job_wrapper.working_directory, "outputs")
        os.makedirs(outputs_directory)
        with open(os.path.join(outputs_directory, "tool_stdout"), "w") as stdout:
            stdout.write("the stdout")
        with open(os.path.join(outputs_directory, "tool_stderr"), "w") as stderr:
            stderr.write("the stderr")
        with open(
            os.path.join(self.job_wrapper.working_directory, f"galaxy_{self.job_wrapper.job_id}.ec"), "w"
        ) as exit_code:
            exit_code.write("0\n")

        self.runner._finish_staged_job(self._job_state())

        assert self.job_wrapper.stdout == "the stdout"
        assert self.job_wrapper.stderr == "the stderr"
        assert self.job_wrapper.exit_code == 0
        assert os.path.exists(self.job_wrapper.mock_metadata_path)

    def test_finish_staged_job_fails_without_an_exit_code(self):
        self.runner._finish_staged_job(self._job_state())

        assert self.job_wrapper.fail_message == "Unable to recover job interrupted while setting metadata"
        assert not hasattr(self.job_wrapper, "exit_code")

    def _job_state(self) -> "AsynchronousJobState":
        return self.runner._job_state(self.job_wrapper.job, cast(MinimalJobWrapper, self.job_wrapper))
