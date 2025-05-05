import os.path
import tempfile

import responses

from galaxy.managers.citations import DoiCache
from galaxy.util.bunch import Bunch


@responses.activate
def test_DoiCache():
    with tempfile.TemporaryDirectory() as tmp_database_dir:
        config = Bunch(
            citation_cache_type="file",
            citation_cache_data_dir=os.path.join(tmp_database_dir, "data"),
            citation_cache_lock_dir=os.path.join(tmp_database_dir, "locks"),
            citation_cache_url=None,
            citation_cache_table_name=None,
            citation_cache_schema_name=None,
        )
        doi_cache = DoiCache(config)
        dois = (("10.1093/bioinformatics/bts252", "Jörg"), ("10.1101/2021.12.24.474111", "Özkurt"))
        for doi, author in dois:
            responses.add(method="GET", url=f"https://doi.org/{doi}", body=author)
            assert author in doi_cache.get_bibtex(doi)
