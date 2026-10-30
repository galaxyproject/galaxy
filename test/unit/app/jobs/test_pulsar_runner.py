"""Unit tests for Pulsar job runner utility methods and client construction."""

import os
from types import SimpleNamespace
from typing import (
    Any,
    cast,
)
from urllib.parse import (
    parse_qs,
    urlparse,
)
from uuid import uuid4

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
from galaxy.exceptions import ConfigurationError
from galaxy.job_execution.datasets import DatasetPath
from galaxy.job_metrics.instrumenters.pulsar import PulsarPlugin
from galaxy.jobs.runners import (
    AsynchronousJobState,
    pulsar as pulsar_runner,
)
from galaxy.jobs.runners.pulsar import (  # type: ignore[attr-defined]
    build_client_manager,
    PulsarComputeEnvironment,
    PulsarJobRunner,
)
from galaxy.model import HistoryDatasetAssociation
from galaxy.model.metadata import MetadataTempFile
from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.security.staging_signer import StagingUrlSigner


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


# Staging inputs by object store identity (``object_store_staging``).

STAGING_SECRET = "1234567890abcdef"
INPUT_CACHE_PATH = "/galaxy/cache/0/00/dataset_5.dat"
METADATA_CACHE_PATH = "/galaxy/cache/_metadata_files/0/00/metadata_9.dat"


class _RecordingJobIO:
    def __init__(self, input_paths):
        self.input_paths = input_paths
        self.sync_cache = None

    def get_input_paths(self, materialized_objects, sync_cache=True):
        self.sync_cache = sync_cache
        return self.input_paths

    def get_input_path(self, dataset, sync_cache=True):
        self.sync_cache = sync_cache
        return INPUT_CACHE_PATH


def _staging_runner():
    runner = cast(Any, object.__new__(PulsarJobRunner))
    runner.app = SimpleNamespace(security=IdEncodingHelper(id_secret=STAGING_SECRET))
    runner.galaxy_url = "http://galaxy.example"
    return runner


def _staging_job_wrapper(dataset_id=5):
    input_path = DatasetPath(dataset_id, INPUT_CACHE_PATH, dataset_uuid=uuid4(), object_store_id="s3")
    return SimpleNamespace(job_id=7, job_io=_RecordingJobIO([input_path]))


def _staging_compute_environment(staging, metadata_file_ids=None):
    metadata_file_ids = metadata_file_ids or {}
    return SimpleNamespace(
        object_store_staging=staging,
        materialized_objects={},
        path_rewrites_input_extra={},
        path_rewrites_input_metadata={path: f"/pulsar/inputs/{os.path.basename(path)}" for path in metadata_file_ids},
        input_metadata_file_ids=metadata_file_ids,
    )


def _assert_signed_input_url(url, kind, object_id, redirect):
    security = IdEncodingHelper(id_secret=STAGING_SECRET)
    parsed = urlparse(url)
    assert parsed.path == f"/api/jobs/{security.encode_id(7)}/staging/inputs/{kind}/{security.encode_id(object_id)}"
    query = parse_qs(parsed.query)
    assert StagingUrlSigner(STAGING_SECRET).verify(7, kind, object_id, "", int(query["exp"][0]), query["sig"][0])
    assert (query.get("redirect") == ["1"]) is redirect


def test_inputs_are_staged_from_signed_urls_without_pulling_them():
    runner, job_wrapper = _staging_runner(), _staging_job_wrapper()
    client_inputs = runner._client_inputs(job_wrapper, _staging_compute_environment("stream"), {})
    (client_input,) = list(client_inputs)
    assert client_input.path == INPUT_CACHE_PATH
    _assert_signed_input_url(client_input.url, "dataset", 5, redirect=False)
    assert job_wrapper.job_io.sync_cache is False


def test_redirect_is_requested_from_a_pulsar_that_follows_redirects():
    runner = _staging_runner()
    remote_job_config = {"pulsar_version": "0.15.16"}
    client_inputs = runner._client_inputs(
        _staging_job_wrapper(), _staging_compute_environment("redirect"), remote_job_config
    )
    _assert_signed_input_url(next(iter(client_inputs)).url, "dataset", 5, redirect=True)


def test_redirect_is_not_requested_from_a_pulsar_that_cannot_follow_it():
    runner = _staging_runner()
    remote_job_config = {"pulsar_version": "0.15.15"}
    client_inputs = runner._client_inputs(
        _staging_job_wrapper(), _staging_compute_environment("redirect"), remote_job_config
    )
    _assert_signed_input_url(next(iter(client_inputs)).url, "dataset", 5, redirect=False)


