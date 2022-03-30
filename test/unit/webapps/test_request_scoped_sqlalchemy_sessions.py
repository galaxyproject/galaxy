import asyncio
import concurrent.futures
import functools
import threading
import time
import uuid

import pytest
from fastapi import FastAPI
from fastapi.param_functions import Depends
from httpx import AsyncClient
from starlette_context import context as request_context

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.webapps.base.api import add_request_id_middleware

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


async def _get_app():
    global GX_APP
    if not GX_APP:
        GX_APP = MockApp()
        GX_APP.stop = False
    app = GX_APP
    request_id = request_context.data["X-Request-ID"]
    app.model.set_request_id(request_id)
    try:
        yield app
    finally:
        app.model.unset_request_id(request_id)


async def get_app(app=Depends(_get_app)):
    return app


@app.get("/")
async def read_main(app=Depends(get_app)):
    assert app.model.scoped_registry.registry == {}
    app.model.session()
    assert len(app.model.scoped_registry.registry) == 1
    request_id = app.model.request_scopefunc()
    assert is_valid_uuid(request_id)
    return {"msg": "Hello World"}


@app.get("/internal_server_error")
def error(app=Depends(get_app)):
    assert app.model.scoped_registry.registry == {}
    app.model.session()
    assert len(app.model.scoped_registry.registry) == 1
    request_id = app.model.request_scopefunc()
    assert is_valid_uuid(request_id)
    raise UnexpectedException("Oh noes!")


@app.get("/sync_wait")
def sync_wait(app=Depends(get_app)):
    app.model.session()
    time.sleep(0.2)
    request_id = app.model.request_scopefunc()
    assert is_valid_uuid(request_id)
    return request_id


@app.get("/async_wait")
async def async_wait(app=Depends(get_app)):
    app.model.session()
    await asyncio.sleep(0.2)
    request_id = app.model.request_scopefunc()
    assert is_valid_uuid(request_id)
    return request_id


def assert_scoped_session_is_thread_local(gx_app):
    while not gx_app.stop:
        time.sleep(0.1)
        request_id = gx_app.model.request_scopefunc()
        assert request_id == threading.get_ident()


@pytest.mark.asyncio
async def test_request_scoped_sa_session_single_request():
    add_request_id_middleware(app)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"msg": "Hello World"}
        assert GX_APP
        assert GX_APP.model.scoped_registry.registry == {}


@pytest.mark.asyncio
async def test_request_scoped_sa_session_exception():
    add_request_id_middleware(app)
    async with AsyncClient(app=app, base_url="http://test") as client:
        with pytest.raises(UnexpectedException):
            await client.get("/internal_server_error")
        assert GX_APP
        assert GX_APP.model.scoped_registry.registry == {}


@pytest.mark.asyncio
async def test_request_scoped_sa_session_concurrent_requests_sync():
    add_request_id_middleware(app)
    async with AsyncClient(app=app, base_url="http://test") as client:
        awaitables = (client.get("/sync_wait") for _ in range(10))
        result = await asyncio.gather(*awaitables)
        uuids = []
        for r in result:
            assert r.status_code == 200
            uuids.append(r.json())
        assert len(set(uuids)) == 10
        assert GX_APP
        assert GX_APP.model.scoped_registry.registry == {}


@pytest.mark.asyncio
async def test_request_scoped_sa_session_concurrent_requests_async():
    add_request_id_middleware(app)
    async with AsyncClient(app=app, base_url="http://test") as client:
        awaitables = (client.get("/async_wait") for _ in range(10))
        result = await asyncio.gather(*awaitables)
        uuids = []
        for r in result:
            assert r.status_code == 200
            uuids.append(r.json())
        assert len(set(uuids)) == 10
        assert GX_APP
        assert GX_APP.model.scoped_registry.registry == {}


@pytest.mark.asyncio
async def test_request_scoped_sa_session_concurrent_requests_and_background_thread():
    add_request_id_middleware(app)
    loop = asyncio.get_running_loop()
    target = functools.partial(assert_scoped_session_is_thread_local, GX_APP)
    with concurrent.futures.ThreadPoolExecutor() as pool:
        background_pool = loop.run_in_executor(pool, target)
        async with AsyncClient(app=app, base_url="http://test") as client:
            awaitables = (client.get("/async_wait") for _ in range(10))
            result = await asyncio.gather(*awaitables)
            uuids = []
            for r in result:
                assert r.status_code == 200
                uuids.append(r.json())
            assert len(set(uuids)) == 10
            assert GX_APP
            assert GX_APP.model.scoped_registry.registry == {}
        GX_APP.stop = True
        await background_pool
