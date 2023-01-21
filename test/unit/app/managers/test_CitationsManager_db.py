import os.path
import tempfile
import pytest

from galaxy.managers.citations import DoiCache
from galaxy.util.bunch import Bunch
from galaxy import config

@pytest.fixture()
def doi_cache():
    return DoiCache(config.GalaxyAppConfiguration(override_tempdir=False))

def test_DoiCache(doi_cache):
    assert "Jörg" in doi_cache.get_bibtex("10.1093/bioinformatics/bts252")
    assert "Özkurt" in doi_cache.get_bibtex("10.1101/2021.12.24.474111")
