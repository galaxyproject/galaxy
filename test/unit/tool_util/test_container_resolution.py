from subprocess import CalledProcessError

from galaxy.tool_util.deps.container_resolvers.mulled import (
    CachedMulledDockerContainerResolver,
    MulledDockerContainerResolver,
)
from galaxy.tool_util.deps.dependencies import ToolInfo
from galaxy.tool_util.deps.requirements import ToolRequirement


def test_docker_container_resolver_detects_docker_cli_absent(mocker):
    mocker.patch('galaxy.tool_util.deps.container_resolvers.mulled.which', return_value=None)
    resolver = CachedMulledDockerContainerResolver()
    assert resolver._cli_available is False


def test_docker_container_resolver_detects_docker_cli(mocker):
    mocker.patch('galaxy.tool_util.deps.container_resolvers.mulled', return_value='/bin/docker')
    resolver = CachedMulledDockerContainerResolver()
    assert resolver.cli_available


def test_cached_docker_container_docker_cli_absent_resolve(mocker):
    mocker.patch('galaxy.tool_util.deps.container_resolvers.mulled.which', return_value=None)
    resolver = CachedMulledDockerContainerResolver()
    assert resolver.cli_available is False
    assert resolver.resolve(enabled_container_types=[], tool_info={}) is None


def test_docker_container_docker_cli_absent_resolve(mocker):
    mocker.patch('galaxy.tool_util.deps.container_resolvers.mulled.which', return_value=None)
    resolver = MulledDockerContainerResolver()
    assert resolver.cli_available is False
    requirement = ToolRequirement(name="samtools", version="1.10", type="package")
    tool_info = ToolInfo(requirements=[requirement])
    mocker.patch('galaxy.tool_util.deps.container_resolvers.mulled.targets_to_mulled_name', return_value='samtools:1.10--h2e538c0_3')
    container_description = resolver.resolve(enabled_container_types=['docker'], tool_info=tool_info)
    assert container_description.type == 'docker'
    assert container_description.identifier == 'quay.io/biocontainers/samtools:1.10--h2e538c0_3'


def test_docker_container_docker_cli_exception_resolve(mocker):
    mocker.patch('galaxy.tool_util.deps.container_resolvers.mulled.which', return_value='/bin/docker')
    resolver = MulledDockerContainerResolver()
    assert resolver.cli_available is True
    requirement = ToolRequirement(name="samtools", version="1.10", type="package")
    tool_info = ToolInfo(requirements=[requirement])
    mocker.patch('galaxy.tool_util.deps.container_resolvers.mulled.targets_to_mulled_name', return_value='samtools:1.10--h2e538c0_3')
    mocker.patch('galaxy.tool_util.deps.container_resolvers.mulled.docker_cached_container_description', side_effect=CalledProcessError(1, 'bla'))
    container_description = resolver.resolve(enabled_container_types=['docker'], tool_info=tool_info, install=True)
    assert resolver.cli_available is True
    assert container_description.type == 'docker'
    assert container_description.identifier == 'quay.io/biocontainers/samtools:1.10--h2e538c0_3'
