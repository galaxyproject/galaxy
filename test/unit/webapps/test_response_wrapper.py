from unittest.mock import Mock

from fastapi.applications import FastAPI
from fastapi.param_functions import Depends
from fastapi.testclient import TestClient
from starlette.responses import Response

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.webapps.galaxy.api import GalaxyASGIResponse
from galaxy.work.context import SessionRequestContext

app = FastAPI()

client = TestClient(app)


def get_trans(response: Response) -> SessionRequestContext:
    galaxy_response = GalaxyASGIResponse(response)
    return SessionRequestContext(
        app=MockApp(),
        request=Mock(),
        response=galaxy_response,
    )


@app.get("/test/change_headers")
async def change_headers(trans=Depends(get_trans)):
    trans.response.headers["test-header"] = "test-value"


@app.get("/test/change_content_type")
async def change_content_type(response: Response, trans=Depends(get_trans)):
    trans.response.__response = response
    trans.response.set_content_type("test-content-type")


@app.get("/test/change_content_type_custom_response")
async def change_content_type_custom_response(trans=Depends(get_trans)):
    trans.response.set_content_type("test-content-type")
    return Response(headers=trans.response.headers)


def test_change_headers():
    response = client.get("/test/change_headers")

    assert response.status_code == 200
    assert "test-header" in response.headers
    assert response.headers["test-header"] == "test-value"


def test_change_content_type():
    response = client.get("/test/change_content_type")

    assert response.status_code == 200
    assert "content-type" in response.headers
    assert "test-content-type" in response.headers["content-type"]
    # Since we are not explicitly returning a response in `/test/change_content_type`
    # the default response will be JSONResponse, hence we will end up with both content types.
    # If we don't want this behavior we must explicitly return a response
    # like in `/test/change_content_type_custom_response`.
    assert response.headers["content-type"] == "application/json, test-content-type"


def test_change_content_type_custom_response():
    response = client.get("/test/change_content_type_custom_response")

    assert response.status_code == 200
    assert "content-type" in response.headers
    assert "test-content-type" in response.headers["content-type"]
    assert response.headers["content-type"] == "test-content-type"
