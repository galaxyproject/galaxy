"""Shared application unit-test support for job runners."""

import datetime
import os
import tempfile
import time

from galaxy import model
from galaxy.jobs.job_destination import JobDestination
from galaxy.util import bunch


class MockJobWrapper:
    """A runner-facing ``MinimalJobWrapper`` test double with real work directories."""

    def __init__(
        self,
        app,
        test_directory,
        tool,
        destination_params=None,
        job_id=1,
        state=model.Job.states.QUEUED,
        destination_id="default",
        use_unique_working_directory=False,
    ):
        if use_unique_working_directory:
            working_directory = tempfile.mkdtemp(prefix="job_workdir_", dir=test_directory)
            mock_metadata_path = os.path.join(working_directory, f"METADATA_SET_{job_id}")
        else:
            working_directory = os.path.join(test_directory, "workdir")
            os.makedirs(working_directory)
            mock_metadata_path = os.path.abspath(os.path.join(test_directory, "METADATA_SET"))
        tool_working_directory = os.path.join(working_directory, "working")
        os.makedirs(tool_working_directory)
        self.app = app
        self.tool = tool
        self.requires_containerization = False
        self.state = state
        self.command_line = "echo HelloWorld"
        self.environment_variables = []
        self.commands_in_new_shell = False
        self.prepare_called = False
        self.dependency_shell_commands = None
        self.working_directory = working_directory
        self.tool_working_directory = tool_working_directory
        self.requires_setting_metadata = True
        self.job_destination = JobDestination(id=destination_id, params=destination_params or {})
        self.galaxy_lib_dir = os.path.abspath("lib")
        self.job = model.Job()
        self.job_id = job_id
        self.job.id = job_id
        self.job.container = None
        self.output_paths = ["/tmp/output1.dat"]
        self.mock_metadata_path = mock_metadata_path
        self.metadata_command = f"touch {self.mock_metadata_path}"
        self.galaxy_virtual_env = None
        self.shell = "/bin/bash"
        self.cleanup_job = "never"
        self.tmp_dir_creation_statement = ""
        self.use_metadata_binary = False
        self.guest_ports = []
        self.metadata_strategy = "directory"
        self.remote_command_line = False
        self.entry_points_checked = False
        self.cleanup_called = False
        self.user = None

        self.external_output_metadata: bunch.Bunch | None = bunch.Bunch()
        self.app.datatypes_registry.set_external_metadata_tool = bunch.Bunch(
            build_dependency_shell_commands=lambda **kwds: []
        )

    def check_tool_output(*args, **kwds):
        return "ok"

    def wait_for_external_id(self):
        """Wait until a runner records an external id."""
        external_id = None
        for _ in range(50):
            external_id = self.job.job_runner_external_id
            if external_id:
                break
            time.sleep(0.1)
        return external_id

    def prepare(self):
        self.prepare_called = True

    def set_external_id(self, external_id, **kwd):
        self.job.job_runner_external_id = external_id

    def get_command_line(self):
        return self.command_line

    def container_monitor_command(self, *args, **kwds):
        return None

    def check_for_entry_points(self):
        self.entry_points_checked = True

    def get_id_tag(self):
        return str(self.job_id)

    def get_state(self):
        return self.state

    def change_state(self, state, job=None):
        self.state = state

    @property
    def job_io(self):
        return bunch.Bunch(
            get_output_fnames=lambda: [], check_job_script_integrity=False, version_path="/tmp/version_path"
        )

    def get_job(self):
        return self.job

    def setup_external_metadata(self, **kwds):
        return self.metadata_command

    def get_env_setup_clause(self):
        return ""

    def has_limits(self):
        return getattr(self.tool, "timelimit", None) is not None

    def check_limits(self, runtime=None):
        if runtime is not None and self.tool:
            timelimit = getattr(self.tool, "timelimit", None)
            if timelimit and timelimit > 0:
                timelimit_delta = datetime.timedelta(seconds=timelimit)
                if runtime > timelimit_delta:
                    return (
                        "tool_timelimit_reached",
                        f"Job exceeded tool time limit (limit: {timelimit}s)",
                    )
        return None

    def fail(
        self, message, exception=False, tool_stdout="", tool_stderr="", exit_code=None, job_stdout=None, job_stderr=None
    ):
        self.fail_message = message
        self.fail_exception = exception

    def finish(self, stdout, stderr, exit_code, **kwds):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

    def cleanup(self):
        self.cleanup_called = True

    def tmp_directory(self):
        return None

    def home_directory(self):
        return None

    def reclaim_ownership(self):
        pass

    @property
    def is_cwl_job(self):
        return False
