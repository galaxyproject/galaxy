import os
import sys
from queue import Queue
from types import ModuleType
from unittest import mock

from galaxy import (
    job_metrics,
    model,
)
from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.jobs.job_destination import JobDestination
from galaxy.jobs.runners import htcondor
from galaxy.util import bunch
from galaxy.util.unittest import TestCase


def _fake_htcondor2_module():
    import enum

    class FakeSubmit:
        def __init__(self, description):
            self.description = description

    class FakeSubmitResult:
        def __init__(self, cluster_id):
            self._cluster_id = cluster_id

        def cluster(self):
            return self._cluster_id

    class JobEventType(enum.Enum):
        SUBMIT = 0
        EXECUTE = 1
        IMAGE_SIZE = 2
        JOB_EVICTED = 3
        JOB_SUSPENDED = 4
        JOB_UNSUSPENDED = 5
        JOB_TERMINATED = 6
        JOB_ABORTED = 7
        JOB_HELD = 8
        CLUSTER_REMOVE = 9

    class JobAction(enum.Enum):
        Remove = "Remove"

    class DaemonType(enum.Enum):
        Schedd = 1

    class FakeJobEvent:
        def __init__(self, cluster, proc, event_type):
            self.cluster = cluster
            self.proc = proc
            self.type = event_type

    class FakeClassAd(dict):
        pass

    class FakeCollector:
        def __init__(self, pool=None):
            self.pool = pool
            self.locate_calls = []

        def locate(self, daemon_type, name=None):
            self.locate_calls.append((daemon_type, name))
            return FakeClassAd(
                Name=name or "schedd@local",
                MyAddress="addr",
                CondorVersion="v1",
                Pool=self.pool,
            )

        def locateAll(self, daemon_type):
            self.locate_calls.append((daemon_type, None))
            return [
                FakeClassAd(
                    Name="schedd@local",
                    MyAddress="addr",
                    CondorVersion="v1",
                    Pool=self.pool,
                )
            ]

    class FakeJobEventLog:
        events_by_log = {}

        def __init__(self, filename):
            self.filename = filename

        @classmethod
        def set_events(cls, filename, events):
            cls.events_by_log[filename] = list(events)

        def events(self, stop_after=None):
            events = self.events_by_log.get(self.filename, [])
            self.events_by_log[self.filename] = []
            for event in events:
                yield event

    class FakeSchedd:
        def __init__(self, location=None):
            self.submissions = []
            self.actions = []
            self.location = location

        def submit(self, description, count=0, spool=False, itemdata=None, queue=None):
            self.submissions.append(description)
            return FakeSubmitResult(123)

        def act(self, action, job_spec, reason=None):
            self.actions.append((action, job_spec, reason))
            return {}

    fake = ModuleType("htcondor2")
    fake.Submit = FakeSubmit
    fake.Schedd = FakeSchedd
    fake.Collector = FakeCollector
    fake.DaemonType = DaemonType
    fake.JobEventType = JobEventType
    fake.JobAction = JobAction
    fake.JobEventLog = FakeJobEventLog
    fake.FakeJobEvent = FakeJobEvent
    return fake


