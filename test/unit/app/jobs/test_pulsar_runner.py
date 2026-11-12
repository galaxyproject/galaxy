"""Unit tests for Pulsar job runner utility methods and client construction."""

import logging
import queue
from dataclasses import dataclass
from types import SimpleNamespace
from typing import (
    Any,
    cast,
)
from unittest.mock import MagicMock

import pytest
from packaging.version import Version
from pulsar.client.client import (
    JobClient,
    MessageJobClient,
    RelayJobClient,
)
from pulsar.client.gcp import (
    GcpMessageCoexecutionJobClient,
    GcpPollingCoexecutionJobClient,
)
from pulsar.client.kubernetes import (
    K8sMessageCoexecutionJobClient,
    K8sPollingCoexecutionJobClient,
)
from pulsar.client.server_interface import (
    HttpPulsarInterface,
    LocalPulsarInterface,
)
from pulsar.client.tes import (
    TesMessageCoexecutionJobClient,
    TesPollingCoexecutionJobClient,
)

from galaxy import model
from galaxy.exceptions import (
    ConfigurationError,
    InsufficientPermissionsException,
)
from galaxy.job_metrics.instrumenters.pulsar import PulsarPlugin
from galaxy.jobs.runners import (
    AsynchronousJobState,
    JobState,
    pulsar as pulsar_runner,
)
from galaxy.jobs.runners.pulsar import (  # type: ignore[attr-defined]
    build_client_manager,
    effective_dependency_resolution,
    FAILED_REMOTE_ERROR,
    LOST_REMOTE_ERROR,
    PulsarFinishJobResult,
    PulsarJobRunner,
)
from galaxy.jobs.runners.runner_state_definitions import RUNNER_STATE_DEFINITIONS
from galaxy.tool_util.output_checker import DETECTED_JOB_STATE


@dataclass
class MockContainer:
    container_id: str = "busybox"
    image_identifier_is_path: bool = True
    resolve_dependencies: bool = False


class _ComputeEnvironment:
    """Minimal stand-in exposing only container_path_rewrite."""

    def __init__(self, rewrites):
        self._rewrites = rewrites

    def container_path_rewrite(self, path):
        return self._rewrites.get(path)


IMAGE = "/cvmfs/singularity.galaxyproject.org/all/img"
REWRITTEN = "/job/dir/.cvmfsexec/dist/cvmfs/singularity.galaxyproject.org/all/img"


def test_rewrite_container_applies_compute_environment_rewrite():
    container = MockContainer(IMAGE)
    compute_environment = _ComputeEnvironment({IMAGE: REWRITTEN})
    PulsarJobRunner._rewrite_container_for_compute_environment(container, compute_environment)
    assert container.container_id == REWRITTEN


def test_rewrite_container_noop_without_matching_rule():
    # container_path_rewrite returns None when no file_actions rule matches.
    container = MockContainer(IMAGE)
    compute_environment = _ComputeEnvironment({})
    PulsarJobRunner._rewrite_container_for_compute_environment(container, compute_environment)
    assert container.container_id == IMAGE


def test_rewrite_container_noop_when_identifier_not_a_path():
    # A registry/docker:// identifier is resolved by the compute node itself;
    # never route it through the path rewriter even if a rule would match.
    container = MockContainer("docker://quay.io/biocontainers/bwa", image_identifier_is_path=False)
    compute_environment = _ComputeEnvironment({"docker://quay.io/biocontainers/bwa": REWRITTEN})
    PulsarJobRunner._rewrite_container_for_compute_environment(container, compute_environment)
    assert container.container_id == "docker://quay.io/biocontainers/bwa"


def test_rewrite_container_noop_without_compute_environment():
    # No compute environment => not rewrite_parameters mode; leave image as-is.
    container = MockContainer(IMAGE)
    PulsarJobRunner._rewrite_container_for_compute_environment(container, None)
    assert container.container_id == IMAGE


