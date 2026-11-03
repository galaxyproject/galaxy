import io
import ipaddress
import os
import zipfile

import pytest
import responses

from galaxy.exceptions import (
    AdminRequiredException,
    ConfigDoesNotAllowException,
)
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


ZIP_URL = "https://example.org/archive.zip"
MOVED_ZIP_URL = "https://other.example/archive.zip"
MEMBER_CONTENTS = "class: GalaxyWorkflow\n" * 20


def _zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("workflow.gxwf.yml", MEMBER_CONTENTS)
    return buffer.getvalue()


def _zip_url(source: str = ZIP_URL) -> str:
    data = _zip_bytes()
    info = zipfile.ZipFile(io.BytesIO(data)).infolist()[0]
    return (
        f"zip://extract?source={source}&header_offset={info.header_offset}"
        f"&compress_size={info.compress_size}&compression_method={info.compress_type}"
    )


def _serve_ranges(url: str):
    data = _zip_bytes()

    def callback(request):
        start, end = (int(i) for i in request.headers["Range"].removeprefix("bytes=").split("-"))
        return 206, {}, data[start : end + 1]

    responses.add_callback(responses.GET, url, callback=callback)


def _realize(test_url: str) -> str:
    return realize_to_temp_file(
        configured_file_sources(FILE_SOURCES_CONF), test_url, user_context=user_context_fixture()
    )


@responses.activate
@pytest.mark.usefixtures("fake_public_dns")
def test_file_source_follows_redirect_to_public_host():
    responses.head(ZIP_URL, status=302, headers={"Location": MOVED_ZIP_URL})
    responses.head(MOVED_ZIP_URL)
    _serve_ranges(MOVED_ZIP_URL)
    assert _realize(_zip_url()) == MEMBER_CONTENTS


@responses.activate
@pytest.mark.usefixtures("fake_public_dns")
def test_file_source_refuses_head_redirect_to_private_address():
    responses.head(ZIP_URL, status=302, headers={"Location": "http://127.0.0.1/archive.zip"})
    redirect_target = responses.head("http://127.0.0.1/archive.zip")
    _serve_ranges("http://127.0.0.1/archive.zip")
    with pytest.raises(ConfigDoesNotAllowException):
        _realize(_zip_url())
    assert redirect_target.call_count == 0


@responses.activate
@pytest.mark.usefixtures("fake_public_dns")
def test_file_source_refuses_range_redirect_to_private_address():
    responses.head(ZIP_URL)
    responses.get(ZIP_URL, status=302, headers={"Location": "http://127.0.0.1/archive.zip"})
    _serve_ranges("http://127.0.0.1/archive.zip")
    with pytest.raises(ConfigDoesNotAllowException):
        _realize(_zip_url())
    assert len(responses.calls) == 2
