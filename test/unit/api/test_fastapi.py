import uuid

import pytest
from fastapi import FastAPI
from fastapi.param_functions import Depends
from fastapi.testclient import TestClient


from galaxy.webapps.galaxy.fast_app import (
    add_exception_handler,
    add_sa_session_middleware,
)

from ..unittest_utils.galaxy_mock import MockApp

app = FastAPI()
GX_APP = None


def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


class UnexpectedException(Exception):
    pass

def get_app():
    global GX_APP
    if GX_APP is None:
        GX_APP = MockApp()
    return GX_APP


@app.get("/")
async def read_main(app=Depends(get_app)):
    assert app.model.scoped_registry.registry == {}
    app.model.session()
    assert len(app.model.scoped_registry.registry) == 1
    assert is_valid_uuid(next(iter(app.model.scoped_registry.registry.keys())))
    return {"msg": "Hello World"}


@app.get('/internal_server_error')
def error(app=Depends(get_app)):
    assert app.model.scoped_registry.registry == {}
    app.model.session()
    assert len(app.model.scoped_registry.registry) == 1
    assert is_valid_uuid(next(iter(app.model.scoped_registry.registry.keys())))
    raise UnexpectedException('Oh noes!')


def test_sa_session_middleware():
    gx_app = get_app()
    add_exception_handler(app)
    add_sa_session_middleware(app, gx_app=gx_app)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}
    assert gx_app.model.scoped_registry.registry == {}
    with pytest.raises(UnexpectedException):
        response = client.get("/internal_server_error")
    assert gx_app.model.scoped_registry.registry == {}