def test_rewrite_container_noop_without_container():
    # Should not raise when there is no resolved container.
    compute_environment = _ComputeEnvironment({IMAGE: REWRITTEN})
    PulsarJobRunner._rewrite_container_for_compute_environment(None, compute_environment)


def test_finishing_uses_the_version_the_job_was_submitted_for(tmp_path):
    PulsarPlugin.write_version_target(
        str(tmp_path), client_version="0.15.16", target_version="0.15.0.dev1", source="container_image"
    )
    assert PulsarJobRunner.submitted_pulsar_version(str(tmp_path), {}) == Version("0.15.0.dev1")
    assert PulsarJobRunner.submitted_pulsar_version(str(tmp_path), {"pulsar_version": "0.16.0"}) == Version(
        "0.15.0.dev1"
    )


def test_finishing_a_job_submitted_before_versions_were_recorded(tmp_path):
    assert PulsarJobRunner.submitted_pulsar_version(str(tmp_path), {"pulsar_version": "0.15.13"}) == Version("0.15.13")
    assert PulsarJobRunner.submitted_pulsar_version(str(tmp_path), {}) == Version("0.6.0")


def test_finish_job_describes_outputs_for_the_submitted_version(tmp_path, monkeypatch):
    metadata_directory = tmp_path / "metadata"
    PulsarPlugin.write_version_target(
        str(metadata_directory), client_version="0.15.16", target_version="0.15.16", source="destination"
    )
    # Polling coexecution status comes from the platform and carries no version at all.
    client = SimpleNamespace(full_status=lambda: {}, destination_params={})
    job_wrapper = SimpleNamespace(
        job_id=1,
        working_directory=str(tmp_path),
        cleanup_job="never",
        get_state=lambda: model.Job.states.RUNNING,
    )
    job_state = cast(Any, object.__new__(AsynchronousJobState))
    job_state.job_wrapper = job_wrapper
    described_for = []
    runner = cast(Any, object.__new__(PulsarJobRunner))
    runner.get_client_from_state = lambda job_state: client
    runner._PulsarJobRunner__client_outputs = lambda client, job_wrapper, version: described_for.append(version)
    runner._complete_staged_job = lambda *args, **kwargs: None
    monkeypatch.setattr(pulsar_runner, "pulsar_finish_job", lambda **kwargs: False)
    runner.finish_job(job_state)
    assert described_for == [Version("0.15.16")]


class RecordingClient:
    def __init__(self, destination_params, **kwargs):
        self.destination_params = destination_params
        self.killed = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    def kill(self):
        self.killed = True


class RecordingClientManager:
    def __init__(self):
        self.calls = []
        self.clients = []

    def get_client(self, destination_params, **kwargs):
        self.calls.append((destination_params, kwargs))
        client = RecordingClient(destination_params, **kwargs)
        self.clients.append(client)
        return client


def _runner():
    """A runner with just enough wired up to build clients."""
    runner = cast(Any, object.__new__(PulsarJobRunner))
    runner.app = SimpleNamespace(
        security=SimpleNamespace(encode_id=lambda job_id, kind=None: f"enc{job_id}"),
        config=SimpleNamespace(nginx_upload_job_files_path=None),
    )
    runner.galaxy_url = "http://galaxy.example"
    runner.client_manager = RecordingClientManager()
    return runner


