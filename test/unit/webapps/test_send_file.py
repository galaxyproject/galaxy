import tempfile

import pytest
from a2wsgi import WSGIMiddleware
from fastapi.applications import FastAPI
from fastapi.testclient import TestClient

from galaxy.util.bunch import Bunch
from galaxy.web.framework.base import (
    Request,
    Response,
    send_file,
)

CONTENT = "content"


def setup_fastAPI(fh, nginx_x_accel_redirect_base=None, apache_xsendfile=None):
    def wsgi_application(env, start_response):
        trans = Bunch(
            response=Response(),
            request=Request(env),
            app=Bunch(
                config=Bunch(nginx_x_accel_redirect_base=nginx_x_accel_redirect_base, apache_xsendfile=apache_xsendfile)
            ),
        )
        trans.response.headers["content-length"] = len(CONTENT)
        trans.response.set_content_type("application/octet-stream")
        return send_file(start_response, trans, fh)

    app = FastAPI()
    # https://github.com/abersheeran/a2wsgi/issues/44
    app.mount("/test/send_file", WSGIMiddleware(wsgi_application))  # type: ignore[arg-type]
    return app


@pytest.fixture
def test_file_handle():
    with tempfile.NamedTemporaryFile() as fh:
        fh.write(b"content")
        fh.flush()
        fh.seek(0)
        yield fh


def test_sendfile_nginx(test_file_handle):
    app = setup_fastAPI(test_file_handle, nginx_x_accel_redirect_base="/base")
    client = TestClient(app)
    response = client.get("/test/send_file")
    assert response.status_code == 200
    assert response.headers["x-accel-redirect"] == f"/base{test_file_handle.name}"
    assert "content-length" not in response.headers
    assert not response.content


def test_sendfile_apache(test_file_handle):
    app = setup_fastAPI(test_file_handle, apache_xsendfile="/base")
    client = TestClient(app)
    response = client.get("/test/send_file")
    assert response.status_code == 200
    assert response.headers["X-Sendfile"] == test_file_handle.name
    assert "content-length" not in response.headers
    assert not response.content


def test_sendfile_in_process(test_file_handle):
    app = setup_fastAPI(test_file_handle)
    client = TestClient(app)
    response = client.get("/test/send_file")
    assert response.status_code == 200
    assert "X-Sendfile" not in response.headers
    assert "x-accel-redirect" not in response.headers
    assert response.headers["content-length"] == str(len(CONTENT))
    assert response.content.decode() == "content"
