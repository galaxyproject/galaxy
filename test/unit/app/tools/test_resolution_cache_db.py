import time

import pytest
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

import galaxy.config
from galaxy.model.unittest_utils.beaker_testing_utils import is_cache_empty
from galaxy.model.unittest_utils.migration_scripts_testing_utils import tmp_directory  # noqa: F401
from galaxy.model.unittest_utils.model_testing_utils import (  # noqa: F401  (url_factory is a fixture we have to import explicitly)
    create_and_drop_database,
    url_factory,
)
from galaxy.tool_util.deps.container_resolvers import ResolutionCache
from galaxy.tool_util.deps.mulled.util import (
    _namespace_has_repo_name,
    mulled_tags_for,
    NAMESPACE_HAS_REPO_NAME_KEY,
    TAG_CACHE_KEY,
)

cache_namespace = "mulled_resolution"


@pytest.fixture(scope="module")
def appconfig():
    return galaxy.config.GalaxyAppConfiguration(override_tempdir=False)


@pytest.fixture()
def resolution_cache(url_factory, appconfig):  # noqa: F811
    db_url = url_factory()
    with create_and_drop_database(db_url):
        resolution_cache = ResolutionCache()
        cache_opts = {
            "cache.type": "ext:database",
            "cache.expire": "1",
            "cache.url": db_url,
            "cache.schema_name": appconfig.mulled_resolution_cache_schema_name,
            "cache.table_name": appconfig.mulled_resolution_cache_table_name,
        }
        cm = CacheManager(**parse_cache_config_options(cache_opts)).get_cache(cache_namespace)
        cm.clear()
        resolution_cache.mulled_resolution_cache = cm
        yield resolution_cache
        assert not is_cache_empty(db_url, cache_namespace)
        cm.clear()
        assert is_cache_empty(db_url, cache_namespace)


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
