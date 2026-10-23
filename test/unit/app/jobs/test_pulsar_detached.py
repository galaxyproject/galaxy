"""Capability-gated detached execution through the stock Pulsar runner."""

import datetime
import json
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pulsar.client.client import JobClient
from pulsar.client.server_interface import (
    HttpPulsarInterface,
    LocalPulsarInterface,
)
from pulsar.managers import ManagerProxy

from galaxy import model
from galaxy.jobs.runners import pulsar as runner_module
from galaxy.jobs.runners.pulsar import (
    DETACHED_LOCAL_CAPABILITIES,
    PulsarEmbeddedJobRunner,
    PulsarFinishJobResult,
)
from galaxy.tool_util.deps.container_classes import (
    DockerContainer,
    SingularityContainer,
)

CAPABILITIES = {
    "schema": 1,
    "asynchronous_cancel": True,
    "collection_ack": True,
    "execution_policy": True,
}


def wrapper_and_runner(tmp_path, *, detached=True, state=model.Job.states.RUNNING):
    runner = object.__new__(PulsarEmbeddedJobRunner)
    params = {DETACHED_LOCAL_CAPABILITIES: CAPABILITIES.copy()} if detached else {}
    job = SimpleNamespace(
        id=42,
        destination_params=params,
        job_runner_external_id="unique-attempt",
        get_job_runner_external_id=lambda: "unique-attempt",
        output_datasets=[],
        output_library_datasets=[],
        finished=False,
    )
    wrapper = SimpleNamespace(
        job_id=42,
        working_directory=str(tmp_path),
        tool_working_directory=str(tmp_path / "working"),
        job_destination=SimpleNamespace(params=params),
        state=state,
        get_job=lambda: job,
        cleanup_job="onsuccess",
        change_state=Mock(),
        fail=Mock(),
        tool=SimpleNamespace(timelimit=None),
        extra_filenames=[],
    )
    wrapper.get_state = lambda: wrapper.state
    client = Mock()
    client.acknowledge_collection.return_value = {"acknowledged": True}
    runner.get_client_from_state = Mock(return_value=client)
    runner.get_client = Mock(return_value=client)
    runner.mark_as_finished = Mock()
    runner.fail_job = Mock()
    job_state = SimpleNamespace(job_id="unique-attempt", job_wrapper=wrapper, running=False)
    return runner, client, wrapper, job_state


@pytest.mark.parametrize("status", [None, "queued", "running"])
def test_async_stop_waits_for_terminal_confirmation(tmp_path, status):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path, state=model.Job.states.STOPPED)
    assert runner._update_job_state_for_status(job_state, status) is job_state
    client.kill.assert_called_once_with()
    runner.mark_as_finished.assert_not_called()
    wrapper.change_state.assert_not_called()


@pytest.mark.parametrize("status", ["complete", "cancelled"])
def test_terminal_confirmation_allows_collection(tmp_path, status):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path, state=model.Job.states.STOPPED)
    assert runner._update_job_state_for_status(job_state, status) is None
    runner.mark_as_finished.assert_called_once_with(job_state)
    client.kill.assert_not_called()


def test_cancel_error_is_retried_without_collecting(tmp_path):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path, state=model.Job.states.STOPPED)
    client.kill.side_effect = OSError("daemon unavailable")
    assert runner._update_job_state_for_status(job_state, "running") is job_state
    runner.mark_as_finished.assert_not_called()


def test_confirmed_resource_failure_is_not_treated_as_user_stop(tmp_path):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path, state=model.Job.states.STOPPED)
    assert runner._update_job_state_for_status(job_state, "failed") is None
    runner.fail_job.assert_called_once()
    runner.mark_as_finished.assert_not_called()


def test_confirmed_failure_retains_worker_diagnostic_in_galaxy_streams(tmp_path):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path)
    client.get_status.return_value = "failed"
    response = {"status": "failed", "stderr": "", "job_stderr": "Detached execution: Execution exceeded walltime limit"}
    client.full_status.return_value = response
    assert runner.check_watched_item_state(job_state) is None
    failure = runner.fail_job.call_args.kwargs["full_status"]
    assert "exceeded walltime limit" in failure["stderr"]
    assert response["stderr"] == ""
    client.full_status.assert_called_once_with()
    runner.mark_as_finished.assert_not_called()