@pytest.mark.parametrize(
    "options,destination,message_class,polling_class",
    [
        ({"k8s_enabled": True}, {"k8s_enabled": True}, K8sMessageCoexecutionJobClient, K8sPollingCoexecutionJobClient),
        (
            {"tes_enabled": True},
            {"tes_url": "http://tes.example"},
            TesMessageCoexecutionJobClient,
            TesPollingCoexecutionJobClient,
        ),
        (
            {"gcp_batch_enabled": True},
            {"project_id": "test-project"},
            GcpMessageCoexecutionJobClient,
            GcpPollingCoexecutionJobClient,
        ),
    ],
)
@pytest.mark.parametrize("messaging", [False, True])
def test_real_client_manager_selects_coexecution_backend(options, destination, message_class, polling_class, messaging):
    """Galaxy's factory must retain every backend for both status transports."""
    runner = _runner()
    runner.client_manager = build_client_manager(**options, **({"amqp_url": "memory://"} if messaging else {}))
    try:
        client = runner.get_client(destination, 543)
        assert isinstance(client, message_class if messaging else polling_class)
        assert client.job_id == "543"
        assert client.job_directory
    finally:
        runner.client_manager.shutdown()


@pytest.mark.parametrize(
    "options,expected_class",
    [
        ({}, JobClient),
        ({"job_manager": SimpleNamespace()}, JobClient),
        ({"amqp_url": "memory://"}, MessageJobClient),
        (
            {"relay_url": "https://relay.example", "relay_username": "test", "relay_password": "test"},
            RelayJobClient,
        ),
    ],
    ids=["http", "local", "amqp", "relay"],
)
def test_real_client_manager_preserves_standard_transports(options, expected_class):
    runner = _runner()
    runner.client_manager = build_client_manager(**options)
    try:
        client = runner.get_client({"url": "http://pulsar.example", "jobs_directory": "/jobs"}, 543)
        assert isinstance(client, expected_class)
        assert client.job_id == "543"
        if expected_class is JobClient:
            expected_interface = LocalPulsarInterface if "job_manager" in options else HttpPulsarInterface
            assert isinstance(client.job_manager_interface, expected_interface)
    finally:
        runner.client_manager.shutdown()


def _job_state(galaxy_job_id, external_id):
    job = SimpleNamespace(get_job_runner_external_id=lambda: external_id)
    job_wrapper = SimpleNamespace(job_id=galaxy_job_id, get_job=lambda: job)
    return SimpleNamespace(
        job_destination=SimpleNamespace(params={"url": "http://pulsar.example"}),
        job_wrapper=job_wrapper,
        job_id=external_id or str(galaxy_job_id),
    )


def test_get_client_omits_external_id_when_absent():
    runner = _runner()
    runner.get_client({}, 543)
    _destination_params, kwargs = runner.client_manager.calls[0]
    assert "external_id" not in kwargs
    assert kwargs["job_id"] == "543"


def test_get_client_passes_external_id_through():
    runner = _runner()
    runner.get_client({}, 543, external_id="tes-task-abc")
    _destination_params, kwargs = runner.client_manager.calls[0]
    assert kwargs["external_id"] == "tes-task-abc"
    # The Galaxy id still drives the job files and token endpoints.
    assert kwargs["job_id"] == "543"
    assert "enc543" in kwargs["files_endpoint"]


def test_get_client_from_state_supplies_the_recorded_external_id():
    """TES status polling has to use the id returned by create_task."""
    runner = _runner()
    runner.get_client_from_state(_job_state(543, "tes-task-abc"))
    _destination_params, kwargs = runner.client_manager.calls[0]
    assert kwargs["job_id"] == "543"
    assert kwargs["external_id"] == "tes-task-abc"


def test_get_client_from_state_does_not_invent_an_external_id():
    """job_state.job_id falls back to the Galaxy id; that is not a backend name."""
    runner = _runner()
    runner.get_client_from_state(_job_state(543, None))
    _destination_params, kwargs = runner.client_manager.calls[0]
    assert "external_id" not in kwargs


def test_stop_job_supplies_recorded_external_id_to_kill_client():
    runner = _runner()
    external_id = "tes-task-abc"
    job = SimpleNamespace(
        id=543,
        job_runner_external_id=external_id,
        job_runner_name="pulsar",
        destination_params={"url": "http://pulsar.example", "remote_metadata": True},
        get_external_output_metadata=lambda: [],
    )
    job_wrapper = SimpleNamespace(get_job=lambda: job)

    runner.stop_job(job_wrapper)

    _destination_params, kill_kwargs = runner.client_manager.calls[-1]
    assert kill_kwargs["external_id"] == external_id
    assert runner.client_manager.clients[-1].killed


