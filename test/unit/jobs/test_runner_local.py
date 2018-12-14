import os
import threading
import time
from unittest import TestCase

import psutil

from galaxy import model
from galaxy.jobs import metrics
from galaxy.jobs.runners import local
from galaxy.util import bunch
from ..tools_support import (
    UsesApp,
    UsesTools
)


class TestLocalJobRunner(TestCase, UsesApp, UsesTools):

    def setUp(self):
        self.setup_app()
        self._init_tool()
        self.app.job_metrics = metrics.JobMetrics()
        self.job_wrapper = MockJobWrapper(self.app, self.test_directory, self.tool)

    def tearDown(self):
        self.tear_down_app()

    def test_run(self):
        self.job_wrapper.command_line = "echo HelloWorld"
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(self.job_wrapper)
        assert self.job_wrapper.stdout.strip() == "HelloWorld"

    def test_galaxy_lib_on_path(self):
        self.job_wrapper.command_line = '''python -c "import galaxy.util"'''
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(self.job_wrapper)
        assert self.job_wrapper.exit_code == 0

    def test_default_slots(self):
        self.job_wrapper.command_line = '''echo $GALAXY_SLOTS'''
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(self.job_wrapper)
        assert self.job_wrapper.stdout.strip() == "1"

    def test_slots_override(self):
        # Set local_slots in job destination to specify slots for
        # local job runner.
        self.job_wrapper.job_destination.params["local_slots"] = 3
        self.job_wrapper.command_line = '''echo $GALAXY_SLOTS'''
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(self.job_wrapper)
        assert self.job_wrapper.stdout.strip() == "3"

    def test_exit_code(self):
        self.job_wrapper.command_line = '''sh -c "exit 4"'''
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(self.job_wrapper)
        assert self.job_wrapper.exit_code == 4

    def test_metadata_gets_set(self):
        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(self.job_wrapper)
        assert os.path.exists(self.job_wrapper.mock_metadata_path)

    def test_metadata_gets_set_if_embedded(self):
        self.job_wrapper.job_destination.params["embed_metadata_in_job"] = "True"

        # Kill off cruft for _handle_metadata_externally and make sure job stil works...
        self.job_wrapper.external_output_metadata = None
        self.app.datatypes_registry.set_external_metadata_tool = None

        runner = local.LocalJobRunner(self.app, 1)
        runner.queue_job(self.job_wrapper)
        assert os.path.exists(self.job_wrapper.mock_metadata_path)

    def test_stopping_job(self):
        self.job_wrapper.command_line = '''python -c "import time; time.sleep(15)"'''
        runner = local.LocalJobRunner(self.app, 1)

        def queue():
            runner.queue_job(self.job_wrapper)

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
        runner.shutdown()

    def test_stopping_job_at_shutdown(self):
        self.job_wrapper.command_line = '''python -c "import time; time.sleep(15)"'''
        runner = local.LocalJobRunner(self.app, 1)
        self.app.config.monitor_thread_join_timeout = 15

        def queue():
            runner.queue_job(self.job_wrapper)

        t = threading.Thread(target=queue)
        t.start()
        external_id = self.job_wrapper.wait_for_external_id()
        assert psutil.pid_exists(external_id)
        runner.shutdown()
        t.join(1)
        assert not psutil.pid_exists(external_id)
        assert "job terminated by Galaxy shutdown" in self.job_wrapper.fail_message


class MockJobWrapper(object):

    def __init__(self, app, test_directory, tool):
        working_directory = os.path.join(test_directory, "workdir")
        tool_working_directory = os.path.join(working_directory, "working")
        os.makedirs(tool_working_directory)
        self.app = app
        self.tool = tool
        self.requires_containerization = False
        self.state = model.Job.states.QUEUED
        self.command_line = "echo HelloWorld"
        self.environment_variables = []
        self.commands_in_new_shell = False
        self.prepare_called = False
        self.write_version_cmd = None
        self.dependency_shell_commands = None
        self.working_directory = working_directory
        self.tool_working_directory = tool_working_directory
        self.requires_setting_metadata = True
        self.job_destination = bunch.Bunch(id="default", params={})
        self.galaxy_lib_dir = os.path.abspath("lib")
        self.job = model.Job()
        self.job_id = 1
        self.job.id = 1
        self.output_paths = ['/tmp/output1.dat']
        self.mock_metadata_path = os.path.abspath(os.path.join(test_directory, "METADATA_SET"))
        self.metadata_command = "touch %s" % self.mock_metadata_path
        self.galaxy_virtual_env = None
        self.shell = "/bin/bash"
        self.cleanup_job = "never"
        self.tmp_dir_creation_statement = ""

        # Cruft for setting metadata externally, axe at some point.
        self.external_output_metadata = bunch.Bunch(
            set_job_runner_external_pid=lambda pid, session: None
        )
        self.app.datatypes_registry.set_external_metadata_tool = bunch.Bunch(
            build_dependency_shell_commands=lambda: []
        )

    def check_tool_output(*args, **kwds):
        return "ok"

    def wait_for_external_id(self):
        """Test method for waiting until an external id has been registered."""
        external_id = None
        for i in range(50):
            external_id = self.job.job_runner_external_id
            if external_id:
                break
            time.sleep(.1)
        return external_id

    def prepare(self):
        self.prepare_called = True

    def set_job_destination(self, job_destination, external_id):
        self.job.job_runner_external_id = external_id

    def get_command_line(self):
        return self.command_line

    def get_id_tag(self):
        return "1"

    def get_state(self):
        return self.state

    def change_state(self, state):
        self.state = state

    def get_output_fnames(self):
        return []

    def get_job(self):
        return self.job

    def setup_external_metadata(self, **kwds):
        return self.metadata_command

    def get_env_setup_clause(self):
        return ""

    def has_limits(self):
        return False

    def fail(self, message, exception):
        self.fail_message = message
        self.fail_exception = exception

    def finish(self, stdout, stderr, exit_code, **kwds):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

    def tmp_directory(self):
        return None

    def home_directory(self):
        return None

    def reclaim_ownership(self):
        pass