def test_lost_identity_is_retained_for_inspection(tmp_path):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path)
    assert runner._update_job_state_for_status(job_state, "lost") is job_state
    runner.fail_job.assert_not_called()
    runner.mark_as_finished.assert_not_called()


@pytest.mark.parametrize("detached", [False, True])
def test_unknown_state_is_retained_only_for_capable_manager(tmp_path, detached):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path, detached=detached)
    client.get_status.side_effect = OSError("unreadable status")
    assert runner.check_watched_item_state(job_state) is (job_state if detached else None)
    assert runner.mark_as_finished.called is not detached


def test_ordinary_manager_retains_synchronous_stop(tmp_path):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path, detached=False, state=model.Job.states.STOPPED)
    assert runner._update_job_state_for_status(job_state, "running") is None
    client.kill.assert_called_once_with()
    runner.mark_as_finished.assert_called_once_with(job_state)


def test_stop_uses_galaxy_id_and_recorded_attempt(tmp_path):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path)
    runner.stop_job(wrapper)
    runner.get_client.assert_called_once_with(wrapper.get_job().destination_params, 42, external_id="unique-attempt")
    client.kill.assert_called_once_with()


@pytest.mark.parametrize("detached", [False, True])
def test_recovery_addresses_attempt_without_changing_file_authentication(tmp_path, detached):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path, detached=detached)
    # Invoke the real method rather than the convenience fixture's mock.
    runner.app = SimpleNamespace(
        config=SimpleNamespace(nginx_upload_job_files_path=None),
        security=SimpleNamespace(encode_id=lambda value, kind=None: f"{kind or 'id'}-{value}"),
    )
    runner.galaxy_url = "http://galaxy.invalid"
    runner.client_manager = Mock()
    PulsarEmbeddedJobRunner.get_client(runner, wrapper.job_destination.params, 42, external_id="unique-attempt")
    params = runner.client_manager.get_client.call_args.kwargs
    assert params["job_id"] == ("unique-attempt" if detached else "42")
    assert params["external_id"] == "unique-attempt"
    assert "/api/jobs/id-42/files?job_key=jobs_files-42" in params["files_endpoint"]
    assert "/api/jobs/id-42/oidc-tokens?job_key=jobs_token-42" in params["token_endpoint"]


def submission_case(tmp_path, monkeypatch, detached=True):
    runner, client, wrapper, unused = wrapper_and_runner(tmp_path, detached=detached)
    job = wrapper.get_job()
    job.job_runner_external_id = None
    wrapper.tool.required_files = None
    wrapper.tool.tool_dir = None
    wrapper.environment_variables = []
    wrapper.guest_ports = []
    wrapper.app = SimpleNamespace(config=SimpleNamespace(redact_email_in_job_name=True))
    wrapper.get_id_tag = lambda: "42"
    wrapper.tool.old_id = "ordinary_tool"
    client.env = []
    client.destination_params = {"dependency_resolution": "none"}
    runner.app = SimpleNamespace(config=SimpleNamespace(metadata_strategy="extended"))
    runner._populate_parameter_defaults = Mock()
    remote_config = {"job_id": "attempt-generated", "pulsar_version": "0.16.0"}
    runner._PulsarJobRunner__prepare_job = lambda *args: ("command", client, remote_config, None, None)
    runner._PulsarJobRunner__dependencies_description = lambda *args: None
    runner._PulsarJobRunner__client_outputs = lambda *args: object()
    runner.get_input_files = lambda *args: []
    runner.monitor_job = Mock()
    monkeypatch.setattr(runner_module.PulsarPlugin, "write_version_target", Mock())
    monkeypatch.setattr(runner_module, "ClientJobDescription", Mock())

    def persist(destination, external_id, **kwargs):
        assert kwargs["flush"] is True
        job.job_runner_external_id = external_id

    wrapper.set_job_destination = persist
    return runner, client, wrapper


@pytest.mark.parametrize("detached", [False, True])
def test_attempt_is_committed_before_detached_launch_can_execute(tmp_path, monkeypatch, detached):
    class SimulatedRestart(BaseException):
        pass

    runner, client, wrapper = submission_case(tmp_path, monkeypatch, detached)
    job = wrapper.get_job()

    def launch(*args):
        # Simulate interruption after server acceptance but before the client
        # returns. The detached attempt must already be recoverable by ID.
        assert job.job_runner_external_id == ("attempt-generated" if detached else None)
        raise SimulatedRestart()

    monkeypatch.setattr(runner_module, "pulsar_submit_job", launch)
    with pytest.raises(SimulatedRestart):
        runner.queue_job(wrapper)


