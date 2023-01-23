import pytest
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

from galaxy.managers.citations import DoiCache
from galaxy import config


class TestDoiCache(DoiCache):
    def __init__(self, config):
        cache_opts = {
            "cache.type": getattr(config, "citation_cache_type", "ext:database"),
            "cache.data_dir": getattr(config, "citation_cache_data_dir", None),
            "cache.lock_dir": getattr(config, "citation_cache_lock_dir", None),
            "cache.url": "sqlite://",
            "cache.table_name": getattr(config, "citation_cache_table_name", "citation_beaker_cache"),
            "cache.schema_name": getattr(config, "citation_cache_schema_name", None),
        }
        self._cache = CacheManager(**parse_cache_config_options(cache_opts)).get_cache("doi")

@pytest.fixture()
def doi_cache():
    return TestDoiCache(config.GalaxyAppConfiguration(override_tempdir=False))


def test_DoiCache(doi_cache):
    assert "Jörg" in doi_cache.get_bibtex("10.1093/bioinformatics/bts252")
    assert "Özkurt" in doi_cache.get_bibtex("10.1101/2021.12.24.474111")
