import pytest
import requests
import responses
from werkzeug.wrappers.response import Response

from galaxy.util import url_get


@responses.activate
def test_get_url_ok():
    url = "https://toolshed.g2.bx.psu.edu/"
    responses.add(responses.GET, url, body="OK", status=200)
    text = url_get(url)
    assert text == "OK"


@responses.activate
def test_get_url_forbidden():
    url = "https://toolshed.g2.bx.psu.edu/"
    responses.add(responses.GET, url, body="Forbidden", status=403)
    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        url_get(url)
    assert "403 Client Error: Forbidden for url: https://toolshed.g2.bx.psu.edu/" in str(excinfo)


def test_get_url_retry_after(httpserver):
    attempts = []

    def retry_handler(request):
        attempts.append(request)
        if len(attempts) < 4:
            return Response("try again later", status=429, content_type="text/plain")
        else:
            return Response("ok", status=200, content_type="text/plain")

    httpserver.expect_request("/429").respond_with_handler(retry_handler)
    url = httpserver.url_for("/429")
    with pytest.raises(requests.exceptions.RetryError):
        url_get(url, max_retries=1, backoff_factor=0.01)
    assert len(attempts) == 2
    response = url_get(url, max_retries=2, backoff_factor=0.01)
    assert len(attempts) == 4
    assert response == "ok"
