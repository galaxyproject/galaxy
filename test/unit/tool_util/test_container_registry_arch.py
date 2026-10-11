import pytest

from galaxy.tool_util.deps.container_resolvers import registry
from galaxy.tool_util.deps.container_resolvers.explicit import (
    CachedExplicitSingularityContainerResolver,
    ExplicitSingularityContainerResolver,
)
from galaxy.tool_util.deps.container_resolvers.mulled import MulledSingularityContainerResolver
from galaxy.tool_util.deps.dependencies import (
    AppInfo,
    ToolInfo,
)
from galaxy.tool_util.deps.requirements import (
    ContainerDescription,
    ToolRequirement,
)

LIST_TYPE = "application/vnd.docker.distribution.manifest.list.v2+json"
MANIFEST_TYPE = "application/vnd.docker.distribution.manifest.v2+json"


class FakeResponse:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code = status
        self._body = body if body is not None else {}
        self.headers = headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture(autouse=True)
def clear_registry_cache():
    registry._cache.clear()
    yield
    registry._cache.clear()


def _patch_get(mocker, handler):
    calls = []

    def get(url, headers=None, timeout=None, params=None):
        assert timeout
        calls.append((url, dict(headers or {}), params))
        return handler(url, dict(headers or {}), params)

    mocker.patch("galaxy.tool_util.deps.container_resolvers.registry.requests.get", side_effect=get)
    return calls


def test_parse_image_reference():
    assert registry.parse_image_reference("docker://python:3.12-alpine") == (
        "registry-1.docker.io",
        "library/python",
        "3.12-alpine",
    )
    assert registry.parse_image_reference("quay.io/biocontainers/samtools:1.20--h0") == (
        "quay.io",
        "biocontainers/samtools",
        "1.20--h0",
    )
    assert registry.parse_image_reference("docker://quay.io/a/b@sha256:abc") == ("quay.io", "a/b", "sha256:abc")
    assert registry.parse_image_reference("localhost:5000/x/y:1") == ("localhost:5000", "x/y", "1")


def test_manifest_list_returns_platform_architectures(mocker):
    body = {
        "mediaType": LIST_TYPE,
        "manifests": [
            {"platform": {"architecture": "amd64", "os": "linux"}},
            {"platform": {"architecture": "arm64", "os": "linux"}},
            {"platform": {"architecture": "unknown", "os": "unknown"}},
        ],
    }
    calls = _patch_get(mocker, lambda url, headers, params: FakeResponse(body=body))
    assert registry.registry_image_architectures("docker://quay.io/org/tool:1") == ["amd64", "arm64"]
    url, headers, _ = calls[0]
    assert url == "https://quay.io/v2/org/tool/manifests/1"
    for media_type in (
        LIST_TYPE,
        "application/vnd.oci.image.index.v1+json",
        MANIFEST_TYPE,
        "application/vnd.oci.image.manifest.v1+json",
    ):
        assert media_type in headers["Accept"]


def test_single_manifest_fetches_config_blob(mocker):
    def handler(url, headers, params):
        if "/manifests/" in url:
            return FakeResponse(body={"mediaType": MANIFEST_TYPE, "config": {"digest": "sha256:cfg"}})
        assert url.endswith("/v2/biocontainers/samtools/blobs/sha256:cfg")
        return FakeResponse(body={"architecture": "amd64"})

    _patch_get(mocker, handler)
    assert registry.registry_image_architectures("quay.io/biocontainers/samtools:1.20") == ["amd64"]


def test_bearer_token_flow_and_library_prefix(mocker):
    challenge = (
        'Bearer realm="https://auth.docker.io/token",service="registry.docker.io",'
        'scope="repository:library/python:pull"'
    )

    def handler(url, headers, params):
        if url.startswith("https://auth.docker.io/token"):
            assert params == {"scope": "repository:library/python:pull", "service": "registry.docker.io"}
            return FakeResponse(body={"token": "tok"})
        if headers.get("Authorization") != "Bearer tok":
            return FakeResponse(status=401, headers={"Www-Authenticate": challenge})
        return FakeResponse(body={"manifests": [{"platform": {"architecture": "arm64"}}]})

    calls = _patch_get(mocker, handler)
    assert registry.registry_image_architectures("docker://python:3.12-alpine") == ["arm64"]
    assert calls[0][0] == "https://registry-1.docker.io/v2/library/python/manifests/3.12-alpine"


