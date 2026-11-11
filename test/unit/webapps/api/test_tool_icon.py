from unittest import mock

import pytest
from starlette.requests import Request

from galaxy.webapps.galaxy.api.tools import FetchTools


def _request(headers=None):
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw_headers})


@pytest.fixture
def icon_path(tmp_path):
    path = tmp_path / "icon.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
    return str(path)


@pytest.fixture
def controller(icon_path):
    controller = FetchTools.__new__(FetchTools)
    controller.service = mock.Mock()
    controller.service.get_tool_icon_path.return_value = icon_path
    return controller


def _get_icon(controller, headers=None):
    return controller.get_icon(_request(headers), "my_tool", trans=mock.Mock())


def test_icon_served_with_validators(controller):
    response = _get_icon(controller)
    assert response.status_code == 200
    assert response.headers["ETag"].startswith('"')
    assert "Last-Modified" in response.headers
    assert "immutable" not in response.headers["Cache-Control"]


@pytest.mark.parametrize(
    "if_none_match",
    [
        "{etag}",
        "W/{etag}",
        '"other", {etag}',
        "*",
    ],
)
def test_if_none_match_returns_304(controller, if_none_match):
    etag = _get_icon(controller).headers["ETag"]
    response = _get_icon(controller, {"If-None-Match": if_none_match.format(etag=etag)})
    assert response.status_code == 304
    assert response.headers["ETag"] == etag
    assert "Cache-Control" in response.headers


def test_if_none_match_mismatch_returns_200(controller):
    response = _get_icon(controller, {"If-None-Match": '"something-else"'})
    assert response.status_code == 200


def test_if_modified_since_returns_304(controller):
    first = _get_icon(controller)
    response = _get_icon(controller, {"If-Modified-Since": first.headers["Last-Modified"]})
    assert response.status_code == 304
    assert response.headers["ETag"] == first.headers["ETag"]


def test_if_none_match_takes_precedence_over_if_modified_since(controller):
    first = _get_icon(controller)
    response = _get_icon(
        controller,
        {"If-None-Match": '"something-else"', "If-Modified-Since": first.headers["Last-Modified"]},
    )
    assert response.status_code == 200
