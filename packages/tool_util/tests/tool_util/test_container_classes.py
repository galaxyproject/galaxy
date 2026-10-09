"""Unit tests for Container classes."""

import pytest

from galaxy.tool_util.deps.container_classes import (
    DockerContainer,
    SingularityContainer,
)
from galaxy.tool_util.deps.dependencies import (
    AppInfo,
    JobInfo,
    ToolInfo,
)
from galaxy.version import VERSION_MAJOR


def _build(container_class, container_id):
    return container_class(
        container_id=container_id,
        app_info=None,
        tool_info=None,
        destination_info={},
        job_info=None,
        container_description=None,
    )


def test_docker_identifier_is_never_a_path():
    container = _build(DockerContainer, "quay.io/biocontainers/bwa:0.7.17")
    assert container.image_identifier_is_path is False


def test_singularity_absolute_path_is_a_path():
    container = _build(SingularityContainer, "/cvmfs/singularity.galaxyproject.org/all/bwa:0.7.17")
    assert container.image_identifier_is_path is True


def test_singularity_docker_uri_is_not_a_path():
    container = _build(SingularityContainer, "docker://quay.io/biocontainers/bwa:0.7.17")
    assert container.image_identifier_is_path is False


def test_singularity_library_uri_is_not_a_path():
    container = _build(SingularityContainer, "library://sylabsed/examples/lolcow")
    assert container.image_identifier_is_path is False


@pytest.mark.parametrize("container_class", [DockerContainer, SingularityContainer])
@pytest.mark.parametrize("metadata", [False, True])
@pytest.mark.parametrize("has_storage", [False, True])
def test_pulsar_defaults_do_not_mount_galaxy_storage(container_class, metadata, has_storage):
    storage_paths = {"/storage/objects", "/storage/cache"} if has_storage else set()
    container = container_class(
        container_id="metadata-image",
        app_info=AppInfo(galaxy_root_dir="/galaxy", outputs_to_working_directory=True),
        tool_info=ToolInfo(tool_id="__SET_METADATA__" if metadata else "tool", profile=float(VERSION_MAJOR)),
        destination_info={},
        job_info=JobInfo(
            working_directory="/pulsar/staging/1",
            tool_directory=None,
            job_directory="/pulsar/staging/1",
            tmp_directory=None,
            home_directory=None,
            job_directory_type="pulsar",
            job_type="epilog" if metadata else "tool",
            output_paths=storage_paths,
        ),
        container_description=None,
    )
    volumes = container._expand_volume_str("$defaults").split(",")
    assert "/pulsar/staging/1:rw" in volumes
    assert "/galaxy:ro" not in volumes
    assert "$storage" not in volumes
    for path in storage_paths:
        assert f"{path}:rw" not in volumes
        assert f"{path}:ro" not in volumes