@pytest.mark.parametrize("detached", [False, True])
def test_submission_disconnect_monitors_saved_attempt_without_replay(tmp_path, monkeypatch, detached):
    runner, client, wrapper = submission_case(tmp_path, monkeypatch, detached)
    accepted = []

    def accept_then_disconnect(client, description, configuration):
        accepted.append(configuration["job_id"])
        raise OSError("response lost after remote execution started")

    monkeypatch.setattr(runner_module, "pulsar_submit_job", accept_then_disconnect)
    runner.queue_job(wrapper)
    if not detached:
        wrapper.fail.assert_called_once()
        runner.monitor_job.assert_not_called()
        return
    wrapper.fail.assert_not_called()
    monitored = runner.monitor_job.call_args.args[0]
    assert monitored.job_id == wrapper.get_job().job_runner_external_id == "attempt-generated"
    client.get_status.side_effect = ["running", "complete"]
    assert runner.check_watched_item_state(monitored) is monitored
    assert runner.check_watched_item_state(monitored) is None
    runner.mark_as_finished.assert_called_once_with(monitored)
    assert accepted == ["attempt-generated"]


def test_destination_commit_error_after_submit_also_monitors_saved_attempt(tmp_path, monkeypatch):
    runner, client, wrapper = submission_case(tmp_path, monkeypatch)
    original_persist = wrapper.set_job_destination
    wrapper.sa_session = Mock()
    persisted = []

    def persist(*args, **kwargs):
        persisted.append(kwargs["external_id"])
        if len(persisted) > 1:
            # Monitor registration must not need a live database once the
            # command has been accepted and its earlier attempt ID committed.
            wrapper.get_id_tag = Mock(side_effect=OSError("database remains unavailable"))
            raise OSError("database unavailable after launch")
        original_persist(*args, **kwargs)

    wrapper.set_job_destination = persist
    submitted = Mock(return_value="attempt-generated")
    monkeypatch.setattr(runner_module, "pulsar_submit_job", submitted)
    runner.queue_job(wrapper)
    wrapper.fail.assert_not_called()
    assert runner.monitor_job.call_args.args[0].job_id == "attempt-generated"
    wrapper.sa_session.rollback.assert_called_once_with()
    submitted.assert_called_once()


def test_failure_before_attempt_commit_keeps_normal_submission_failure(tmp_path, monkeypatch):
    runner, client, wrapper = submission_case(tmp_path, monkeypatch)
    monkeypatch.setattr(
        runner_module, "ClientJobDescription", Mock(side_effect=ValueError("invalid input description"))
    )
    runner.queue_job(wrapper)
    wrapper.fail.assert_called_once()
    runner.monitor_job.assert_not_called()
    assert wrapper.get_job().job_runner_external_id is None


def resolved_execution_policy(tmp_path, container_class):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path)
    runner.app = SimpleNamespace(
        job_config=SimpleNamespace(
            limits=SimpleNamespace(walltime_delta=datetime.timedelta(seconds=60), output_size=4096)
        )
    )
    wrapper.tool.timelimit = 30
    runner.get_output_files = lambda unused: ["/galaxy/output.dat"]
    mapper = SimpleNamespace(remote_output_path_rewrite=lambda path: path.replace("/galaxy", "/pulsar/attempt/outputs"))
    container = container_class("image", None, None, {}, None, None, container_name="tool-token")
    metadata = DockerContainer(
        "metadata-image",
        None,
        None,
        {"docker_host": "unix:///docker.sock"},
        None,
        None,
        container_name="metadata-token",
    )
    runner._write_detached_execution_configuration(
        wrapper,
        {"job_directory": "/pulsar/attempt"},
        SimpleNamespace(path_mapper=mapper),
        container,
        metadata,
    )
    policy_path = tmp_path / "configs/detached_execution.json"
    policy = json.loads(policy_path.read_text())
    return policy, wrapper, container