class TestHTCondorJobRunner(TestCase, UsesTools):
    def setUp(self):
        self.setup_app()
        self._init_tool()
        self.app.job_metrics = job_metrics.JobMetrics()
        self.app.config.cleanup_job = "never"
        self.job_wrapper = MockJobWrapper(self.app, self.test_directory, self.tool)
        self.fake_htcondor2 = _fake_htcondor2_module()
        self.patcher = mock.patch.dict(sys.modules, {"htcondor2": self.fake_htcondor2})
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tear_down_app()

    def test_queue_job_submits(self):
        self.job_wrapper.job_destination.params["request_cpus"] = 2
        runner = htcondor.HTCondorJobRunner(self.app, 1)
        runner.queue_job(self.job_wrapper)

        cjs = runner.monitor_queue.get_nowait()
        schedd = runner._schedd_for_destination(self.job_wrapper.job_destination)
        submit = schedd.submissions[0]
        with open(cjs.job_file) as handle:
            job_script = handle.read()

        assert self.job_wrapper.job.job_runner_external_id == "123"
        assert f"log = {cjs.user_log}" in submit.description
        assert "request_cpus = 2" in submit.description
        assert "queue" in submit.description
        assert (
            'GALAXY_SLOTS="2"; export GALAXY_SLOTS; GALAXY_SLOTS_CONFIGURED="1"; export GALAXY_SLOTS_CONFIGURED;'
            in job_script
        )
        assert "GALAXY_MEMORY_MB" in job_script

    def test_queue_job_docker_universe_sets_image(self):
        self.job_wrapper.job_destination.params["universe"] = "docker"
        runner = htcondor.HTCondorJobRunner(self.app, 1)
        container = bunch.Bunch(container_id="quay.io/galaxy/test:latest")
        with mock.patch.object(runner, "_find_container", side_effect=[None, container]):
            runner.queue_job(self.job_wrapper)

        schedd = runner._schedd_for_destination(self.job_wrapper.job_destination)
        submit = schedd.submissions[0]

        assert "universe = docker" in submit.description
        assert f"docker_image = {container.container_id}" in submit.description

    def test_event_log_transitions(self):
        runner = htcondor.HTCondorJobRunner(self.app, 1)
        runner.work_queue = Queue()
        runner.queue_job(self.job_wrapper)
        cjs = runner.monitor_queue.get_nowait()
        runner.watched = [cjs]

        with open(cjs.user_log, "w") as handle:
            handle.write("1")
        self.fake_htcondor2.JobEventLog.set_events(
            cjs.user_log,
            [self.fake_htcondor2.FakeJobEvent(123, 0, self.fake_htcondor2.JobEventType.EXECUTE)],
        )
        runner.check_watched_items()
        assert self.job_wrapper.state == model.Job.states.RUNNING

        with open(cjs.user_log, "a") as handle:
            handle.write("2")
        self.fake_htcondor2.JobEventLog.set_events(
            cjs.user_log,
            [self.fake_htcondor2.FakeJobEvent(123, 0, self.fake_htcondor2.JobEventType.JOB_TERMINATED)],
        )
        runner.check_watched_items()
        method, job_state = runner.work_queue.get_nowait()
        assert method == runner.finish_job
        assert job_state.job_id == "123"

    def test_event_log_aborted_triggers_fail(self):
        runner = htcondor.HTCondorJobRunner(self.app, 1)
        runner.work_queue = Queue()
        runner.queue_job(self.job_wrapper)
        cjs = runner.monitor_queue.get_nowait()
        runner.watched = [cjs]

        with open(cjs.user_log, "w") as handle:
            handle.write("1")
        self.fake_htcondor2.JobEventLog.set_events(
            cjs.user_log,
            [self.fake_htcondor2.FakeJobEvent(123, 0, self.fake_htcondor2.JobEventType.JOB_ABORTED)],
        )
        runner.check_watched_items()
        method, job_state = runner.work_queue.get_nowait()
        assert method == runner.fail_job
        assert job_state.job_id == "123"

    def test_event_log_cluster_remove_triggers_fail(self):
        runner = htcondor.HTCondorJobRunner(self.app, 1)
        runner.work_queue = Queue()
        runner.queue_job(self.job_wrapper)
        cjs = runner.monitor_queue.get_nowait()
        runner.watched = [cjs]

        with open(cjs.user_log, "w") as handle:
            handle.write("1")
        self.fake_htcondor2.JobEventLog.set_events(
            cjs.user_log,
            [self.fake_htcondor2.FakeJobEvent(123, 0, self.fake_htcondor2.JobEventType.CLUSTER_REMOVE)],
        )
        runner.check_watched_items()
        method, job_state = runner.work_queue.get_nowait()
        assert method == runner.fail_job
        assert job_state.job_id == "123"

    def test_queue_job_submit_failure(self):
        runner = htcondor.HTCondorJobRunner(self.app, 1)
        schedd = runner._schedd_for_destination(self.job_wrapper.job_destination)
        with mock.patch.object(schedd, "submit", side_effect=RuntimeError("boom")):
            runner.queue_job(self.job_wrapper)

        assert self.job_wrapper.fail_message == "htcondor submit failed"
        assert self.job_wrapper.job.job_runner_external_id is None

    def test_missing_event_log_keeps_job_watched(self):
        runner = htcondor.HTCondorJobRunner(self.app, 1)
        runner.work_queue = Queue()
        runner.queue_job(self.job_wrapper)
        cjs = runner.monitor_queue.get_nowait()
        runner.watched = [cjs]

        if os.path.exists(cjs.user_log):
            os.unlink(cjs.user_log)
        cjs.user_log_size = 0

        runner.check_watched_items()

        assert runner.watched == [cjs]
        assert runner.work_queue.empty()

    def test_stop_job_removes(self):
        runner = htcondor.HTCondorJobRunner(self.app, 1)
        runner.queue_job(self.job_wrapper)
        runner.stop_job(self.job_wrapper)
        schedd = runner._schedd_for_destination(self.job_wrapper.job_destination)
        action, job_spec, _reason = schedd.actions[0]
        assert action == self.fake_htcondor2.JobAction.Remove
        assert job_spec == 123

    def test_queue_job_uses_remote_schedd(self):
        self.job_wrapper.job_destination.params["htcondor_collector"] = "collector:9618"
        self.job_wrapper.job_destination.params["htcondor_schedd"] = "schedd@remote"
        runner = htcondor.HTCondorJobRunner(self.app, 1)
        runner.queue_job(self.job_wrapper)

        schedd = next(iter(runner._schedd_cache.values()))
        submit = schedd.submissions[0]

        assert schedd.location["Name"] == "schedd@remote"
        assert schedd.location["Pool"] == "collector:9618"
        assert "htcondor_collector" not in submit.description
        assert "htcondor_schedd" not in submit.description


class MockJobWrapper:
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
        self.dependency_shell_commands = None
        self.working_directory = working_directory
        self.tool_working_directory = tool_working_directory
        self.requires_setting_metadata = True
        self.job_destination = JobDestination(id="default", params={})
        self.galaxy_lib_dir = os.path.abspath("lib")
        self.job = model.Job()
        self.job_id = 1
        self.job.id = 1
        self.job.container = None
        self.output_paths = ["/tmp/output1.dat"]
        self.mock_metadata_path = os.path.abspath(os.path.join(test_directory, "METADATA_SET"))
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
        self.user = None

        self.external_output_metadata = bunch.Bunch()
        self.app.datatypes_registry.set_external_metadata_tool = bunch.Bunch(build_dependency_shell_commands=lambda: [])

    def check_tool_output(*args, **kwds):
        return "ok"

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
        return "1"

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
        return False

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
        pass

    def tmp_directory(self):
        return None

    def home_directory(self):
        return None

    def reclaim_ownership(self):
        pass

    @property
    def is_cwl_job(self):
        return False
