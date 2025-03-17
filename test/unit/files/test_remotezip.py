import os

from galaxy.util.unittest_utils import skip_if_github_down
from ._util import (
    assert_realizes_contains,
    configured_file_sources,
    user_context_fixture,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "remotezip_file_sources_conf.yml")


@skip_if_github_down
def test_file_source():
    remote_zip_url = "https://raw.githubusercontent.com/davelopez/ro-crate-zip-explorer/refs/heads/main/tests/test-data/rocrate-test.zip"
    header_offset = 15875
    compression_method = 8
    compress_size = 582
    expected_contents = "class: GalaxyWorkflow"

    test_url = f"zip://extract?source={remote_zip_url}&header_offset={header_offset}&compress_size={compress_size}&compression_method={compression_method}"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    assert_realizes_contains(file_sources, test_url, expected_contents, user_context=user_context)
