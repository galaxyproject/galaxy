from subprocess import CalledProcessError

import pytest

from galaxy.tool_util.deps.container_classes import DOCKER_CONTAINER_TYPE
from galaxy.tool_util.deps.container_resolvers.explicit import CachedExplicitSingularityContainerResolver
from galaxy.tool_util.deps.container_resolvers.mulled import (
    CachedMulledDockerContainerResolver,
    CachedMulledSingularityContainerResolver,
    MulledDockerContainerResolver,
    MulledSingularityContainerResolver,
)
from galaxy.tool_util.deps.container_resolvers.oci_arch import (
    destination_platform,
    platform_to_oci_arch,
    pull_arch,
)
from galaxy.tool_util.deps.containers import ContainerRegistry
from galaxy.tool_util.deps.dependencies import (
    AppInfo,
    ToolInfo,
)
from galaxy.tool_util.deps.requirements import (
    ContainerDescription,
    ToolRequirement,
)
from galaxy.tool_util.deps.singularity_util import (
    pull_singularity_command,
    singularity_supports_arch,
)

SINGULARITY_IMAGES = (
    "foo:1.0--bar",
    "baz:2.22",
    "mulled-v2-fe8a3b846bc50d24e5df78fa0b562c43477fe9ce:9f946d13f673ab2903cb0da849ad42916d619d18-0",
)


@pytest.fixture
def appinfo() -> AppInfo:
    return AppInfo(
        involucro_auto_init=True,
        enable_mulled_containers=True,
        container_image_cache_path=".",
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
    mocker.patch("galaxy.tool_util.deps.mulled.util.quay_repositories", return_value=["samtools"])
    tool_info = ToolInfo(requirements=[ToolRequirement(name="samtools", version="1.10", type="package")])
    container_description = container_registry.find_best_container_description(
        [DOCKER_CONTAINER_TYPE],
        tool_info,
        install=False,
    )
    assert container_description.type == "docker"
    assert "samtools:1.10" in container_description.identifier


def test_docker_container_resolver_detects_docker_cli_absent(appinfo, mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value=None)
    resolver = CachedMulledDockerContainerResolver(appinfo)
    assert resolver._cli_available is False


def test_docker_container_resolver_detects_docker_cli(appinfo, mocker):
    """
    - CachedMulledDockerContainerResolver properly detects present docker binary
    """
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value="/bin/docker")
    resolver = CachedMulledDockerContainerResolver(appinfo)
    assert resolver.cli_available


def test_cached_docker_container_docker_cli_absent_resolve(appinfo, mocker) -> None:
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value=None)
    resolver = CachedMulledDockerContainerResolver(appinfo)
    assert resolver.cli_available is False
    assert resolver.resolve(enabled_container_types=[], tool_info=ToolInfo()) is None


def test_docker_container_docker_cli_absent_resolve(appinfo, mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value=None)
    resolver = MulledDockerContainerResolver(appinfo)
    assert resolver.cli_available is False
    requirement = ToolRequirement(name="samtools", version="1.10", type="package")
    tool_info = ToolInfo(requirements=[requirement])
    mocker.patch(
        "galaxy.tool_util.deps.container_resolvers.mulled.targets_to_mulled_name",
        return_value="samtools:1.10--h2e538c0_3",
    )
    container_description = resolver.resolve(enabled_container_types=["docker"], tool_info=tool_info)
    assert container_description
    assert container_description.type == "docker"
    assert container_description.identifier == "quay.io/biocontainers/samtools:1.10--h2e538c0_3"


def test_docker_container_docker_cli_exception_resolve(appinfo, mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value="/bin/docker")
    resolver = MulledDockerContainerResolver(appinfo)
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
    assert container_description
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
    assert container_description
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
    assert container_description
    assert container_description.type == "singularity"
    assert container_description.identifier == "/singularity/mulled/baz:2.22"
    requirement = ToolRequirement(name="foo", version="1.0", type="package")
    tool_info.requirements.append(requirement)
    container_description = resolver.resolve(enabled_container_types=["singularity"], tool_info=tool_info)
    assert container_description
    assert container_description.type == "singularity"
    assert (
        container_description.identifier
        == "/singularity/mulled/mulled-v2-fe8a3b846bc50d24e5df78fa0b562c43477fe9ce:9f946d13f673ab2903cb0da849ad42916d619d18-0"
    )


