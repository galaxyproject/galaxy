import time

import pytest
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

from galaxy.tool_util.deps.container_resolvers import ResolutionCache
from galaxy.tool_util.deps.mulled.util import (
    _namespace_has_repo_name,
    mulled_tags_for,
    NAMESPACE_HAS_REPO_NAME_KEY,
    TAG_CACHE_KEY,
)


@pytest.fixture()
def resolution_cache(tmpdir):
    resolution_cache = ResolutionCache()
    cache_opts = {
        "cache.type": "file",
        "cache.data_dir": str(tmpdir / "data"),
        "cache.lock_dir": str(tmpdir / "lock"),
        "cache.expire": "1",
    }
    cm = CacheManager(**parse_cache_config_options(cache_opts)).get_cache("mulled_resolution")
    resolution_cache.mulled_resolution_cache = cm
    return resolution_cache


def test_resolution_cache_namespace_missing():
    resolution_cache = ResolutionCache()
    resolution_cache.mulled_resolution_cache = {"a": "b"}
    assert not _namespace_has_repo_name("bioconda", "mytool3000", resolution_cache=resolution_cache)


def test_resolution_cache_namepace_has_repo_name(resolution_cache):
    resolution_cache.mulled_resolution_cache[NAMESPACE_HAS_REPO_NAME_KEY] = ["mytool3000"]
    assert _namespace_has_repo_name("bioconda", "mytool3000", resolution_cache=resolution_cache)


def test_resolution_cache_expires(resolution_cache):
    resolution_cache.mulled_resolution_cache[NAMESPACE_HAS_REPO_NAME_KEY] = ["mytool3000"]
    assert NAMESPACE_HAS_REPO_NAME_KEY in resolution_cache.mulled_resolution_cache
    time.sleep(1.2)
    assert NAMESPACE_HAS_REPO_NAME_KEY not in resolution_cache.mulled_resolution_cache


def test_targets_to_mulled_name(resolution_cache):
    resolution_cache.mulled_resolution_cache[NAMESPACE_HAS_REPO_NAME_KEY] = ["mytool3000"]
    cache = resolution_cache.mulled_resolution_cache._get_cache("mulled_tag_cache", {"expire": 1})
    cache[TAG_CACHE_KEY] = {"bioconda": {"mytool3000": ["1.0", "1.1"]}}
    tags = mulled_tags_for(namespace="bioconda", image="mytool3000", resolution_cache=resolution_cache)
    assert tags == ["1.1", "1.0"]
