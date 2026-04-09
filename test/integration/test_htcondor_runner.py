import importlib
import json
import os
import shutil
import sys
import tempfile
from queue import Queue

import pytest

from galaxy import model
from galaxy.jobs.job_destination import JobDestination
from galaxy.jobs.runners import htcondor
from galaxy_test.driver import integration_util
from galaxy.util import bunch

LIVE_FAKE_MODULE_PATH = os.path.join(os.path.dirname(__file__), "htcondor_fake")


def _live_job_conf(htcondor_params: str) -> str:
    return f"""
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  htcondor:
    load: galaxy.jobs.runners.htcondor:HTCondorJobRunner
    workers: 1
execution:
  default: htcondor_environment
  environments:
    htcondor_environment:
      runner: htcondor{htcondor_params}
    local_environment:
      runner: local
tools:
  - id: __DATA_FETCH__
    environment: local_environment
"""


def _live_htcondor_params():
    lines = []
    collector = os.environ.get("GALAXY_TEST_HTCONDOR_COLLECTOR")
    schedd = os.environ.get("GALAXY_TEST_HTCONDOR_SCHEDD")
    condor_config = os.environ.get("GALAXY_TEST_HTCONDOR_CONFIG")
    request_memory = os.environ.get("GALAXY_TEST_HTCONDOR_REQUEST_MEMORY", "512")
    if collector:
        lines.append(f'      htcondor_collector: "{collector}"')
    if schedd:
        lines.append(f'      htcondor_schedd: "{schedd}"')
    if condor_config:
        lines.append(f'      htcondor_config: "{condor_config}"')
    if request_memory:
        lines.append(f"      request_memory: {request_memory}")
    return ("\n" + "\n".join(lines)) if lines else ""


