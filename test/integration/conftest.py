import json
import os
import tempfile

import pytest
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

from galaxy.tool_util.deps.mulled.util import NAMESPACE_HAS_REPO_NAME_KEY
from galaxy_test import shard
from galaxy_test.conftest import pytest_plugins  # noqa: F401
from galaxy_test.conftest import (
    pytest_configure as _base_pytest_configure,
)
from galaxy_test.shard import (  # noqa: F401
    pytest_collection_modifyitems,
    pytest_report_collectionfinish,
)


def pytest_configure(config):
    _base_pytest_configure(config)
    shard.pytest_configure(config)


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
