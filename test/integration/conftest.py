import json
import os
import tempfile
from collections import defaultdict

import pytest
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
from xdist.scheduler import LoadScopeScheduling

from galaxy.tool_util.deps.mulled.util import NAMESPACE_HAS_REPO_NAME_KEY
from galaxy_test import shard
from galaxy_test.conftest import pytest_plugins  # noqa: F401
from galaxy_test.conftest import (
    pytest_configure as _base_pytest_configure,
)
from galaxy_test.shard import pytest_report_collectionfinish  # noqa: F401

HOST_SERVICES_SCOPE = "host-services"
INTEGRATION_LANES = (HOST_SERVICES_SCOPE, "default")

# Tests that share something outside their Galaxy instance -- a fixed host port, the AMQP
# broker, the minikube cluster, the host's Docker image cache -- keyed by test file or class.
# With --dist loadscope, each scope runs on a single pytest-xdist worker.
SHARED_RESOURCE_SCOPES = {
    "test/integration/oidc/test_auth_oidc.py": "keycloak",
    "test/integration/test_cli_runners.py": "cli-runner-containers",
    "test/integration/test_container_resolvers.py": HOST_SERVICES_SCOPE,
    "test/integration/test_containerized_jobs.py": HOST_SERVICES_SCOPE,
    "test/integration/test_coexecution.py": HOST_SERVICES_SCOPE,
    "test/integration/test_interactivetools_api.py::TestKubeInteractiveToolsRemoteProxyIntegration": HOST_SERVICES_SCOPE,
    "test/integration/test_interactivetools_api.py::TestKubernetesNativeInteractiveToolsIntegration": HOST_SERVICES_SCOPE,
    "test/integration/test_kubernetes_runner.py": HOST_SERVICES_SCOPE,
    "test/integration/test_pulsar_embedded_mq.py": HOST_SERVICES_SCOPE,
    "test/integration/test_pulsar_embedded_relay.py": HOST_SERVICES_SCOPE,
    "test/integration/test_resolvers.py": HOST_SERVICES_SCOPE,
}


def shared_resource_scope(nodeid: str) -> str | None:
    for prefix, scope in SHARED_RESOURCE_SCOPES.items():
        if nodeid.startswith(f"{prefix}::"):
            return scope
    return None


class SharedResourceScopeScheduling(LoadScopeScheduling):  # type: ignore[misc]  # pytest-xdist is untyped
    def _split_scope(self, nodeid: str) -> str:
        return shared_resource_scope(nodeid) or super()._split_scope(nodeid)


def longest_scopes_first(items: list) -> list:
    """Order items for --dist loadscope: the scopes with the most recorded work first.

    Within a shared-resource scope, groups run in name order as they do in a serial run. Its tests
    leave state behind for each other: test_containerized_jobs builds a mulled image that
    test_container_resolvers expects to be absent from the Docker image cache.
    """
    durations = shard.load_durations()
    scopes: dict[str, list] = defaultdict(list)
    for item in items:
        scopes[shared_resource_scope(item.nodeid) or shard.group_key(item)].append(item)

    def seconds(scope_items: list) -> float:
        group_keys = {shard.group_key(item) for item in scope_items}
        return sum(durations.get(key, shard.DEFAULT_GROUP_SECONDS) for key in group_keys)

    ordered = []
    for _, scope_items in sorted(scopes.items(), key=lambda scope: (-seconds(scope[1]), scope[0])):
        ordered.extend(sorted(scope_items, key=shard.group_key))
    return ordered


def pytest_configure(config):
    _base_pytest_configure(config)
    shard.pytest_configure(config)


def select_integration_lane(config, items: list) -> None:
    """Keep the tests of the CI lane named by GALAXY_TEST_INTEGRATION_LANE.

    The host-services lane runs the tests that need minikube, the AMQP broker or the host's
    Docker image cache; the default lane runs everything else. Unset, all tests run.
    """
    lane = os.environ.get("GALAXY_TEST_INTEGRATION_LANE")
    if not lane:
        return
    if lane not in INTEGRATION_LANES:
        raise pytest.UsageError(f"GALAXY_TEST_INTEGRATION_LANE must be one of {INTEGRATION_LANES}, not {lane!r}")
    keep_host_services = lane == HOST_SERVICES_SCOPE
    selected: list = []
    deselected: list = []
    for item in items:
        in_host_services = shared_resource_scope(item.nodeid) == HOST_SERVICES_SCOPE
        (selected if in_host_services == keep_host_services else deselected).append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    select_integration_lane(config, items)
    shard.pytest_collection_modifyitems(config, items)
    if os.environ.get("PYTEST_XDIST_WORKER"):
        items[:] = longest_scopes_first(items)


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_make_scheduler(config, log):
    if config.getvalue("dist") == "loadscope":
        return SharedResourceScopeScheduling(config, log)


@pytest.fixture(scope="session", autouse=True)
def seed_mulled_resolution_cache():
    """Seed the shared integration-test cache with a Quay namespace index."""
    seed_path = os.environ.get("GALAXY_TEST_MULLED_RESOLUTION_CACHE_SEED")
    data_dir = os.environ.get("GALAXY_CONFIG_OVERRIDE_MULLED_RESOLUTION_CACHE_DATA_DIR")
    lock_dir = os.environ.get("GALAXY_CONFIG_OVERRIDE_MULLED_RESOLUTION_CACHE_LOCK_DIR")
    if not seed_path or not data_dir or not lock_dir:
        return

    with open(seed_path) as seed_file:
        repositories = json.load(seed_file).get("repositories", [])
    if not repositories:
        return

    cache_opts = {
        "cache.type": "file",
        "cache.data_dir": data_dir,
        "cache.lock_dir": lock_dir,
        "cache.expire": os.environ.get("GALAXY_CONFIG_OVERRIDE_MULLED_RESOLUTION_CACHE_EXPIRE", "3600"),
    }
    cache = CacheManager(**parse_cache_config_options(cache_opts)).get_cache("mulled_resolution")
    cache[NAMESPACE_HAS_REPO_NAME_KEY] = repositories


@pytest.fixture(scope="session")
def celery_includes():
    return ["galaxy.celery.tasks"]


@pytest.fixture
def temp_file():
    with tempfile.NamedTemporaryFile(delete=True, mode="wb") as fh:
        yield fh
