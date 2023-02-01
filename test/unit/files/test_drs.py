import json
import os

import responses

from ._util import configured_file_sources, user_context_fixture, assert_realizes_as

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "drs_file_sources_conf.yml")


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
                    "access_url": {
                        "url": "https://my.respository.org/myfile.txt",
                        "headers": ["Authorization: Basic Z2E0Z2g6ZHJz"],
                    },
                    "access_id": "1234",
                }
            ],
        }
        return (200, {}, json.dumps(data))

    responses.add_callback(
        responses.GET,
        "https://drs.example.org/ga4gh/drs/v1/objects/314159",
        callback=drs_repo_handler,
        content_type="application/json",
    )

    responses.get("https://my.respository.org/myfile.txt", body="hello drs world")

    test_url = "drs://drs.example.org/314159"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    assert_realizes_as(file_sources, test_url, "hello drs world", user_context=user_context)