def test_input_metadata_files_are_staged_from_signed_urls():
    runner = _staging_runner()
    compute_environment = _staging_compute_environment("stream", {METADATA_CACHE_PATH: 9})
    client_inputs = runner._client_inputs(_staging_job_wrapper(), compute_environment, {})
    metadata_input = next(i for i in client_inputs if i.path == METADATA_CACHE_PATH)
    _assert_signed_input_url(metadata_input.url, "metadata_file", 9, redirect=False)


def test_materialized_inputs_keep_path_staging():
    # A deferred input materialized into the job directory has no object store identity.
    runner = _staging_runner()
    client_inputs = runner._client_inputs(
        _staging_job_wrapper(dataset_id=None), _staging_compute_environment("stream"), {}
    )
    assert next(iter(client_inputs)).url is None


def test_inputs_keep_path_staging_without_object_store_staging():
    runner, job_wrapper = _staging_runner(), _staging_job_wrapper()
    compute_environment = _staging_compute_environment(None, {METADATA_CACHE_PATH: 9})
    client_inputs = runner._client_inputs(job_wrapper, compute_environment, {})
    assert [client_input.url for client_input in client_inputs] == [None, None]
    assert job_wrapper.job_io.sync_cache is True


def _staging_compute_environment_for_rewrites(staging):
    compute_environment = cast(Any, object.__new__(PulsarComputeEnvironment))
    compute_environment.object_store_staging = staging
    compute_environment.job_wrapper = SimpleNamespace(job_io=_RecordingJobIO([]))
    compute_environment.local_path_config = SimpleNamespace(input_path_rewrite=lambda dataset: INPUT_CACHE_PATH)
    compute_environment.path_mapper = SimpleNamespace(
        remote_input_path_rewrite=lambda path, **kwd: f"/pulsar/inputs/{os.path.basename(path)}"
    )
    compute_environment.path_rewrites_input_metadata = {}
    compute_environment.input_metadata_file_ids = {}
    return compute_environment


def test_input_path_rewrite_does_not_pull_an_input_staged_by_identity():
    compute_environment = _staging_compute_environment_for_rewrites("stream")
    assert compute_environment.input_path_rewrite(object()) == "/pulsar/inputs/dataset_5.dat"
    assert compute_environment.job_wrapper.job_io.sync_cache is False


def test_input_metadata_rewrite_records_which_metadata_file_the_path_belongs_to(tmp_path):
    app = GalaxyDataTestApp()
    hda = HistoryDatasetAssociation(extension="bam", create_dataset=True, sa_session=app.model.session)
    index = tmp_path / "index"
    index.write_text("bam index")
    app.model.session.add(hda)
    app.model.session.commit()
    hda.metadata.from_JSON_dict(
        json_dict={"bam_index": MetadataTempFile.from_JSON({"kwds": {}, "filename": str(index)})}
    )
    app.model.session.commit()
    metadata_path = hda.metadata.bam_index.get_file_name()

    compute_environment = _staging_compute_environment_for_rewrites("stream")
    compute_environment.input_metadata_rewrite(hda, metadata_path)
    assert compute_environment.input_metadata_file_ids == {metadata_path: hda.metadata.bam_index.id}


def test_unknown_object_store_staging_mode_is_a_configuration_error():
    runner = _staging_runner()
    with pytest.raises(ConfigurationError):
        runner._client_inputs(_staging_job_wrapper(), _staging_compute_environment("true"), {})


def test_input_path_rewrite_keeps_the_local_path_without_object_store_staging():
    compute_environment = _staging_compute_environment_for_rewrites(None)
    assert compute_environment.input_path_rewrite(object()) == "/pulsar/inputs/dataset_5.dat"
    assert compute_environment.job_wrapper.job_io.sync_cache is None  # the local path config was used


def test_input_metadata_rewrite_records_nothing_for_a_path_that_is_no_metadata_file(tmp_path):
    app = GalaxyDataTestApp()
    hda = HistoryDatasetAssociation(extension="bam", create_dataset=True, sa_session=app.model.session)
    app.model.session.add(hda)
    app.model.session.commit()

    compute_environment = _staging_compute_environment_for_rewrites("stream")
    compute_environment.input_metadata_rewrite(hda, str(tmp_path / "not_a_metadata_file.dat"))
    assert compute_environment.input_metadata_file_ids == {}
