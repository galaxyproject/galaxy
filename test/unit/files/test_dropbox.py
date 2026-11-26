import os

import pytest

from galaxy.exceptions import AuthenticationRequired
from ._util import (
    assert_simple_file_realize,
    configured_file_sources,
    list_root,
    user_context_fixture,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "dropbox_file_sources_conf.yml")

skip_if_no_dropbox_access_token = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_DROPBOX_ACCESS_TOKEN"), reason="GALAXY_TEST_DROPBOX_ACCESS_TOKEN not set"
)


@skip_if_no_dropbox_access_token
def test_file_source():
    assert_simple_file_realize(FILE_SOURCES_CONF, recursive=True)


def test_no_access_token_says_so(monkeypatch):
    pytest.importorskip("fs.dropboxfs")
    monkeypatch.delenv("GALAXY_TEST_DROPBOX_ACCESS_TOKEN", raising=False)
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    with pytest.raises(AuthenticationRequired, match="No Dropbox access token is set"):
        list_root(file_sources, "gxfiles://test1", recursive=False, user_context=user_context_fixture())