def test_network_error_returns_none(mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.registry.requests.get", side_effect=ConnectionError("down"))
    assert registry.registry_image_architectures("docker://python:3.12") is None


def test_result_is_cached_per_reference(mocker):
    calls = _patch_get(
        mocker, lambda url, headers, params: FakeResponse(body={"manifests": [{"platform": {"architecture": "amd64"}}]})
    )
    registry.registry_image_architectures("quay.io/a/b:1")
    registry.registry_image_architectures("quay.io/a/b:1")
    assert len(calls) == 1


def test_missing_architecture(mocker):
    mocker.patch.object(registry, "registry_image_architectures", return_value=["amd64"])
    assert registry.missing_architecture("docker://quay.io/a/b:1", "linux-aarch64") == ["amd64"]
    assert registry.missing_architecture("docker://quay.io/a/b:1", "linux-64") is None
    assert registry.missing_architecture("docker://quay.io/a/b:1", "win-64") is None
    assert registry.missing_architecture("/some/path.sif", "linux-aarch64") is None
    mocker.patch.object(registry, "registry_image_architectures", return_value=None)
    assert registry.missing_architecture("docker://quay.io/a/b:1", "linux-aarch64") is None


def _tool_info():
    return ToolInfo(requirements=[ToolRequirement(name="foo", version="1.0", type="package")])


def test_mulled_singularity_does_not_pull_missing_architecture(mocker):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.safe_makedirs")
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value="/usr/bin/singularity")
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.targets_to_mulled_name", return_value="foo:1.0--bar")
    mocker.patch("os.listdir", return_value=[])
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch.object(registry, "registry_image_architectures", return_value=["amd64"])
    shell = mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.shell")
    resolver = MulledSingularityContainerResolver(app_info=mocker.Mock(container_image_cache_path="/cache"))
    description = resolver.resolve(
        enabled_container_types=["singularity"],
        tool_info=_tool_info(),
        install=True,
        destination_info={"platform": "linux-aarch64"},
    )
    assert description is None
    shell.assert_not_called()


def test_explicit_cached_singularity_does_not_pull_missing_architecture(mocker, tmp_path):
    mocker.patch("galaxy.tool_util.deps.container_resolvers.mulled.which", return_value="/usr/bin/singularity")
    mocker.patch.object(registry, "registry_image_architectures", return_value=["amd64"])
    shell = mocker.patch("galaxy.tool_util.deps.container_resolvers.explicit.shell")
    resolver = CachedExplicitSingularityContainerResolver(app_info=AppInfo(container_image_cache_path=str(tmp_path)))
    tool_info = ToolInfo(container_descriptions=[ContainerDescription("python:3.12-alpine", type="docker")])
    description = resolver.resolve(
        enabled_container_types=["singularity"],
        tool_info=tool_info,
        install=True,
        destination_info={"platform": "linux-aarch64"},
    )
    assert description is None
    shell.assert_not_called()


def test_explicit_singularity_checks_architecture(mocker):
    tool_info = ToolInfo(container_descriptions=[ContainerDescription("python:3.12-alpine", type="docker")])
    resolver = ExplicitSingularityContainerResolver(app_info=AppInfo())
    mocker.patch.object(registry, "registry_image_architectures", return_value=["amd64", "arm64"])
    description = resolver.resolve(
        enabled_container_types=["singularity"], tool_info=tool_info, destination_info={"platform": "linux-aarch64"}
    )
    assert description is not None
    assert description.identifier == "docker://python:3.12-alpine"
    mocker.patch.object(registry, "registry_image_architectures", return_value=["amd64"])
    assert (
        resolver.resolve(
            enabled_container_types=["singularity"], tool_info=tool_info, destination_info={"platform": "linux-aarch64"}
        )
        is None
    )
    assert resolver.resolve(enabled_container_types=["singularity"], tool_info=tool_info) is not None
