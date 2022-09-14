from subprocess import CalledProcessError

import pytest

from galaxy.tool_util.deps.container_classes import DOCKER_CONTAINER_TYPE
from galaxy.tool_util.deps.container_resolvers.mulled import (
    CachedMulledDockerContainerResolver,
    CachedMulledSingularityContainerResolver,
    MulledDockerContainerResolver,
)
from galaxy.tool_util.deps.containers import ContainerRegistry
from galaxy.tool_util.deps.dependencies import (
    AppInfo,
    ToolInfo,
)
from galaxy.tool_util.deps.requirements import ToolRequirement

SINGULARITY_IMAGES = (
    "foo:1.0--bar",
    "baz:2.22",
    "mulled-v2-fe8a3b846bc50d24e5df78fa0b562c43477fe9ce:9f946d13f673ab2903cb0da849ad42916d619d18-0",
)


@pytest.fixture
def container_registry():
    app_info = AppInfo(
        involucro_auto_init=True,
        enable_mulled_containers=True,
        container_image_cache_path=".",
    )
    return ContainerRegistry(app_info)


def test_container_registry(container_registry, mocker):
    mocker.patch("galaxy.tool_util.deps.mulled.util._get_namespace", return_value=["samtools"])
    tool_info = ToolInfo(requirements=[ToolRequirement(name="samtools", version="1.10", type="package")])
    container_description = container_registry.find_best_container_description(
        [DOCKER_CONTAINER_TYPE],
        tool_info,
        install=False,
    )
    assert container_description.type == "docker"
    assert "samtools:1.10" in container_description.identifier


def test_docker_container_resolver_detects_docker_cli_absent(mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value=None)
    resolver = CachedMulledDockerContainerResolver()
    assert resolver._cli_available is False


def test_docker_container_resolver_detects_docker_cli(mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled", return_value="/bin/docker")
    resolver = CachedMulledDockerContainerResolver()
    assert resolver.cli_available


def test_cached_docker_container_docker_cli_absent_resolve(mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value=None)
    resolver = CachedMulledDockerContainerResolver()
    assert resolver.cli_available is False
    assert resolver.resolve(enabled_container_types=[], tool_info={}) is None


def test_docker_container_docker_cli_absent_resolve(mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value=None)
    resolver = MulledDockerContainerResolver()
    assert resolver.cli_available is False
    requirement = ToolRequirement(name="samtools", version="1.10", type="package")
    tool_info = ToolInfo(requirements=[requirement])
    mocker.patch(
        "galaxy.tool_util.deps.container_resolvers.mulled.targets_to_mulled_name",
        return_value="samtools:1.10--h2e538c0_3",
    )
    container_description = resolver.resolve(enabled_container_types=["docker"], tool_info=tool_info)
    assert container_description.type == "docker"
    assert container_description.identifier == "quay.io/biocontainers/samtools:1.10--h2e538c0_3"


def test_docker_container_docker_cli_exception_resolve(mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value="/bin/docker")
    resolver = MulledDockerContainerResolver()
    assert resolver.cli_available is True
    requirement = ToolRequirement(name="samtools", version="1.10", type="package")
    tool_info = ToolInfo(requirements=[requirement])
    mocker.patch(
        "galaxy.tool_util.deps.container_resolvers.mulled.targets_to_mulled_name",
        return_value="samtools:1.10--h2e538c0_3",
    )
    mocker.patch(
        "galaxy.tool_util.deps.container_resolvers.mulled.docker_cached_container_description",
        side_effect=CalledProcessError(1, "bla"),
    )
    container_description = resolver.resolve(enabled_container_types=["docker"], tool_info=tool_info, install=True)
    assert resolver.cli_available is True
    assert container_description.type == "docker"
    assert container_description.identifier == "quay.io/biocontainers/samtools:1.10--h2e538c0_3"


def test_cached_singularity_container_resolver_uncached(mocker):
    mocker.patch("os.listdir", return_value=SINGULARITY_IMAGES)
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.safe_makedirs")
    resolver = CachedMulledSingularityContainerResolver(app_info=mocker.Mock(container_image_cache_path="/"))
    requirement = ToolRequirement(name="foo", version="1.0", type="package")
    tool_info = ToolInfo(requirements=[requirement])
    container_description = resolver.resolve(enabled_container_types=["singularity"], tool_info=tool_info)
    assert container_description.type == "singularity"
    assert container_description.identifier == "/singularity/mulled/foo:1.0--bar"


def test_cached_singularity_container_resolver_dir_mtime_cached(mocker):
    mocker.patch("os.listdir", return_value=SINGULARITY_IMAGES)
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.safe_makedirs")
    mocker.patch("os.stat", return_value=mocker.Mock(st_mtime=42))
    resolver = CachedMulledSingularityContainerResolver(
        app_info=mocker.Mock(container_image_cache_path="/"), cache_directory_cacher_type="dir_mtime"
    )
    requirement = ToolRequirement(name="baz", version="2.22", type="package")
    tool_info = ToolInfo(requirements=[requirement])
    container_description = resolver.resolve(enabled_container_types=["singularity"], tool_info=tool_info)
    assert container_description.type == "singularity"
    assert container_description.identifier == "/singularity/mulled/baz:2.22"
    requirement = ToolRequirement(name="foo", version="1.0", type="package")
    tool_info.requirements.append(requirement)
    container_description = resolver.resolve(enabled_container_types=["singularity"], tool_info=tool_info)
    assert container_description.type == "singularity"
    assert (
        container_description.identifier
        == "/singularity/mulled/mulled-v2-fe8a3b846bc50d24e5df78fa0b562c43477fe9ce:9f946d13f673ab2903cb0da849ad42916d619d18-0"
    )
