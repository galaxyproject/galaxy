import io
import json
import os
from typing import Any

import pytest
import responses

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
def test_file_source_drs_s3():
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


def _download_response(request, **kwargs):
    response: Any = io.StringIO("hello drs world")
    response.headers = {}
    response.geturl = lambda: request.full_url
    return response