@pytest.mark.parametrize("container_class", [DockerContainer, SingularityContainer])
def test_policy_uses_resolved_containers_and_effective_limits(tmp_path, container_class):
    policy, wrapper, container = resolved_execution_policy(tmp_path, container_class)
    assert policy["schema"] == 1
    assert policy["limits"] == {
        "walltime_seconds": 30,
        "output_size_bytes": 4096,
        "output_paths": ["/pulsar/attempt/outputs/output.dat"],
    }
    expected_roles = ["tool", "metadata"] if container_class is DockerContainer else ["metadata"]
    assert [entry["role"] for entry in policy["containers"]] == expected_roles
    if container_class is DockerContainer:
        assert policy["containers"][0]["container_name"] == container.container_name
        assert policy["containers"][0]["container_type"] == container.container_type
    assert policy["containers"][-1]["connection_configuration"]["host"] == "unix:///docker.sock"
    assert all(entry["expected_mount"] == "/pulsar/attempt" for entry in policy["containers"])
    assert wrapper.extra_filenames == [str(tmp_path / "configs/detached_execution.json")]


@pytest.mark.parametrize("container_class", [DockerContainer, SingularityContainer])
def test_execution_policy_matches_detached_worker_contract(tmp_path, container_class):
    worker = pytest.importorskip(
        "pulsar.managers.util.detached_worker",
        reason="Installed Pulsar does not implement detached local execution",
    )
    policy = resolved_execution_policy(tmp_path, container_class)[0]

    # Both native Docker and foreground Apptainer command policies must pass
    # the actual worker's contract, including a separate metadata container.
    worker._validate_manifest(
        {
            **policy,
            "job_id": "attempt",
            "token": "a" * 32,
            "job_directory": "/pulsar/attempt",
            "command_script": "/pulsar/attempt/command.sh",
            "stdout": "/pulsar/attempt/stdout",
            "stderr": "/pulsar/attempt/stderr",
            "environment": {},
            "host_identity": worker.host_identity(),
        }
    )


def test_host_policy_without_limits_or_containers(tmp_path):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path)
    runner.app = SimpleNamespace(
        job_config=SimpleNamespace(limits=SimpleNamespace(walltime_delta=None, output_size=None))
    )
    runner.get_output_files = lambda unused: []
    runner._write_detached_execution_configuration(wrapper, {"job_directory": "/attempt"}, None, None, None)
    policy = json.loads(Path(wrapper.extra_filenames[0]).read_text())
    assert policy == {
        "schema": 1,
        "containers": [],
        "limits": {"walltime_seconds": None, "output_size_bytes": None, "output_paths": []},
    }


def finish_result():
    return PulsarFinishJobResult("stdout", "stderr", 0, "", "", "/attempt/metadata", "metadata")


def test_metadata_and_import_precede_ack_and_cleanup(tmp_path):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path)
    events = []
    runner._handle_metadata_externally = lambda *args, **kwargs: events.append("metadata")

    def finish(*args, **kwargs):
        assert not client.acknowledge_collection.called
        events.append("import")
        wrapper.state = model.Job.states.OK

    wrapper.finish = finish
    client.acknowledge_collection.side_effect = lambda: events.append("ack") or {"acknowledged": True}
    client.clean.side_effect = lambda: events.append("clean")
    runner._complete_staged_job(wrapper, finish_result())
    assert events == ["metadata", "import", "ack", "clean"]


@pytest.mark.parametrize("output_state", [model.Dataset.states.ERROR, model.Dataset.states.FAILED_METADATA])
def test_failed_metadata_retains_staging(tmp_path, output_state):
    runner, client, wrapper, job_state = wrapper_and_runner(tmp_path, state=model.Job.states.OK)
    wrapper.get_job().output_datasets.append(SimpleNamespace(dataset=SimpleNamespace(state=output_state)))
    runner._acknowledge_staged_collection(wrapper)
    client.acknowledge_collection.assert_not_called()
    client.clean.assert_not_called()


@pytest.mark.parametrize("job_state", [model.Job.states.ERROR, model.Job.states.FINISHING, model.Job.states.RUNNING])
def test_unfinished_or_failed_import_never_acknowledges(tmp_path, job_state):
    runner, client, wrapper, unused = wrapper_and_runner(tmp_path, state=job_state)
    runner._acknowledge_staged_collection(wrapper)
    client.acknowledge_collection.assert_not_called()
    client.clean.assert_not_called()