def _handle_live_galaxy_config_kwds(config):
    if not os.environ.get("GALAXY_TEST_HTCONDOR"):
        pytest.skip("GALAXY_TEST_HTCONDOR not configured for htcondor integration tests")
    sys.modules.pop("htcondor2", None)
    try:
        import htcondor2  # noqa: F401
    except Exception:
        pytest.skip("htcondor2 is not installed in the test environment")

    htcondor_params = _live_htcondor_params()
    job_conf_str = _live_job_conf(htcondor_params)
    with tempfile.NamedTemporaryFile(suffix="_htcondor_job_conf.yml", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    config["job_config_file"] = job_conf.name
    job_working_directory = os.environ.get("GALAXY_TEST_HTCONDOR_JOB_WORKING_DIRECTORY")
    if not job_working_directory:
        job_working_directory = tempfile.mkdtemp(prefix="htcondor_job_working_", dir=os.getcwd())
    os.makedirs(job_working_directory, exist_ok=True)
    os.chmod(job_working_directory, 0o777)
    config["job_working_directory"] = job_working_directory
    data_directory = os.environ.get("GALAXY_TEST_HTCONDOR_DATA_DIR")
    if not data_directory:
        data_directory = tempfile.mkdtemp(prefix="htcondor_data_", dir=os.getcwd())
    os.chmod(data_directory, 0o777)
    file_path = os.path.join(data_directory, "files")
    new_file_path = os.path.join(data_directory, "new_files")
    os.makedirs(file_path, exist_ok=True)
    os.makedirs(new_file_path, exist_ok=True)
    os.chmod(file_path, 0o777)
    os.chmod(new_file_path, 0o777)
    config["file_path"] = file_path
    config["new_file_path"] = new_file_path


class HTCondorIntegrationInstance(integration_util.IntegrationInstance):
    framework_tool_and_types = True

    @classmethod
    def _prepare_galaxy(cls):
        sys.modules.pop("htcondor2", None)
        if LIVE_FAKE_MODULE_PATH in sys.path:
            sys.path.remove(LIVE_FAKE_MODULE_PATH)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        _handle_live_galaxy_config_kwds(config)


instance = integration_util.integration_module_instance(HTCondorIntegrationInstance)

test_tools = integration_util.integration_tool_runner(["simple_constructs"])


class FakeHTCondorIntegrationInstance(integration_util.IntegrationInstance):
    framework_tool_and_types = True
    _fake_record_dir: str
    _old_pythonpath: str | None
    _added_fake_sys_path: bool

    @classmethod
    def _prepare_galaxy(cls):
        sys.modules.pop("htcondor2", None)
        cls._fake_record_dir = tempfile.mkdtemp(prefix="fake_htcondor_records_")
        cls._old_pythonpath = os.environ.get("PYTHONPATH")
        cls._added_fake_sys_path = LIVE_FAKE_MODULE_PATH not in sys.path
        if cls._added_fake_sys_path:
            sys.path.insert(0, LIVE_FAKE_MODULE_PATH)
        fake_pythonpath = LIVE_FAKE_MODULE_PATH
        if cls._old_pythonpath:
            os.environ["PYTHONPATH"] = f"{fake_pythonpath}{os.pathsep}{cls._old_pythonpath}"
        else:
            os.environ["PYTHONPATH"] = fake_pythonpath
        os.environ["GALAXY_TEST_FAKE_HTCONDOR_RECORD_DIR"] = cls._fake_record_dir

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            sys.modules.pop("htcondor2", None)
            if cls._added_fake_sys_path and LIVE_FAKE_MODULE_PATH in sys.path:
                sys.path.remove(LIVE_FAKE_MODULE_PATH)
            if cls._old_pythonpath is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = cls._old_pythonpath
            os.environ.pop("GALAXY_TEST_FAKE_HTCONDOR_RECORD_DIR", None)
            shutil.rmtree(cls._fake_record_dir, ignore_errors=True)

fake_instance = integration_util.integration_module_instance(FakeHTCondorIntegrationInstance)


class FastFakeHTCondorJobRunner(htcondor.HTCondorJobRunner):
    def prepare_job(
        self,
        job_wrapper,
        include_metadata=False,
        include_work_dir_outputs=True,
        modify_command_for_container=True,
        stream_stdout_stderr=False,
    ):
        job_state = job_wrapper.get_state()
        if job_state == model.Job.states.DELETED:
            return False
        if job_state != model.Job.states.QUEUED:
            return False
        job_wrapper.prepare()
        job_wrapper.runner_command_line = job_wrapper.command_line
        return True

    def get_job_file(self, job_wrapper, **kwds):
        return "#!/bin/bash\nexit 0\n"

    def write_executable_script(self, path, contents, job_io):
        with open(path, "w") as handle:
            handle.write(contents)
        os.chmod(path, 0o755)


@pytest.fixture
def fake_htcondor(fake_instance):
    record_dir = fake_instance._fake_record_dir
    module = importlib.import_module("htcondor2")
    for entry in os.listdir(record_dir):
        os.unlink(os.path.join(record_dir, entry))
    module.JobEventLog.events_by_log.clear()
    yield module
    module.JobEventLog.events_by_log.clear()
    for entry in os.listdir(record_dir):
        os.unlink(os.path.join(record_dir, entry))


@pytest.fixture
def runner_factory(fake_instance):
    runners = []
    original_helper_module = htcondor.HTCONDOR_HELPER_MODULE

    def create_runner():
        runner = FastFakeHTCondorJobRunner(fake_instance._app, 1)
        runner.work_queue = Queue()
        runners.append(runner)
        return runner

    htcondor.HTCONDOR_HELPER_MODULE = "htcondor_helper"
    yield create_runner
    htcondor.HTCONDOR_HELPER_MODULE = original_helper_module

    for runner in runners:
        work_threads = getattr(runner, "work_threads", None)
        if work_threads is not None and not runner._should_stop:
            runner.shutdown()
        else:
            runner._shutdown_clients()


def _tool(fake_instance):
    tool = fake_instance._app.toolbox.get_tool("create_2")
    assert tool is not None
    return tool


def _job_wrapper(fake_instance, job_id, destination_params=None, *, state=model.Job.states.QUEUED):
    return MockJobWrapper(
        fake_instance._app,
        fake_instance._tempdir,
        _tool(fake_instance),
        destination_params or {},
        job_id,
        state=state,
    )


def _records(fake_instance, kind=None):
    records = []
    for entry in sorted(os.listdir(fake_instance._fake_record_dir)):
        path = os.path.join(fake_instance._fake_record_dir, entry)
        with open(path) as handle:
            record = json.load(handle)
        if kind is None or record["kind"] == kind:
            records.append(record)
    return records


def _watch_job(runner, job_wrapper, external_id="123"):
    cjs = htcondor.HTCondorJobState(
        job_wrapper=job_wrapper,
        job_destination=job_wrapper.job_destination,
        user_log=os.path.join(job_wrapper.working_directory, f"galaxy_{job_wrapper.get_id_tag()}.condor.log"),
        files_dir=job_wrapper.working_directory,
        job_id=external_id,
    )
    cjs.register_cleanup_file_attribute("user_log")
    runner.watched = [cjs]
    return cjs


def _write_user_log(cjs):
    with open(cjs.user_log, "w") as handle:
        handle.write("1")


def _set_job_events(fake_htcondor, cjs, event_names):
    fake_htcondor.JobEventLog.set_events(
        cjs.user_log,
        [
            fake_htcondor.FakeJobEvent(int(cjs.job_id), 0, getattr(fake_htcondor.JobEventType, event_name))
            for event_name in event_names
        ],
    )


@pytest.mark.parametrize(
    (
        "destination_params",
        "event_names",
        "job_state",
        "create_log",
        "expected_method_name",
        "expected_wrapper_state",
        "expected_running",
        "expected_watched_count",
        "expect_entry_points",
    ),
    [
        pytest.param(
            dict(htcondor_config="/tmp/condor-execute"),
            ["EXECUTE"],
            None,
            True,
            None,
            model.Job.states.RUNNING,
            True,
            1,
            True,
            id="execute-sets-running",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-terminated"),
            ["JOB_TERMINATED"],
            None,
            True,
            "finish_job",
            model.Job.states.QUEUED,
            False,
            0,
            False,
            id="terminated-finishes",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-aborted"),
            ["JOB_ABORTED"],
            None,
            True,
            "fail_job",
            model.Job.states.QUEUED,
            False,
            0,
            False,
            id="aborted-fails",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-removed"),
            ["CLUSTER_REMOVE"],
            None,
            True,
            "fail_job",
            model.Job.states.QUEUED,
            False,
            0,
            False,
            id="cluster-remove-fails",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-held-stopped"),
            ["JOB_HELD"],
            model.Job.states.STOPPED,
            True,
            "finish_job",
            model.Job.states.STOPPED,
            False,
            0,
            False,
            id="held-stopped-finishes",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-held-failed"),
            ["JOB_HELD", "JOB_ABORTED"],
            None,
            True,
            "fail_job",
            model.Job.states.QUEUED,
            False,
            0,
            False,
            id="held-terminal-fails",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-missing-log"),
            [],
            None,
            False,
            None,
            model.Job.states.QUEUED,
            False,
            1,
            False,
            id="missing-log-stays-watched",
        ),
    ],
)
def test_watch_lifecycle_transitions(
    fake_instance,
    fake_htcondor,
    runner_factory,
    destination_params,
    event_names,
    job_state,
    create_log,
    expected_method_name,
    expected_wrapper_state,
    expected_running,
    expected_watched_count,
    expect_entry_points,
):
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, destination_params)
    cjs = _watch_job(runner, job_wrapper)

    if create_log:
        _write_user_log(cjs)
    if event_names:
        _set_job_events(fake_htcondor, cjs, event_names)
    if job_state is not None:
        job_wrapper.state = job_state

    runner.check_watched_items()

    if expected_method_name is None:
        assert runner.work_queue.empty()
    else:
        method, job_state_record = runner.work_queue.get_nowait()
        assert method == getattr(runner, expected_method_name)
        assert job_state_record.job_id == cjs.job_id
        assert runner.work_queue.empty()

    assert len(runner.watched) == expected_watched_count
    if expected_watched_count:
        assert runner.watched[0] is cjs
        assert runner.watched[0].running is expected_running
    assert job_wrapper.state == expected_wrapper_state
    assert job_wrapper.entry_points_checked is expect_entry_points