@pytest.mark.parametrize("remote", [False, True])
def test_metadata_container_uses_execution_host_paths(monkeypatch, remote):
    """Pulsar's staging directory need not exist on the Galaxy host, or vice versa."""
    storage_paths = {"/galaxy/objects"}

    def get_disk_paths(object_store):
        assert not remote, "Remote metadata must not query Galaxy's disk object store"
        return storage_paths

    monkeypatch.setattr("galaxy.jobs.runners.get_disk_paths", get_disk_paths)
    finder = SimpleNamespace(find_container=lambda tool_info, destination_info, job_info: job_info)
    runner = _runner()
    runner.app = SimpleNamespace(container_finder=finder, object_store=object())
    wrapper = SimpleNamespace(
        working_directory="/galaxy/jobs/1",
        job_destination=SimpleNamespace(params={"metadata_config": {"containerize": True}}),
    )
    job_info = runner._get_metadata_container(
        wrapper,
        job_directory_type="pulsar" if remote else "galaxy",
        working_directory="/pulsar/staging/1" if remote else None,
    )
    expected_directory = "/pulsar/staging/1" if remote else "/galaxy/jobs/1"
    assert job_info.working_directory == expected_directory
    assert job_info.job_directory == expected_directory
    assert job_info.output_paths == (set() if remote else storage_paths)


@pytest.mark.parametrize("version", ["26.1.1", "26.2.dev0"])
@pytest.mark.parametrize("image", [None, "registry.example/metadata@sha256:custom"])
def test_metadata_container_tracks_galaxy_release(monkeypatch, version, image):
    profile = float(".".join(version.split(".")[:2]))
    monkeypatch.setattr("galaxy.jobs.runners.VERSION", version)
    monkeypatch.setattr("galaxy.jobs.runners.VERSION_MAJOR", str(profile))
    runner = _runner()
    captured = []

    def find_container(tool_info, destination_info, job_info):
        captured.append(tool_info)
        return object()

    runner.app = SimpleNamespace(container_finder=SimpleNamespace(find_container=find_container))
    config = {"containerize": True}
    if image is not None:
        config["image"] = image
    wrapper = SimpleNamespace(
        working_directory="/galaxy/jobs/1",
        job_destination=SimpleNamespace(params={"metadata_config": config}),
    )
    runner._get_metadata_container(wrapper, job_directory_type="pulsar", working_directory="/pulsar/staging/1")
    tool_info = captured[0]
    assert tool_info.profile == profile
    assert tool_info.tool_version == version
    assert tool_info.container_descriptions[0].identifier == (
        image or f"quay.io/galaxyproject/galaxy-job-execution:{version}"
    )


@pytest.mark.parametrize("remote", [False, True])
def test_requested_metadata_container_must_resolve(monkeypatch, remote):
    monkeypatch.setattr("galaxy.jobs.runners.get_disk_paths", lambda _: set())
    runner = _runner()
    runner.app = SimpleNamespace(
        object_store=object(),
        container_finder=SimpleNamespace(find_container=lambda *args: None),
    )
    wrapper = SimpleNamespace(
        working_directory="/jobs/1",
        job_destination=SimpleNamespace(params={"metadata_config": {"containerize": True, "image": "site/metadata:1"}}),
    )
    with pytest.raises(ConfigurationError, match="Cannot resolve metadata container 'site/metadata:1' using 'docker'"):
        runner._get_metadata_container(wrapper, job_directory_type="pulsar" if remote else "galaxy")


@pytest.mark.parametrize("config", [{}, {"metadata_config": {"containerize": False}}])
def test_host_metadata_does_not_resolve_container(config):
    runner = _runner()
    wrapper = SimpleNamespace(job_destination=SimpleNamespace(params=config))
    assert runner._get_metadata_container(wrapper) is None


