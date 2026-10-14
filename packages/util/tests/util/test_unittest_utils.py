from unittest import SkipTest

import pytest

from galaxy.util.unittest_utils import (
    raise_skip_if_site_down,
    skip_if_site_down,
)


def test_raise_skip_if_site_down_passes_when_site_is_up(httpserver):
    httpserver.expect_request("/").respond_with_data("ok")
    raise_skip_if_site_down(httpserver.url_for("/"))


def test_raise_skip_if_site_down_skips_with_reason(httpserver):
    httpserver.expect_request("/").respond_with_data("down", status=503)
    url = httpserver.url_for("/")
    with pytest.raises(SkipTest, match=rf"Test depends on \[{url}\] being up and it appears to be down \(HTTP 503\)"):
        raise_skip_if_site_down(url)


def test_skip_if_site_down_skips_without_running_the_test(httpserver):
    httpserver.expect_request("/").respond_with_data("down", status=503)
    calls = []

    @skip_if_site_down(httpserver.url_for("/"))
    def test_remote():
        calls.append(True)

    with pytest.raises(SkipTest, match=r"\(HTTP 503\)"):
        test_remote()
    assert calls == []
