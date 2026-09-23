import gzip
import io
import os
import urllib
from typing import Any
from unittest import mock

import pytest
import responses

from galaxy import exceptions
from ._util import (
    assert_realizes_as,
    assert_realizes_contains,
    configured_file_sources,
    user_context_fixture,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "http_file_sources_conf.yml")
FILE_SOURCES_CONF_WITHOUT_STOCK = os.path.join(SCRIPT_DIRECTORY, "http_without_stock_file_sources_conf.yml")


@responses.activate
def test_file_source_http_specific():
    test_url = "https://www.usegalaxy.org/myfile.txt"

    def check_specific_header(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        return 200, {}, "hello specific world"

    responses.add_callback(responses.GET, test_url, callback=check_specific_header)
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    assert_realizes_as(file_sources, test_url, "hello specific world", user_context=user_context)


def test_plugins_to_dict_serializes_only_best_matching_http_source():
    test_url = "https://www.usegalaxy.org/myfile.txt"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    plugins = file_sources.plugins_to_dict(
        for_serialization=True,
        user_context=user_context,
        referenced_uris={test_url},
    )
    assert [plugin["id"] for plugin in plugins] == ["test1"]


@responses.activate
def test_file_source_another_http_specific():
    test_url = "http://www.galaxyproject.org/anotherfile.txt"

    def check_another_header(request):
        assert request.headers["Another_header"] == "found"
        return 200, {}, "hello another world"

    responses.add_callback(responses.GET, test_url, callback=check_another_header)
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test2"

    assert_realizes_as(file_sources, test_url, "hello another world", user_context=user_context)


@responses.activate
def test_file_source_http_generic():
    test_url = "https://www.elsewhere.org/myfile.txt"

    def check_generic_headers(request):
        assert "Authorization" not in request.headers
        assert "Another_header" not in request.headers
        return 200, {}, "hello generic world"

    responses.add_callback(responses.GET, test_url, callback=check_generic_headers)
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test3"

    assert_realizes_as(file_sources, test_url, "hello generic world", user_context=user_context)


@responses.activate
def test_file_source_http_decodes_content_encoding():
    test_url = "https://www.elsewhere.org/compressed.txt"
    content = b"content compressed for transfer"
    responses.add(
        responses.GET,
        test_url,
        body=gzip.compress(content, mtime=0),
        headers={"Content-Encoding": "gzip"},
    )
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)

    assert_realizes_as(file_sources, test_url, content.decode(), user_context=user_context)


def test_file_source_ftp_url():
    test_url = "ftp://ftp.gnu.org/README"

    def check_generic_headers(request, **kwargs):
        assert not request.headers
        response: Any = io.StringIO("This is ftp.gnu.org, the FTP server of the the GNU project.")
        response.headers = {}
        response.geturl = lambda: test_url
        return response

    with mock.patch.object(urllib.request, "urlopen", new=check_generic_headers):
        user_context = user_context_fixture()
        file_sources = configured_file_sources(FILE_SOURCES_CONF)
        file_source_pair = file_sources.get_file_source_path(test_url)

        assert file_source_pair.path == test_url
        assert file_source_pair.file_source.id == "test3"

        assert_realizes_contains(
            file_sources,
            test_url,
            "This is ftp.gnu.org, the FTP server of the the GNU project.",
            user_context=user_context,
        )


def test_file_source_http_without_stock_generic():
    test_url = "https://www.elsewhere.org/myfile.txt"
    file_sources = configured_file_sources(FILE_SOURCES_CONF_WITHOUT_STOCK)
    with pytest.raises(exceptions.RequestParameterInvalidException, match="Could not find handler for URI"):
        file_sources.get_file_source_path(test_url)


@responses.activate
def test_file_source_http_without_stock_specific():
    test_url = "https://www.usegalaxy.org/myfile2.txt"

    def check_specific_header(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        return 200, {}, "hello specific world 2"

    responses.add_callback(responses.GET, test_url, callback=check_specific_header)
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF_WITHOUT_STOCK)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    assert_realizes_as(file_sources, test_url, "hello specific world 2", user_context=user_context)


def test_file_source_http_with_spaces_in_url_error():
    """Test that URLs with unencoded spaces give a helpful error (issue #21221)."""
    test_url = "https://example.com/Markers File.csv"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)

    with pytest.raises(ValueError, match="URL contains unencoded characters"):
        file_source_pair = file_sources.get_file_source_path(test_url)
        file_source_pair.file_source.realize_to(file_source_pair.path, "/tmp/test", user_context=user_context)


@responses.activate
def test_file_source_http_validates_redirect_target():
    test_url = "https://example.com/start"
    private_url = "http://127.0.0.1/private"
    responses.add(responses.GET, test_url, status=302, headers={"Location": private_url})
    responses.add(responses.GET, private_url, body="private data")
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)

    with pytest.raises(exceptions.ConfigDoesNotAllowException):
        file_source_pair = file_sources.get_file_source_path(test_url)
        file_source_pair.file_source.realize_to(file_source_pair.path, "/tmp/test", user_context=user_context)


@pytest.mark.parametrize("character", ("\n", "\t", "\x7f"))
def test_file_source_http_with_control_character_error(character):
    test_url = f"https://example.com/file{character}name.txt"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)

    with pytest.raises(ValueError, match="URL contains unencoded characters"):
        file_source_pair = file_sources.get_file_source_path(test_url)
        file_source_pair.file_source.realize_to(file_source_pair.path, "/tmp/test", user_context=user_context)
