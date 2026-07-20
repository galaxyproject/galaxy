"""Unit tests for Container classes."""

from galaxy.tool_util.deps.container_classes import (
    DockerContainer,
    SingularityContainer,
)


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
