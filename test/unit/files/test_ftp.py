import os

import pytest
from fs.errors import RemoteConnectionError

from ._util import (
    assert_realizes_contains,
    configured_file_sources,
    user_context_fixture,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "ftp_file_sources_conf.yml")


def test_file_source_ftp_specific():
    test_url = "ftp://ftp.gnu.org/README"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    try:
        assert_realizes_contains(
            file_sources,
            test_url,
            "This is ftp.gnu.org, the FTP server of the the GNU project.",
            user_context=user_context,
        )
    except RemoteConnectionError:
        pytest.skip("ftp.gnu.org not available")


def test_file_source_ftp_generic():
    test_url = "ftp://ftp.slackware.com/welcome.msg"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test2"

    assert_realizes_contains(
        file_sources,
        test_url,
        "Oregon State University",
        user_context=user_context,
    )