def test_rejected_job_fails_without_resubmission():
    runner = cast(Any, object.__new__(PulsarJobRunner))
    runner.work_queue = queue.Queue()
    client = SimpleNamespace(
        destination_params={"remote_container_handling": True}, setup=lambda *args: {"pulsar_version": "0.16.0"}
    )
    runner.get_client_from_wrapper = lambda job_wrapper: client

    def find_container(job_wrapper, **kwargs):
        raise AssertionError("container resolved for a rejected job")

    runner._find_container = find_container
    runner._job_state = lambda job, job_wrapper: SimpleNamespace()

    def reject(**kwargs):
        raise InsufficientPermissionsException("Container 'busybox' is not allowed")

    failures = []
    job_wrapper = SimpleNamespace(
        job_id=1,
        tool=SimpleNamespace(id="cat", version="1.0", requires_galaxy_python_environment=False),
        prepare=reject,
        get_job=lambda: SimpleNamespace(resubmission_count=0),
        fail=lambda message, **kwargs: failures.append(message),
    )

    command_line, *_ = runner._PulsarJobRunner__prepare_job(job_wrapper, None)

    assert command_line is None
    assert failures == ["Container 'busybox' is not allowed"]
    assert runner.work_queue.empty()


@pytest.mark.parametrize(
    "destination_params, container, expected",
    [
        ({}, None, "remote"),
        ({"dependency_resolution": "local"}, None, "local"),
        ({}, MockContainer(), "none"),
        ({"dependency_resolution": "local"}, MockContainer(), "none"),
        ({}, MockContainer(resolve_dependencies=True), "remote"),
        ({"dependency_resolution": "local"}, MockContainer(resolve_dependencies=True), "local"),
        ({"dependency_resolution": "none"}, MockContainer(resolve_dependencies=True), "none"),
    ],
)
def test_dependency_resolution_skipped_for_containers(destination_params, container, expected):
    assert effective_dependency_resolution(destination_params, container) == expected


@pytest.mark.parametrize("container", [None, MockContainer()])
def test_unknown_dependency_resolution_rejected(container):
    with pytest.raises(Exception, match="Unknown dependency_resolution value encountered conda"):
        effective_dependency_resolution({"dependency_resolution": "conda"}, container)


def _failing_job_state():
    job_state = MagicMock(spec=["job_id", "job_wrapper", "runner_state", "job_destination", "runner_state_handled"])
    job_state.runner_state = None
    job_state.runner_state_handled = False
    job_state.job_wrapper.get_state.return_value = model.Job.states.RUNNING
    job_state.job_wrapper.get_job.return_value.finished = False
    return job_state


def _update(job_state, pulsar_status, full_status=None):
    runner = MagicMock()
    PulsarJobRunner._update_job_state_for_status(runner, job_state, pulsar_status, full_status=full_status)
    return runner


def _fail_message(runner):
    return runner.fail_job.call_args.kwargs["message"]


@pytest.mark.parametrize("full_status", [None, {"status": "failed"}])
def test_failure_without_runner_state_keeps_generic_message(full_status):
    job_state = _failing_job_state()
    runner = _update(job_state, "failed", full_status)
    assert job_state.runner_state is None
    assert _fail_message(runner) == FAILED_REMOTE_ERROR


@pytest.mark.parametrize(
    "runner_state",
    [
        JobState.runner_states.MEMORY_LIMIT_REACHED,
        JobState.runner_states.WALLTIME_REACHED,
        JobState.runner_states.NODE_FAILURE,
        JobState.runner_states.PREEMPTED,
        JobState.runner_states.CANCELLED,
    ],
)
def test_failure_with_runner_state_is_classified(runner_state):
    job_state = _failing_job_state()
    full_status = {"status": "failed", "runner_state": runner_state}
    runner = _update(job_state, "failed", full_status)
    assert job_state.runner_state == runner_state
    assert _fail_message(runner) == RUNNER_STATE_DEFINITIONS[runner_state].fail_message
    assert runner.fail_job.call_args.kwargs["full_status"] == full_status


