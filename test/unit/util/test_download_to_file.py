import pytest
import requests
from werkzeug.wrappers.response import Response

from galaxy.util import download_to_file


def test_download_to_file_ok(httpserver, tmp_path):
    httpserver.expect_request("/installer.sh").respond_with_data("echo hello")
    dest = tmp_path / "installer.sh"
    download_to_file(httpserver.url_for("/installer.sh"), str(dest))
    assert dest.read_text() == "echo hello"


def test_download_to_file_client_error_not_written(httpserver, tmp_path):
    attempts = []

    def handler(request):
        attempts.append(request)
        return Response("<html><body><h1>404 Not Found</h1>", status=404, content_type="text/html")

    httpserver.expect_request("/installer.sh").respond_with_handler(handler)
    dest = tmp_path / "installer.sh"
    with pytest.raises(requests.exceptions.HTTPError, match="404"):
        download_to_file(httpserver.url_for("/installer.sh"), str(dest))
    # 4xx (other than 429) is not transient, so it isn't retried
    assert len(attempts) == 1
    assert not dest.exists()


def test_download_to_file_retries_server_error(httpserver, tmp_path):
    attempts = []

    def handler(request):
        attempts.append(request)
        if len(attempts) < 2:
            return Response("<html><body><h1>504 Gateway Time-out</h1>", status=504, content_type="text/html")
        return Response("echo hello", status=200, content_type="text/plain")

    httpserver.expect_request("/installer.sh").respond_with_handler(handler)
    dest = tmp_path / "installer.sh"
    download_to_file(httpserver.url_for("/installer.sh"), str(dest))
    assert len(attempts) == 2
    assert dest.read_text() == "echo hello"


def test_download_to_file_server_error_exhausts_retries(httpserver, tmp_path):
    attempts = []

    def handler(request):
        attempts.append(request)
        return Response("<html><body><h1>504 Gateway Time-out</h1>", status=504, content_type="text/html")

    httpserver.expect_request("/installer.sh").respond_with_handler(handler)
    dest = tmp_path / "installer.sh"
    with pytest.raises(requests.exceptions.HTTPError, match="504"):
        download_to_file(httpserver.url_for("/installer.sh"), str(dest), max_retries=2, backoff_factor=0)
    assert len(attempts) == 3
    assert not dest.exists()
