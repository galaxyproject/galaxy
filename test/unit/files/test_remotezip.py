import ipaddress
import os

import pytest

from galaxy.exceptions import AdminRequiredException
from galaxy.files.models import FileSourcePluginsConfig
from ._util import (
    assert_realizes_contains,
    configured_file_sources,
    realize_to_temp_file,
    user_context_fixture,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "remotezip_file_sources_conf.yml")
LOCALHOST_ALLOWLIST = FileSourcePluginsConfig(
    fetch_url_allowlist=[ipaddress.ip_network("127.0.0.0/24")],
)


def test_file_source(mock_http_server):
    zip_url = mock_http_server.get_url(
        remote_url="https://raw.githubusercontent.com/davelopez/ro-crate-zip-explorer/refs/heads/main/tests/test-data/rocrate-test.zip",
        file_path="test-data/rocrate-test.zip",
        content_type="application/zip",
        support_ranges=True,
        support_head=True,
    )
    header_offset = 15875
    compression_method = 8
    compress_size = 582
    expected_contents = "class: GalaxyWorkflow"

    test_url = f"zip://extract?source={zip_url}&header_offset={header_offset}&compress_size={compress_size}&compression_method={compression_method}"
    user_context = user_context_fixture()
    file_sources_config = LOCALHOST_ALLOWLIST if not mock_http_server.is_remote else None
    file_sources = configured_file_sources(FILE_SOURCES_CONF, file_sources_config=file_sources_config)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    assert_realizes_contains(file_sources, test_url, expected_contents, user_context=user_context)


def test_file_source_cannot_access_local_file():
    local_file_url = "file://etc/passwd"
    header_offset = 15875
    compression_method = 8
    compress_size = 582
    test_url = f"zip://extract?source={local_file_url}&header_offset={header_offset}&compress_size={compress_size}&compression_method={compression_method}"
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)
    user_context = user_context_fixture()

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    with pytest.raises(AdminRequiredException):
        realize_to_temp_file(file_sources, test_url, user_context=user_context)