@pytest.mark.parametrize(
    "subdir,arch",
    [
        ("linux-64", "amd64"),
        ("linux-aarch64", "arm64"),
        ("linux-ppc64le", "ppc64le"),
        ("linux-s390x", "s390x"),
        ("linux-riscv64", "riscv64"),
        ("osx-arm64", "arm64"),
        ("osx-64", "amd64"),
        ("win-64", None),
        ("", None),
        (None, None),
    ],
)
def test_platform_to_oci_arch(subdir, arch):
    assert platform_to_oci_arch(subdir) == arch


def test_destination_platform_rejects_path_components():
    assert destination_platform({"platform": "linux-aarch64"}) == "linux-aarch64"
    assert destination_platform({}) is None
    assert destination_platform(None) is None
    assert destination_platform({"platform": "../etc"}) is None


def _singularity_listdir(mocker, cache_by_dir):
    mocker.patch("os.listdir", side_effect=lambda path: cache_by_dir.get(path, []))
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.safe_makedirs")


def _foo_tool_info():
    return ToolInfo(requirements=[ToolRequirement(name="foo", version="1.0", type="package")])


def test_cached_singularity_container_resolver_platform(mocker):
    _singularity_listdir(
        mocker,
        {"/singularity/mulled": ["foo:1.0--amd"], "/singularity/mulled/linux-aarch64": ["foo:1.0--arm"]},
    )
    resolver = CachedMulledSingularityContainerResolver(app_info=mocker.Mock(container_image_cache_path="/"))
    description = resolver.resolve(
        enabled_container_types=["singularity"],
        tool_info=_foo_tool_info(),
        destination_info={"platform": "linux-aarch64"},
    )
    assert description
    assert description.identifier == "/singularity/mulled/linux-aarch64/foo:1.0--arm"


def test_cached_singularity_container_resolver_no_platform_uses_plain_path(mocker):
    _singularity_listdir(
        mocker,
        {"/singularity/mulled": ["foo:1.0--amd"], "/singularity/mulled/linux-aarch64": ["foo:1.0--arm"]},
    )
    resolver = CachedMulledSingularityContainerResolver(app_info=mocker.Mock(container_image_cache_path="/"))
    for destination_info in (None, {}, {"other": "x"}):
        description = resolver.resolve(
            enabled_container_types=["singularity"], tool_info=_foo_tool_info(), destination_info=destination_info
        )
        assert description
        assert description.identifier == "/singularity/mulled/foo:1.0--amd"


def test_cached_singularity_container_resolver_platform_without_image(mocker):
    _singularity_listdir(mocker, {"/singularity/mulled": ["foo:1.0--amd"]})
    resolver = CachedMulledSingularityContainerResolver(app_info=mocker.Mock(container_image_cache_path="/"))
    description = resolver.resolve(
        enabled_container_types=["singularity"],
        tool_info=_foo_tool_info(),
        destination_info={"platform": "linux-aarch64"},
    )
    assert description is None


def test_platform_cache_directory_created_on_demand(tmp_path):
    app_info = AppInfo(container_image_cache_path=str(tmp_path))
    resolver = CachedMulledSingularityContainerResolver(app_info=app_info)
    assert not (tmp_path / "singularity" / "mulled" / "linux-ppc64le").exists()
    resolver.resolve(
        enabled_container_types=["singularity"],
        tool_info=_foo_tool_info(),
        destination_info={"platform": "linux-ppc64le"},
    )
    assert (tmp_path / "singularity" / "mulled" / "linux-ppc64le").is_dir()