def test_different_configs_use_separate_helpers(fake_instance, fake_htcondor, runner_factory):
    runner = runner_factory()
    runner.queue_job(_job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-A", htcondor_schedd="schedd@alpha")))
    runner.queue_job(_job_wrapper(fake_instance, 2, dict(htcondor_config="/tmp/condor-B", htcondor_schedd="schedd@beta")))

    records = _records(fake_instance, "submit")
    assert len(records) == 2
    assert {record["config"] for record in records} == {
        os.path.realpath("/tmp/condor-A"),
        os.path.realpath("/tmp/condor-B"),
    }
    assert {record["schedd_name"] for record in records} == {"schedd@alpha", "schedd@beta"}
    assert len({record["pid"] for record in records}) == 2


def test_same_config_reuses_helper_across_shedds(fake_instance, fake_htcondor, runner_factory):
    runner = runner_factory()
    shared_config = "/tmp/condor-shared"
    runner.queue_job(
        _job_wrapper(
            fake_instance,
            1,
            dict(
                htcondor_config=shared_config,
                htcondor_collector="collector:9618",
                htcondor_schedd="schedd@alpha",
            ),
        )
    )
    runner.queue_job(
        _job_wrapper(
            fake_instance,
            2,
            dict(
                htcondor_config=shared_config,
                htcondor_collector="collector:9618",
                htcondor_schedd="schedd@beta",
            ),
        )
    )

    records = _records(fake_instance, "submit")
    assert len(records) == 2
    assert {record["config"] for record in records} == {os.path.realpath(shared_config)}
    assert {record["schedd_name"] for record in records} == {"schedd@alpha", "schedd@beta"}
    assert {record["collector"] for record in records} == {"collector:9618"}
    assert len({record["pid"] for record in records}) == 1
    for record in records:
        assert "htcondor_config" not in record["submit_description"]
        assert "htcondor_collector" not in record["submit_description"]
        assert "htcondor_schedd" not in record["submit_description"]


def test_stop_job_uses_same_config_scoped_helper(fake_instance, fake_htcondor, runner_factory):
    runner = runner_factory()
    job_wrapper = _job_wrapper(
        fake_instance, 1, dict(htcondor_config="/tmp/condor-stop", htcondor_schedd="schedd@stop")
    )
    runner.queue_job(job_wrapper)
    runner.stop_job(job_wrapper)

    submit_record = _records(fake_instance, "submit")[0]
    remove_record = _records(fake_instance, "remove")[0]
    assert submit_record["pid"] == remove_record["pid"]
    assert submit_record["config"] == remove_record["config"] == os.path.realpath("/tmp/condor-stop")
    assert remove_record["schedd_name"] == "schedd@stop"
    assert remove_record["job_spec"] == int(job_wrapper.job.job_runner_external_id)


@pytest.mark.parametrize("state", [model.Job.states.STOPPED, model.Job.states.DELETED], ids=["stopped", "deleted"])
def test_stopped_or_deleted_jobs_are_not_submitted(fake_instance, fake_htcondor, runner_factory, state):
    runner = runner_factory()
    job_wrapper = _job_wrapper(
        fake_instance,
        1,
        dict(htcondor_config="/tmp/condor-cancelled"),
        state=state,
    )

    runner.queue_job(job_wrapper)

    assert _records(fake_instance) == []
    assert runner.monitor_queue.empty()
    assert runner._client_cache == {}


@pytest.mark.parametrize(
    "job_state, expected_running",
    [
        pytest.param(model.Job.states.QUEUED, False, id="queued"),
        pytest.param(model.Job.states.RUNNING, True, id="running"),
        pytest.param(model.Job.states.STOPPED, True, id="stopped"),
    ],
)
def test_recover_readds_monitored_jobs(fake_instance, fake_htcondor, runner_factory, job_state, expected_running):
    runner = runner_factory()
    job = model.Job()
    job.id = 7
    job.state = job_state
    job.job_runner_external_id = "123"
    job_wrapper = _job_wrapper(fake_instance, 7, dict(htcondor_config="/tmp/condor-recover"))

    runner.recover(job, job_wrapper)

    cjs = runner.monitor_queue.get_nowait()
    assert cjs.job_id == "123"
    assert cjs.running is expected_running
    assert cjs.job_wrapper is job_wrapper


def test_recover_without_external_id_requeues_job(fake_instance, fake_htcondor, runner_factory, monkeypatch):
    runner = runner_factory()
    job = model.Job()
    job.id = 8
    job.state = model.Job.states.QUEUED
    job_wrapper = _job_wrapper(fake_instance, 8, dict(htcondor_config="/tmp/condor-requeue"))
    put_calls = []
    monkeypatch.setattr(runner, "put", lambda recovered_job_wrapper: put_calls.append(recovered_job_wrapper))

    runner.recover(job, job_wrapper)

    assert put_calls == [job_wrapper]
    assert runner.monitor_queue.empty()


def test_runner_shutdown_terminates_all_helpers(fake_instance, fake_htcondor, runner_factory):
    runner = runner_factory()
    runner.work_threads = []
    runner.shutdown_monitor = lambda: None
    runner.queue_job(_job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-A", htcondor_schedd="schedd@alpha")))
    runner.queue_job(_job_wrapper(fake_instance, 2, dict(htcondor_config="/tmp/condor-B", htcondor_schedd="schedd@beta")))

    clients = list(runner._client_cache.values())
    processes = [client._process for client in clients if getattr(client, "_process", None) is not None]
    assert len(processes) == 2
    assert all(process.poll() is None for process in processes)

    runner.shutdown()

    assert all(getattr(client, "_process", None) is None for client in clients)
    assert all(process.poll() is not None for process in processes)


def test_helper_respawns_after_crash(fake_instance, fake_htcondor, runner_factory):
    runner = runner_factory()
    destination_params = dict(htcondor_config="/tmp/condor-respawn", htcondor_schedd="schedd@respawn")
    first_job_wrapper = _job_wrapper(fake_instance, 1, destination_params)
    second_job_wrapper = _job_wrapper(fake_instance, 2, destination_params)
    runner.queue_job(first_job_wrapper)

    client = runner._client_for_destination(first_job_wrapper.job_destination)
    process = client._process
    assert process is not None
    first_pid = process.pid
    process.kill()
    process.wait(timeout=5)

    runner.queue_job(second_job_wrapper)

    submit_records = _records(fake_instance, "submit")
    assert len(submit_records) == 2
    assert submit_records[0]["pid"] == first_pid
    assert submit_records[1]["pid"] != first_pid
    assert submit_records[1]["config"] == os.path.realpath(destination_params["htcondor_config"])


def test_finish_handles_external_metadata(fake_instance, fake_htcondor, runner_factory, monkeypatch):
    runner = runner_factory()
    job_wrapper = _job_wrapper(
        fake_instance,
        1,
        dict(htcondor_config="/tmp/condor-external-metadata", embed_metadata_in_job=False),
    )
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)
    _set_job_events(fake_htcondor, cjs, ["JOB_TERMINATED"])
    metadata_calls = []

    def handle_metadata_externally(job_wrapper_arg, resolve_requirements=False):
        metadata_calls.append((job_wrapper_arg, resolve_requirements))

    monkeypatch.setattr(runner, "_handle_metadata_externally", handle_metadata_externally)

    runner.check_watched_items()

    method, job_state_record = runner.work_queue.get_nowait()
    assert method == runner.finish_job
    assert job_state_record.job_id == cjs.job_id
    assert metadata_calls == [(job_wrapper, True)]
    assert runner.watched == []


class MockJobWrapper:
    def __init__(self, app, test_directory, tool, destination_params, job_id, state=model.Job.states.QUEUED):
        working_directory = tempfile.mkdtemp(prefix="htcondor_workdir_", dir=test_directory)
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
        self.job_destination = JobDestination(id=f"htcondor_destination_{job_id}", params=destination_params)
        self.galaxy_lib_dir = os.path.abspath("lib")
        self.job = model.Job()
        self.job_id = job_id
        self.job.id = job_id
        self.job.container = None
        self.output_paths = ["/tmp/output1.dat"]
        self.mock_metadata_path = os.path.join(working_directory, f"METADATA_SET_{job_id}")
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
        return str(self.job_id)

    def get_state(self):
        return self.state

    def change_state(self, state, job=None):
        self.state = state

    @property
    def job_io(self):
        return bunch.Bunch(
            get_output_fnames=lambda: [],
            check_job_script_integrity=False,
            version_path="/tmp/version_path",
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
