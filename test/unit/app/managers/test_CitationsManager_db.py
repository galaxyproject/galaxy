from unittest import SkipTest

import requests
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

import galaxy.config
from galaxy.managers.citations import DoiCache
from galaxy.model.unittest_utils.beaker_testing_utils import is_cache_empty
from galaxy.model.unittest_utils.migration_scripts_testing_utils import tmp_directory  # noqa: F401
from galaxy.model.unittest_utils.model_testing_utils import (  # noqa: F401  (url_factory is a fixture we have to import explicitly)
    create_and_drop_database,
    url_factory,
)


class MockDoiCache(DoiCache):
    def __init__(self, config, db_url):
        cache_opts = {
            "cache.type": "ext:database",
            "cache.data_dir": config.citation_cache_data_dir,
            "cache.url": db_url,
            "cache.table_name": config.citation_cache_table_name,
            "cache.schema_name": config.citation_cache_schema_name,
        }
        self._cache = CacheManager(**parse_cache_config_options(cache_opts)).get_cache("doi")
        self._cache.clear()


def test_DoiCache(url_factory):  # noqa: F811
    db_url = url_factory()
    with create_and_drop_database(db_url):
        doi_cache = MockDoiCache(galaxy.config.GalaxyAppConfiguration(override_tempdir=False), db_url)
        assert is_cache_empty(db_url, "doi")
        try:
            assert "Jörg" in doi_cache.get_bibtex("10.1093/bioinformatics/bts252")
            assert "Özkurt" in doi_cache.get_bibtex("10.1101/2021.12.24.474111")
        except requests.exceptions.RequestException as e:
            raise SkipTest(f"dx.doi failed to respond: {e}")
        assert not is_cache_empty(db_url, "doi")
        doi_cache._cache.clear()
        assert is_cache_empty(db_url, "doi")
