"""Unit tests for Pulsar job runner utility methods and client construction."""

from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

from galaxy.jobs.runners import (
    AsynchronousJobState,
    pulsar as pulsar_module,
)
from galaxy.jobs.runners.pulsar import PulsarJobRunner


def _container(container_id, image_identifier_is_path=True):
    return SimpleNamespace(container_id=container_id, image_identifier_is_path=image_identifier_is_path)


class _ComputeEnvironment:
    """Minimal stand-in exposing only container_path_rewrite."""

    def __init__(self, rewrites):
        self._rewrites = rewrites

    def container_path_rewrite(self, path):
        return self._rewrites.get(path)


IMAGE = "/cvmfs/singularity.galaxyproject.org/all/img"
REWRITTEN = "/job/dir/.cvmfsexec/dist/cvmfs/singularity.galaxyproject.org/all/img"


def test_rewrite_container_applies_compute_environment_rewrite():
    container = _container(IMAGE)
    compute_environment = _ComputeEnvironment({IMAGE: REWRITTEN})
    PulsarJobRunner._rewrite_container_for_compute_environment(container, compute_environment)
    assert container.container_id == REWRITTEN


def test_rewrite_container_noop_without_matching_rule():
    # container_path_rewrite returns None when no file_actions rule matches.
    container = _container(IMAGE)
    compute_environment = _ComputeEnvironment({})
    PulsarJobRunner._rewrite_container_for_compute_environment(container, compute_environment)
    assert container.container_id == IMAGE


def test_rewrite_container_noop_when_identifier_not_a_path():
    # A registry/docker:// identifier is resolved by the compute node itself;
    # never route it through the path rewriter even if a rule would match.
    container = _container("docker://quay.io/biocontainers/bwa", image_identifier_is_path=False)
    compute_environment = _ComputeEnvironment({"docker://quay.io/biocontainers/bwa": REWRITTEN})
    PulsarJobRunner._rewrite_container_for_compute_environment(container, compute_environment)
    assert container.container_id == "docker://quay.io/biocontainers/bwa"


def test_rewrite_container_noop_without_compute_environment():
    # No compute environment => not rewrite_parameters mode; leave image as-is.
    container = _container(IMAGE)
    PulsarJobRunner._rewrite_container_for_compute_environment(container, None)
    assert container.container_id == IMAGE


def test_rewrite_container_noop_without_container():
    # Should not raise when there is no resolved container.
    compute_environment = _ComputeEnvironment({IMAGE: REWRITTEN})
    PulsarJobRunner._rewrite_container_for_compute_environment(None, compute_environment)


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


def test_finish_job_stages_outputs_before_external_metadata(monkeypatch, tmp_path):
    events: list[Any] = []
    client = SimpleNamespace(
        destination_params={"remote_metadata": False},
        full_status=lambda: {
            "stdout": "tool stdout",
            "stderr": "tool stderr",
            "job_stdout": "job stdout",
            "job_stderr": "job stderr",
            "returncode": 0,
        },
    )
    job_wrapper = SimpleNamespace(
        working_directory=str(tmp_path),
        job_id=42,
        cleanup_job="always",
        get_state=lambda: "running",
    )
    job_state = object.__new__(AsynchronousJobState)
    job_state.job_wrapper = job_wrapper
    job_state.job_id = "remote-42"
    runner = cast(Any, object.__new__(PulsarJobRunner))
    runner.get_client_from_state = lambda _: client
    runner._PulsarJobRunner__client_outputs = lambda *args: "client outputs"
    runner._handle_metadata_externally = lambda *args, **kwargs: events.append("metadata")
    runner._finish_pulsar_job = lambda wrapper, result: events.append(("finish", result))
    monkeypatch.setattr(
        pulsar_module.PulsarOutputs,
        "from_status_response",
        lambda _: "pulsar outputs",
    )

    def stage_outputs(**kwargs):
        events.append(("stage", kwargs))
        return False

    monkeypatch.setattr(pulsar_module, "pulsar_finish_job", stage_outputs)

    runner.finish_job(job_state)

    assert [event[0] if isinstance(event, tuple) else event for event in events] == ["stage", "metadata", "finish"]
    _, stage_kwargs = events[0]
    assert stage_kwargs == {
        "client": client,
        "job_completed_normally": True,
        "cleanup_job": "always",
        "client_outputs": "client outputs",
        "pulsar_outputs": "pulsar outputs",
    }
    _, result = events[2]
    assert result.tool_stdout == "tool stdout"
    assert result.tool_stderr == "tool stderr"
    assert result.exit_code == 0
    assert result.job_stdout == "job stdout"
    assert result.job_stderr == "job stderr"
    assert result.job_metrics_directory == str(tmp_path / "metadata")
    assert (tmp_path / "galaxy_42.ec").read_text() == "0"
