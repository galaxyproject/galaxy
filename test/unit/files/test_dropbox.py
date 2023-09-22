import os

import pytest

from ._util import assert_simple_file_realize

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "dropbox_file_sources_conf.yml")

skip_if_no_dropbox_access_token = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_DROPBOX_ACCESS_TOKEN"), reason="GALAXY_TEST_DROPBOX_ACCESS_TOKEN not set"
)


@skip_if_no_dropbox_access_token
def test_file_source():
    assert_simple_file_realize(FILE_SOURCES_CONF, recursive=True)