@pytest.mark.parametrize("response", [{"acknowledged": False}, OSError("offline")])
def test_unconfirmed_ack_retains_staging_without_failing_finished_job(tmp_path, response):
    runner, client, wrapper, unused = wrapper_and_runner(tmp_path, state=model.Job.states.OK)
    if isinstance(response, Exception):
        client.acknowledge_collection.side_effect = response
    else:
        client.acknowledge_collection.return_value = response
    runner._acknowledge_staged_collection(wrapper)
    client.clean.assert_not_called()
    wrapper.fail.assert_not_called()


def test_never_cleanup_acknowledges_but_retains_staging(tmp_path):
    runner, client, wrapper, unused = wrapper_and_runner(tmp_path, state=model.Job.states.OK)
    wrapper.cleanup_job = "never"
    runner._acknowledge_staged_collection(wrapper)
    client.acknowledge_collection.assert_called_once_with()
    client.clean.assert_not_called()


def test_finish_exception_prevents_acknowledgment(tmp_path):
    runner, client, wrapper, unused = wrapper_and_runner(tmp_path)
    wrapper.finish = Mock(side_effect=RuntimeError("import failed"))
    runner._complete_staged_job(wrapper, finish_result(), handle_metadata_externally=False)
    wrapper.fail.assert_called_once()
    client.acknowledge_collection.assert_not_called()


@pytest.mark.parametrize("detached", [False, True])
def test_finishing_recovery_preserves_remote_attempt_metadata(tmp_path, detached):
    runner, client, wrapper, job_state = wrapper_and_runner(
        tmp_path, detached=detached, state=model.Job.states.FINISHING
    )
    job = wrapper.get_job()
    job.get_state = wrapper.get_state
    job.get_command_line = lambda: "command"
    runner._job_state = lambda *args: job_state
    runner.work_queue = Queue()
    runner.recover(job, wrapper)
    method, recovered = runner.work_queue.get_nowait()
    assert method == (runner.finish_job if detached else runner._finish_staged_job)
    assert recovered is job_state


@pytest.mark.parametrize("detached", [False, True])
def test_unstaging_cleanup_is_deferred_only_for_capable_manager(tmp_path, monkeypatch, detached):
    runner, client, wrapper, unused = wrapper_and_runner(tmp_path, detached=detached)
    from galaxy.jobs.runners import AsynchronousJobState

    job_state = AsynchronousJobState(job_wrapper=None, job_destination=wrapper.job_destination, job_id="unique-attempt")
    job_state.job_wrapper = wrapper
    client.full_status.return_value = {
        "returncode": 0,
        "stdout": "",
        "stderr": "",
        "system_properties": {},
        "working_directory": "/attempt/working",
    }
    client.destination_params = {}
    runner._PulsarJobRunner__client_outputs = lambda *args: object()
    runner._complete_staged_job = Mock()
    stage = Mock(return_value=[])
    monkeypatch.setattr(runner_module, "pulsar_finish_job", stage)
    runner.finish_job(job_state)
    assert stage.call_args.kwargs["cleanup_job"] == ("never" if detached else "onsuccess")
    runner._complete_staged_job.assert_called_once()


@pytest.mark.skipif(
    not callable(getattr(JobClient, "acknowledge_collection", None)),
    reason="Installed Pulsar does not implement collection acknowledgment",
)
def test_acknowledgment_forwarded_through_real_client_proxy_and_local_route():
    manager = SimpleNamespace(acknowledge_collection=Mock(return_value=True))
    interface = LocalPulsarInterface({}, job_manager=ManagerProxy(manager))
    client = JobClient({}, "attempt-token", interface)
    assert client.acknowledge_collection() == {"acknowledged": True}
    assert client.acknowledge_collection() == {"acknowledged": True}
    assert manager.acknowledge_collection.call_args_list == [(("attempt-token",),), (("attempt-token",),)]


@pytest.mark.skipif(
    not callable(getattr(JobClient, "acknowledge_collection", None)),
    reason="Installed Pulsar does not implement collection acknowledgment",
)
def test_acknowledgment_has_explicit_http_method_and_endpoint():
    transport = Mock()
    transport.execute.return_value = '{"acknowledged":true}'
    client = JobClient({}, "attempt-token", HttpPulsarInterface({"url": "http://pulsar.invalid"}, transport))
    assert client.acknowledge_collection() == {"acknowledged": True}
    args, kwargs = transport.execute.call_args
    assert args[0].startswith("http://pulsar.invalid/jobs/attempt-token/collection?")
    assert kwargs["method"] == "PUT"
