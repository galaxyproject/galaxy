import pytest
import requests
import responses

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


def test_get_url_retry_after():
    # This test is not ideal since it contacts an external resource
    # and doesn't acutally verify multiple attempts have been made.
    # responses doesn't mock the right place to fully simulate this.
    url = "https://httpbin.org/status/429"
    with pytest.raises(requests.exceptions.RetryError):
        url_get(url, max_retries=2, backoff_factor=0.01)
