import tempfile

import pytest
from fastapi import HTTPException
from fastapi.applications import FastAPI
from fastapi.testclient import TestClient

from galaxy.webapps.base.api import (
    _get_range_header,
    GalaxyFileResponse,
)


@pytest.mark.parametrize(
    "range_header, expected",
    [
        ("bytes=0-499", (0, 499)),
        ("bytes=500-", (500, 999)),
        ("bytes=-500", (500, 999)),
        ("bytes=-1", (999, 999)),
        ("bytes=-5000", (0, 999)),
        ("bytes=0-5000", (0, 999)),
        ("bytes=999-999", (999, 999)),
        ("Bytes=0-1", (0, 1)),
        ("bytes = 0 - 1", (0, 1)),
    ],
)
def test_get_range_header(range_header, expected):
    assert _get_range_header(range_header, 1000) == expected


@pytest.mark.parametrize("range_header", ["", "bytes=0-1,3-4", "items=0-1"])
def test_get_range_header_ignored(range_header):
    assert _get_range_header(range_header, 1000) is None


@pytest.mark.parametrize(
    "range_header, file_size",
    [
        ("bytes=1000-", 1000),
        ("bytes=-0", 1000),
        ("bytes=-1", 0),
        ("bytes=500-499", 1000),
        ("bytes=-", 1000),
        ("bytes", 1000),
        ("bytes=a-b", 1000),
        ("bytes=\u0661-", 1000),
        ("bytes=-1-1", 1000),
        ("bytes=--5", 1000),
        ("bytes=" + " " * 65536 + "x", 1000),
        ("bytes=" + "1" * 5000 + "-", 1000),
    ],
    ids=lambda value: value if not isinstance(value, str) or len(value) < 20 else f"{value[:10]}...",
)
def test_get_range_header_unsatisfiable(range_header, file_size):
    with pytest.raises(HTTPException) as exc_info:
        _get_range_header(range_header, file_size)
    assert exc_info.value.status_code == 416
    assert exc_info.value.headers == {"content-range": f"bytes */{file_size}"}


@pytest.fixture
def file_client():
    with tempfile.NamedTemporaryFile() as fh:
        fh.write(b"content")
        fh.flush()
        app = FastAPI()

        @app.get("/file")
        def serve_file():
            return GalaxyFileResponse(fh.name)

        yield TestClient(app)


def test_file_response_suffix_range(file_client):
    response = file_client.get("/file", headers={"Range": "bytes=-3"})
    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 4-6/7"
    assert response.headers["content-length"] == "3"
    assert response.content == b"ent"


def test_file_response_multiple_ranges_serves_whole_file(file_client):
    response = file_client.get("/file", headers={"Range": "bytes=0-1,3-4"})
    assert response.status_code == 200
    assert "content-range" not in response.headers
    assert response.content == b"content"


def test_file_response_unsatisfiable_range(file_client):
    response = file_client.get("/file", headers={"Range": "bytes=7-"})
    assert response.status_code == 416
    assert response.headers["content-range"] == "bytes */7"
