import io
import ipaddress
import json
import os
from typing import Any
from unittest import mock

import pytest
import responses

from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    RequestParameterInvalidException,
)
from galaxy.files.sources.util import (
    fetch_drs_to_file,
    RetryOptions,
)
from ._util import (
    assert_realizes_as,
    assert_realizes_contains,
    configured_file_sources,
    patch_http_open,
    user_context_fixture,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "drs_file_sources_conf.yml")


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_file_source_drs_http():
    def drs_repo_handler(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        data = {
            "id": "314159",
            "name": "hello-314159",
            "access_methods": [
                {
                    "type": "https",
                    "access_id": "1234",
                }
            ],
        }
        return (200, {}, json.dumps(data))

    def access_handler(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        access_data = {
            "url": "https://my.respository.org/myfile.txt",
            "headers": ["Authorization: Basic Z2E0Z2g6ZHJz"],
        }
        return (200, {}, json.dumps(access_data))

    responses.add_callback(
        responses.GET,
        "https://drs.example.org/ga4gh/drs/v1/objects/314159",
        callback=drs_repo_handler,
        content_type="application/json",
    )

    responses.add_callback(
        responses.GET,
        "https://drs.example.org/ga4gh/drs/v1/objects/314159/access/1234",
        callback=access_handler,
        content_type="application/json",
    )

    test_url = "drs://drs.example.org/314159"

    def check_specific_header(request, **kwargs):
        assert request.full_url == "https://my.respository.org/myfile.txt"
        assert request.headers["Authorization"] == "Basic Z2E0Z2g6ZHJz"
        response: Any = io.StringIO("hello drs world")
        response.headers = {}
        response.geturl = lambda: test_url
        return response

    with patch_http_open(check_specific_header):
        user_context = user_context_fixture()
        file_sources = configured_file_sources(FILE_SOURCES_CONF)
        file_source_pair = file_sources.get_file_source_path(test_url)

        assert file_source_pair.path == test_url
        assert file_source_pair.file_source.id == "test1"

        assert_realizes_as(file_sources, test_url, "hello drs world", user_context=user_context)


@responses.activate
@mock.patch("galaxy.files.uris.validate_non_local")
def test_file_source_drs_s3(_validate_non_local):
    def drs_repo_handler(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        data = {
            "id": "314160",
            "name": "hello-314160",
            "access_methods": [
                {
                    "type": "s3",
                    "access_id": "1234",
                    "region": "us-east-1",
                }
            ],
        }
        return (200, {}, json.dumps(data))

    def access_handler(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        access_data = {
            "url": "s3://ga4gh-demo-data/phenopackets/Cao-2018-TGFBR2-Patient_4.json",
        }
        return (200, {}, json.dumps(access_data))

    responses.add_callback(
        responses.GET,
        "https://drs.example.org/ga4gh/drs/v1/objects/314160",
        callback=drs_repo_handler,
        content_type="application/json",
    )

    responses.add_callback(
        responses.GET,
        "https://drs.example.org/ga4gh/drs/v1/objects/314160/access/1234",
        callback=access_handler,
        content_type="application/json",
    )

    test_url = "drs://drs.example.org/314160"
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    user_context = user_context_fixture(file_sources=file_sources)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    assert_realizes_contains(
        file_sources, test_url, "PMID:30101859-Cao-2018-TGFBR2-Patient_4", user_context=user_context
    )


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_file_source_drs_access_lookup_sends_headers():
    object_url = "https://drs.example.org/ga4gh/drs/v1/objects/314161"
    responses.get(object_url, json={"id": "314161", "access_methods": [{"type": "https", "access_id": "1234"}]})

    def access_handler(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        assert request.headers["User-Agent"].startswith("galaxy/")
        return (200, {}, json.dumps({"url": "https://my.respository.org/myfile.txt"}))

    responses.add_callback(responses.GET, f"{object_url}/access/1234", callback=access_handler)

    with patch_http_open(_download_response):
        file_sources = configured_file_sources(FILE_SOURCES_CONF)
        assert_realizes_as(
            file_sources, "drs://drs.example.org/314161", "hello drs world", user_context=user_context_fixture()
        )


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_lookups_keep_galaxy_user_agent_over_configured_one(tmp_path):
    object_url = "https://drs.example.org/ga4gh/drs/v1/objects/1"
    responses.get(object_url, json={"access_methods": [{"type": "https", "access_id": "1234"}]})
    responses.get(f"{object_url}/access/1234", json={"url": "https://my.respository.org/myfile.txt"})
    with patch_http_open(_download_response):
        fetch_drs_to_file(
            "drs://drs.example.org/1", tmp_path / "out", user_context=None, headers={"User-Agent": "custom"}
        )
    assert [call.request.headers["User-Agent"].split("/")[0] for call in responses.calls] == ["galaxy"] * 2


def _download_response(request, **kwargs):
    response: Any = io.StringIO("hello drs world")
    response.headers = {}
    response.geturl = lambda: request.full_url
    return response


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_retry_after_202_keeps_headers(tmp_path):
    object_url = "https://drs.example.org/ga4gh/drs/v1/objects/314162"
    responses.get(object_url, status=202, headers={"Retry-After": "1"})
    responses.get(object_url, json=_public_object())
    retry_options = RetryOptions()
    retry_options.override_retry_after = 0.01

    with patch_http_open(_download_response):
        fetch_drs_to_file(
            "drs://drs.example.org/314162",
            tmp_path / "out",
            user_context=None,
            retry_options=retry_options,
            headers={"Authorization": "Bearer IBearTokens"},
        )

    assert [call.request.headers.get("Authorization") for call in responses.calls] == ["Bearer IBearTokens"] * 2


@responses.activate
def test_drs_object_lookup_refuses_private_address(tmp_path):
    with pytest.raises(ConfigDoesNotAllowException):
        fetch_drs_to_file("drs://127.0.0.1/1", tmp_path / "out", user_context=None, force_http=True)
    assert len(responses.calls) == 0


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_object_lookup_refuses_redirect_to_private_address(tmp_path):
    responses.get(
        "https://drs.example.org/ga4gh/drs/v1/objects/1",
        status=302,
        headers={"Location": "http://127.0.0.1:8000/secret"},
    )
    with pytest.raises(ConfigDoesNotAllowException):
        fetch_drs_to_file("drs://drs.example.org/1", tmp_path / "out", user_context=None)
    assert [call.request.url for call in responses.calls] == ["https://drs.example.org/ga4gh/drs/v1/objects/1"]


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_access_lookup_refuses_redirect_to_private_address(tmp_path):
    object_url = "https://drs.example.org/ga4gh/drs/v1/objects/1"
    responses.get(object_url, json={"access_methods": [{"type": "https", "access_id": "1234"}]})
    responses.get(f"{object_url}/access/1234", status=302, headers={"Location": "http://127.0.0.1:8000/secret"})
    with pytest.raises(ConfigDoesNotAllowException):
        fetch_drs_to_file("drs://drs.example.org/1", tmp_path / "out", user_context=None)
    assert [call.request.url for call in responses.calls] == [object_url, f"{object_url}/access/1234"]


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_compact_identifier_lookup_refuses_redirect_to_private_address(tmp_path):
    resolved_url = "https://drs.example.org/ga4gh/drs/v1/objects/1"
    responses.get(resolved_url, status=302, headers={"Location": "http://127.0.0.1:8000/secret"})
    with mock.patch("galaxy.files.sources.util.resolve_compact_identifier_to_url", return_value=resolved_url):
        with pytest.raises(ConfigDoesNotAllowException):
            fetch_drs_to_file("drs://test.prefix:1", tmp_path / "out", user_context=None)
    assert [call.request.url for call in responses.calls] == [resolved_url]


@responses.activate
def test_drs_compact_identifier_refuses_private_resolved_url(tmp_path):
    with mock.patch(
        "galaxy.files.sources.util.resolve_compact_identifier_to_url",
        return_value="http://127.0.0.1:8000/ga4gh/drs/v1/objects/1",
    ):
        with pytest.raises(ConfigDoesNotAllowException):
            fetch_drs_to_file("drs://test.prefix:1", tmp_path / "out", user_context=None)
    assert len(responses.calls) == 0


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_unverifiable_access_url_keeps_verification_error(tmp_path):
    responses.get(
        "https://drs.example.org/ga4gh/drs/v1/objects/1",
        json={"access_methods": [{"type": "https", "access_url": {"url": "https://exa%6dple.org/myfile.txt"}}]},
    )
    with pytest.raises(RequestParameterInvalidException, match="Could not verify url"):
        fetch_drs_to_file("drs://drs.example.org/1", tmp_path / "out", user_context=None)


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_private_access_url_keeps_refusal(tmp_path):
    responses.get(
        "https://drs.example.org/ga4gh/drs/v1/objects/1",
        json={"access_methods": [{"type": "https", "access_url": {"url": "http://127.0.0.1:8000/secret"}}]},
    )
    with pytest.raises(ConfigDoesNotAllowException):
        fetch_drs_to_file("drs://drs.example.org/1", tmp_path / "out", user_context=None)


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_skips_access_method_without_handler(tmp_path):
    responses.get(
        "https://drs.example.org/ga4gh/drs/v1/objects/1",
        json={
            "access_methods": [
                {"type": "gsiftp", "access_url": {"url": "gsiftp://example.org/myfile.txt"}},
                *_public_object()["access_methods"],
            ]
        },
    )
    with patch_http_open(_download_response):
        fetch_drs_to_file("drs://drs.example.org/1", tmp_path / "out", user_context=None)
    assert (tmp_path / "out").read_text() == "hello drs world"


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_ftp_access_method_honours_allowlist_without_user_context(tmp_path):
    responses.get(
        "https://drs.example.org/ga4gh/drs/v1/objects/1",
        json={"access_methods": [{"type": "ftp", "access_url": {"url": "ftp://10.1.2.3/myfile.txt"}}]},
    )
    with patch_http_open(_download_response):
        fetch_drs_to_file(
            "drs://drs.example.org/1",
            tmp_path / "out",
            user_context=None,
            fetch_url_allowlist=[ipaddress.ip_network("10.0.0.0/8")],
        )
    assert (tmp_path / "out").read_text() == "hello drs world"


def _public_object():
    return {
        "access_methods": [{"type": "https", "access_url": {"url": "https://my.respository.org/myfile.txt"}}],
    }