def test_reason_without_definition_is_kept_for_resubmit_conditions():
    job_state = _failing_job_state()
    runner = _update(job_state, "failed", {"status": "failed", "runner_state": "from_the_future"})
    assert job_state.runner_state == "from_the_future"
    assert _fail_message(runner) == FAILED_REMOTE_ERROR


def test_malformed_runner_state_is_logged_and_ignored(caplog):
    job_state = _failing_job_state()
    with caplog.at_level(logging.WARNING):
        runner = _update(job_state, "failed", {"status": "failed", "runner_state": "not a reason; DROP"})
    assert job_state.runner_state is None
    assert _fail_message(runner) == FAILED_REMOTE_ERROR
    assert "malformed runner state" in caplog.text


def test_runner_state_message_is_preferred_over_the_definition():
    job_state = _failing_job_state()
    full_status = {
        "status": "failed",
        "runner_state": JobState.runner_states.MEMORY_LIMIT_REACHED,
        "runner_state_message": "Held by the pool for exceeding request_memory",
    }
    runner = _update(job_state, "failed", full_status)
    assert job_state.runner_state == JobState.runner_states.MEMORY_LIMIT_REACHED
    assert _fail_message(runner) == "Held by the pool for exceeding request_memory"


def test_runner_state_message_without_a_reason_is_shown():
    job_state = _failing_job_state()
    runner = _update(
        job_state, "failed", {"status": "failed", "runner_state_message": "Slurm reported: RaisedSignal:9"}
    )
    assert job_state.runner_state is None
    assert _fail_message(runner) == "Slurm reported: RaisedSignal:9"


def test_lost_job_ignores_runner_state():
    job_state = _failing_job_state()
    runner = _update(job_state, "lost", {"status": "lost", "runner_state": JobState.runner_states.MEMORY_LIMIT_REACHED})
    assert job_state.runner_state is None
    assert _fail_message(runner) == LOST_REMOTE_ERROR


def _polling_runner(client):
    runner = MagicMock()
    runner.get_client_from_state.return_value = client
    return runner


def test_polling_passes_full_status_for_failed_jobs():
    full_status = {"status": "failed", "runner_state": JobState.runner_states.MEMORY_LIMIT_REACHED}
    client = MagicMock()
    client.get_status.return_value = "failed"
    client.full_status.return_value = full_status
    runner = _polling_runner(client)
    job_state = _failing_job_state()
    PulsarJobRunner.check_watched_item_state(runner, job_state)
    runner._update_job_state_for_status.assert_called_once_with(job_state, "failed", full_status=full_status)


def test_polling_still_fails_job_when_full_status_unavailable():
    client = MagicMock()
    client.get_status.return_value = "failed"
    client.full_status.side_effect = OSError("gone away")
    runner = _polling_runner(client)
    job_state = _failing_job_state()
    PulsarJobRunner.check_watched_item_state(runner, job_state)
    runner._update_job_state_for_status.assert_called_once_with(job_state, "failed", full_status=None)


def test_polling_does_not_fetch_full_status_of_running_jobs():
    client = MagicMock()
    client.get_status.return_value = "running"
    PulsarJobRunner.check_watched_item_state(_polling_runner(client), _failing_job_state())
    client.full_status.assert_not_called()


def _tool_failure_runner(job_state, handled):
    runner = MagicMock()

    def handle(_, state):
        state.runner_state_handled = handled

    runner._handle_runner_state.side_effect = handle
    return runner


