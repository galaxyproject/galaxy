import os

import pytest

from ._util import (
    assert_realizes_as,
    configured_file_sources,
    find,
    user_context_fixture,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "basespace_file_sources_conf.yml")

skip_if_no_basespace_access_token = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_BASESPACE_CLIENT_ID")
    or not os.environ.get("GALAXY_TEST_BASESPACE_CLIENT_SECRET")
    or not os.environ.get("GALAXY_TEST_BASESPACE_ACCESS_TOKEN")
    or not os.environ.get("GALAXY_TEST_BASESPACE_TEST_FILE_PATH"),
    reason="GALAXY_TEST_BASESPACE_CLIENT_ID and related vars not set",
)


@skip_if_no_basespace_access_token
def test_file_source():
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path("gxfiles://test1")

    assert file_source_pair.path == "/"
    file_source = file_source_pair.file_source
    test_file = os.environ.get("GALAXY_TEST_BASESPACE_TEST_FILE_PATH", "")
    res = file_source.list(os.path.dirname(test_file), recursive=False, user_context=user_context)
    a_file = find(res, class_="File", name=os.path.basename(test_file))
    assert a_file

    assert_realizes_as(file_sources, a_file["uri"], "a\n", user_context=user_context)
