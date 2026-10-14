import os
import signal
import threading
from typing import (
    cast,
    TYPE_CHECKING,
)
from unittest.mock import MagicMock

import psutil
import pytest

from galaxy import job_metrics
from galaxy.app_unittest_utils.job_runner_support import MockJobWrapper
from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.job_execution.output_collect import default_exit_code_file
from galaxy.jobs import MinimalJobWrapper
from galaxy.jobs.runners import local
from galaxy.util.unittest import TestCase

if TYPE_CHECKING:
    from sqlalchemy.orm import scoped_session


class TestLocalJobRunner(TestCase, UsesTools):
    def setUp(self):
        self.setup_app()
        self._init_tool()
        self.app.job_metrics = job_metrics.JobMetrics()
        self.job_wrapper = MockJobWrapper(self.app, self.test_directory, self.tool)

    def tearDown(self):
        self.tear_down_app()

    def test_run(self, caplog):
        self.job_wrapper.command_line = "echo HelloWorld"
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))
        assert self.job_wrapper.stdout.strip() == "HelloWorld"
        assert any("return code: 0" in message for message in caplog.messages)
        assert not any(record.name == local.log.name and record.levelname == "ERROR" for record in caplog.records)

    def test_early_process_exit_is_logged(self, caplog):
        self.job_wrapper.dependency_shell_commands = ["echo setup stdout", "echo setup stderr >&2", "exit 7"]
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))

        assert not os.path.exists(default_exit_code_file(self.job_wrapper.working_directory, "1"))
        assert any("(1) execution finished:" in message and "return code: 7" in message for message in caplog.messages)
        assert any(
            record.levelname == "ERROR" and record.message == "(1) job process exited with return code 7"
            for record in caplog.records
        )
        assert not any("killed by signal" in message for message in caplog.messages)
        assert self.job_wrapper.exit_code == 7
        assert self.job_wrapper.fail_message == "job process exited with return code 7"
        assert self.job_wrapper.fail_exception is False
        assert self.job_wrapper.job_stdout == "setup stdout\n"
        assert self.job_wrapper.job_stderr == "setup stderr\njob process exited with return code 7"

    @pytest.mark.parametrize("has_limits", [False, True])
    def test_signal_death_before_job_script_outputs_is_logged(self, caplog, has_limits):
        self.job_wrapper.dependency_shell_commands = ["kill -TERM $$"]
        self.job_wrapper.job_destination.params["embed_metadata_in_job"] = False
        if has_limits:
            self.tool.timelimit = 60
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))

        assert not os.path.exists(default_exit_code_file(self.job_wrapper.working_directory, "1"))
        assert not os.path.exists(os.path.join(self.job_wrapper.working_directory, "outputs", "tool_stdout"))
        assert any(f"return code: {-signal.SIGTERM}" in message for message in caplog.messages)
        assert any(
            record.levelname == "ERROR" and record.message == f"(1) job process was killed by signal {signal.SIGTERM}"
            for record in caplog.records
        )
        assert self.job_wrapper.exit_code == -signal.SIGTERM
        assert self.job_wrapper.fail_message == f"job process was killed by signal {signal.SIGTERM}"
        assert self.job_wrapper.job_stderr == self.job_wrapper.fail_message
        assert self.job_wrapper.fail_exception is False
        assert not os.path.exists(self.job_wrapper.mock_metadata_path)

    def test_signal_after_tool_exit_preserves_tool_exit_code(self):
        self.job_wrapper.command_line = '''sh -c "exit 4"'''
        self.job_wrapper.metadata_command = "kill -TERM $$"
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))

        assert self.job_wrapper.exit_code == 4
        assert not hasattr(self.job_wrapper, "fail_message")

    def test_galaxy_lib_on_path(self):
        self.job_wrapper.command_line = '''python -c "import galaxy.util"'''
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))
        assert self.job_wrapper.exit_code == 0

    def test_default_slots(self):
        self.job_wrapper.command_line = """echo $GALAXY_SLOTS"""
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))
        assert self.job_wrapper.stdout.strip() == "1"

    def test_slots_override(self):
        # Set local_slots in job destination to specify slots for
        # local job runner.
        self.job_wrapper.job_destination.params["local_slots"] = 3
        self.job_wrapper.command_line = """echo $GALAXY_SLOTS"""
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))
        assert self.job_wrapper.stdout.strip() == "3"

    def test_exit_code(self):
        self.job_wrapper.command_line = '''sh -c "exit 4"'''
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))
        assert self.job_wrapper.exit_code == 4

    def test_metadata_gets_set(self):
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))
        assert os.path.exists(self.job_wrapper.mock_metadata_path)

    def test_metadata_gets_set_if_embedded(self):
        self.job_wrapper.job_destination.params["embed_metadata_in_job"] = "True"

        # Kill off cruft for _handle_metadata_externally and make sure job still works...
        self.job_wrapper.external_output_metadata = None
        self.app.datatypes_registry.set_external_metadata_tool = None

        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))
        assert os.path.exists(self.job_wrapper.mock_metadata_path)

    def test_stopping_job(self):
        self.job_wrapper.command_line = '''python -c "import time; time.sleep(15)"'''
        runner = local.LocalJobRunner(self.app, 1)

        def queue():
            runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))

        t = threading.Thread(target=queue)
        t.start()
        external_id = self.job_wrapper.wait_for_external_id()
        assert psutil.pid_exists(external_id)
        runner.stop_job(self.job_wrapper)
        t.join(1)
        assert not psutil.pid_exists(external_id)

    def test_shutdown_no_jobs(self):
        self.app.config.monitor_thread_join_timeout = 5
        runner = local.LocalJobRunner(self.app, 1)
        runner.start()
        runner.shutdown()

    def test_stopping_job_at_shutdown(self):
        self.job_wrapper.command_line = '''python -c "import time; time.sleep(15)"'''
        self.app.model.session = cast("scoped_session", MagicMock())
        runner = local.LocalJobRunner(self.app, 1)
        runner.start()
        self.app.config.monitor_thread_join_timeout = 15

        def queue():
            runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))

        t = threading.Thread(target=queue)
        t.start()
        external_id = self.job_wrapper.wait_for_external_id()
        assert psutil.pid_exists(external_id)
        runner.shutdown()
        t.join(1)
        assert not psutil.pid_exists(external_id)
        assert "job terminated by Galaxy shutdown" in self.job_wrapper.fail_message

    def test_timelimit_kills_job(self):
        self.tool.timelimit = 3
        self.job_wrapper.command_line = '''python -c "import time; time.sleep(30)"'''
        runner = local.LocalJobRunner(self.app, 1)

        def queue():
            runner.queue_job(cast(MinimalJobWrapper, self.job_wrapper))

        t = threading.Thread(target=queue)
        t.start()
        external_id = self.job_wrapper.wait_for_external_id()
        assert external_id is not None
        assert psutil.pid_exists(external_id)
        t.join(30)
        assert not t.is_alive(), "Job was not killed by timelimit"
        assert not psutil.pid_exists(external_id)
        assert hasattr(self.job_wrapper, "fail_message")
        assert "time limit" in self.job_wrapper.fail_message
