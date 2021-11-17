from fastapi.applications import FastAPI
from fastapi.testclient import TestClient

from galaxy.webapps.galaxy.api import DependsOnTrans  # TODO mock most of the dependencies?

app = FastAPI()

client = TestClient(app)

OK_RESPONSE = {"msg": "OK"}


@app.get("/test/change_headers")
async def change_headers(trans=DependsOnTrans):
    trans.response.headers["test-header"] = "test-value"
    return OK_RESPONSE


@app.get("/test/change_content_type")
async def change_content_type(trans=DependsOnTrans):
    trans.response.set_content_type("test-content-type")
    return OK_RESPONSE


def test_change_headers():
    response = client.get("/test/change_headers")

    _assert_response_ok(response)
    assert "test-header" in response.headers
    assert response.headers["test-header"] == "test-value"


def test_change_content_type():
    response = client.get("/test/change_content_type")

    _assert_response_ok(response)
    assert "content-type" in response.headers
    assert response.headers["content-type"] == "test-content-type"


def _assert_response_ok(response):
    assert response.status_code == 200
    assert response.json() == OK_RESPONSE