RESULT = PulsarFinishJobResult(
    tool_stdout="o",
    tool_stderr="e",
    exit_code=42,
    job_stdout="",
    job_stderr="",
    remote_metadata_directory=None,
    job_metrics_directory="",
)
resubmitted_for_tool_failure = PulsarJobRunner._resubmitted_for_tool_failure


@pytest.mark.parametrize(
    "detected_state,expected_runner_state",
    [
        (DETECTED_JOB_STATE.OUT_OF_MEMORY_ERROR, JobState.runner_states.MEMORY_LIMIT_REACHED),
        (DETECTED_JOB_STATE.GENERIC_ERROR, JobState.runner_states.TOOL_DETECT_ERROR),
    ],
)
def test_tool_detected_failures_reach_resubmission(detected_state, expected_runner_state):
    job_state = _failing_job_state()
    job_state.job_destination.resubmit = [{"condition": "memory_limit_reached"}]
    job_state.job_wrapper.check_tool_output.return_value = detected_state
    runner = _tool_failure_runner(job_state, handled=True)
    assert resubmitted_for_tool_failure(runner, job_state, RESULT) is True
    assert job_state.runner_state == expected_runner_state
    runner._handle_runner_state.assert_called_once_with("failure", job_state)


def test_unhandled_tool_failure_finishes_normally():
    job_state = _failing_job_state()
    job_state.job_destination.resubmit = [{"condition": "memory_limit_reached"}]
    job_state.job_wrapper.check_tool_output.return_value = DETECTED_JOB_STATE.GENERIC_ERROR
    runner = _tool_failure_runner(job_state, handled=False)
    assert resubmitted_for_tool_failure(runner, job_state, RESULT) is False


def test_successful_tool_is_not_resubmitted():
    job_state = _failing_job_state()
    job_state.job_destination.resubmit = [{"condition": "any_failure"}]
    job_state.job_wrapper.check_tool_output.return_value = DETECTED_JOB_STATE.OK
    runner = _tool_failure_runner(job_state, handled=True)
    assert resubmitted_for_tool_failure(runner, job_state, RESULT) is False
    runner._handle_runner_state.assert_not_called()


def test_destination_without_resubmit_skips_output_check():
    job_state = _failing_job_state()
    job_state.job_destination.resubmit = []
    runner = _tool_failure_runner(job_state, handled=True)
    assert resubmitted_for_tool_failure(runner, job_state, RESULT) is False
    job_state.job_wrapper.check_tool_output.assert_not_called()


def test_job_already_finished_is_not_resubmitted():
    job_state = _failing_job_state()
    job_state.job_destination.resubmit = [{"condition": "any_failure"}]
    job_state.job_wrapper.get_job.return_value.finished = True
    runner = _tool_failure_runner(job_state, handled=True)
    assert resubmitted_for_tool_failure(runner, job_state, RESULT) is False


def test_client_from_wrapper_reports_resubmission_count():
    runner = _runner()
    job = SimpleNamespace(user=None, resubmission_count=2)
    job_wrapper = SimpleNamespace(
        job_id=543,
        get_job=lambda: job,
        job_destination=SimpleNamespace(params={"url": "http://pulsar.example"}, env=[]),
    )
    runner.get_client_from_wrapper(job_wrapper)
    destination_params, _kwargs = runner.client_manager.calls[0]
    assert destination_params["resubmission_count"] == 2
    # The destination itself stays untouched, it is persisted and reused.
    assert "resubmission_count" not in job_wrapper.job_destination.params


discard_previous_attempt = PulsarJobRunner._PulsarJobRunner__discard_previous_attempt  # type: ignore[attr-defined]


def test_discard_previous_attempt_cleans_the_remote_job():
    client = MagicMock()
    discard_previous_attempt(client, SimpleNamespace(job_id=543))
    client.clean.assert_called_once_with()


def test_discard_previous_attempt_tolerates_nothing_to_clean():
    client = MagicMock()
    client.clean.side_effect = KeyError("543")
    discard_previous_attempt(client, SimpleNamespace(job_id=543))
