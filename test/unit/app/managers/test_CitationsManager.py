import os.path
import tempfile

from galaxy.managers.citations import DoiCache
from galaxy.util.bunch import Bunch


def test_DoiCache():
    with tempfile.TemporaryDirectory() as tmp_database_dir:
        config = Bunch(
            citation_cache_data_dir=os.path.join(tmp_database_dir, "data"),
            citation_cache_lock_dir=os.path.join(tmp_database_dir, "locks"),
        )
        doi_cache = DoiCache(config)
        assert "Jörg" in doi_cache.get_bibtex("10.1093/bioinformatics/bts252")
        assert "Özkurt" in doi_cache.get_bibtex("10.1101/2021.12.24.474111")
