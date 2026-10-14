import gzip
import io
from typing import cast
from unittest import mock

import responses
from requests import Response
from tools.data_source import data_source


class FTPResponse(io.BytesIO):
    headers: dict[str, str]


@responses.activate
def test_open_remote_source_get_streams_and_closes():
    url = "https://example.com/data"
    responses.add(
        responses.GET,
        url,
        body=gzip.compress(b"result", mtime=0),
        headers={"Content-Encoding": "gzip"},
    )

    with data_source._open_remote_source(url, "get", {}, {"X-Test": "yes"}) as (source, headers):
        assert source.read() == b"result"
        assert headers is not None

    assert responses.calls[0].request.headers["X-Test"] == "yes"
    response = cast(Response, responses.calls[0].response)
    assert response.raw.closed


@responses.activate
def test_open_remote_source_post_sends_form_and_closes():
    url = "https://example.com/data"

    def check_form(request):
        assert request.body == "gene=BRCA1"
        return 200, {}, b"result"

    responses.add_callback(responses.POST, url, callback=check_form)
    with data_source._open_remote_source(url, "post", {"gene": "BRCA1"}, {}) as (source, _):
        assert source.read() == b"result"

    response = cast(Response, responses.calls[0].response)
    assert response.raw.closed


def test_open_remote_source_keeps_ftp_fallback():
    response = FTPResponse(b"ftp result")
    response.headers = {}
    with mock.patch.object(data_source, "urlopen", return_value=response) as urlopen:
        with data_source._open_remote_source("ftp://example.com/data", "get", {}, {}) as (source, _):
            assert source.read() == b"ftp result"

    request = urlopen.call_args.args[0]
    assert request.full_url == "ftp://example.com/data"
    assert response.closed
