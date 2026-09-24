"""Unit tests for Pulsar job runner utility methods and client construction."""

from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

import pytest

from galaxy.exceptions import ConfigurationError
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