def test_mulled_singularity_pull_uses_arch_and_platform_directory(mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.safe_makedirs")
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value="/usr/bin/singularity")
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.targets_to_mulled_name", return_value="foo:1.0--bar")
    mocker.patch("galaxy.tool_util.deps.container_resolvers.oci_arch.server_oci_arch", return_value="amd64")
    mocker.patch("galaxy.tool_util.deps.singularity_util.singularity_supports_arch", return_value=True)
    mocker.patch("os.listdir", return_value=[])
    mocker.patch("os.path.exists", return_value=True)
    shell = mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.shell")
    resolver = MulledSingularityContainerResolver(app_info=mocker.Mock(container_image_cache_path="/cache"))
    resolver.resolve(
        enabled_container_types=["singularity"],
        tool_info=_foo_tool_info(),
        install=True,
        destination_info={"platform": "linux-aarch64"},
    )
    cmds = shell.call_args.kwargs["cmds"]
    assert cmds[:4] == ["singularity", "build", "--arch", "arm64"]
    assert cmds[4] == "/cache/singularity/mulled/linux-aarch64/foo:1.0--bar"
    assert cmds[5] == "docker://quay.io/biocontainers/foo:1.0--bar"


def test_mulled_singularity_pull_without_platform_has_no_arch(mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.safe_makedirs")
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value="/usr/bin/singularity")
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.targets_to_mulled_name", return_value="foo:1.0--bar")
    mocker.patch("os.listdir", return_value=[])
    mocker.patch("os.path.exists", return_value=True)
    shell = mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.shell")
    resolver = MulledSingularityContainerResolver(app_info=mocker.Mock(container_image_cache_path="/cache"))
    resolver.resolve(enabled_container_types=["singularity"], tool_info=_foo_tool_info(), install=True)
    cmds = shell.call_args.kwargs["cmds"]
    assert "--arch" not in cmds
    assert cmds[2] == "/cache/singularity/mulled/foo:1.0--bar"


def test_pull_omits_arch_of_server(mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.oci_arch.server_oci_arch", return_value="arm64")
    assert pull_arch("linux-aarch64") is None
    assert pull_arch("linux-64") == "amd64"
    assert pull_arch("win-64") is None


def test_pull_command_without_arch_support_warns(mocker, caplog, tmp_path):
    mocker.patch("galaxy.tool_util.deps.singularity_util.singularity_supports_arch", return_value=False)
    target = str(tmp_path / "x.sif")
    cmds = pull_singularity_command("docker://quay.io/biocontainers/foo:1.0", target, arch="arm64")
    assert cmds == ["singularity", "build", target, "docker://quay.io/biocontainers/foo:1.0"]
    assert "does not support --arch" in caplog.text


def test_singularity_supports_arch_parses_help(mocker):
    singularity_supports_arch.cache_clear()
    mocker.patch(
        "galaxy.tool_util.deps.singularity_util.subprocess.run",
        return_value=mocker.Mock(stdout="  --arch string  architecture", stderr=""),
    )
    assert singularity_supports_arch("singularity") is True
    singularity_supports_arch.cache_clear()
    mocker.patch("galaxy.tool_util.deps.singularity_util.subprocess.run", side_effect=FileNotFoundError)
    assert singularity_supports_arch("singularity") is False
    singularity_supports_arch.cache_clear()


def test_explicit_cached_singularity_platform_pull(mocker, tmp_path):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.explicit.which", create=True)
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value="/usr/bin/singularity")
    mocker.patch("galaxy.tool_util.deps.container_resolvers.oci_arch.server_oci_arch", return_value="amd64")
    mocker.patch("galaxy.tool_util.deps.singularity_util.singularity_supports_arch", return_value=True)
    shell = mocker.patch("galaxy.tool_util.deps.container_resolvers.explicit.shell")
    resolver = CachedExplicitSingularityContainerResolver(app_info=AppInfo(container_image_cache_path=str(tmp_path)))
    tool_info = ToolInfo(container_descriptions=[ContainerDescription("quay.io/biocontainers/foo:1.0", type="docker")])
    description = resolver.resolve(
        enabled_container_types=["singularity"],
        tool_info=tool_info,
        install=True,
        destination_info={"platform": "linux-aarch64"},
    )
    cache_path = str(
        tmp_path / "singularity" / "explicit" / "linux-aarch64" / "docker:" / "quay.io" / "biocontainers" / "foo:1.0"
    )
    assert description.identifier == cache_path
    assert shell.call_args.args[0] == [
        "singularity",
        "build",
        "--arch",
        "arm64",
        cache_path,
        "docker://quay.io/biocontainers/foo:1.0",
    ]
