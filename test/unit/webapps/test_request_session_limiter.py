"""Requests must not exhaust the connection pool by holding sessions while they queue for threads.

A request checks a pooled connection out in its first dependency that touches
the database and keeps it until its teardown, but borrows a threadpool thread
for one dependency or the endpoint body at a time. Without a bound on the
requests that hold a session, a burst leaves every connection with a request
that queues for a thread while the threads wait for a connection, and whatever
else uses the pool (the database heartbeat) times out with them.

These tests serve real requests through Galaxy's request-session dependency,
against a real ``QueuePool`` that is smaller than the burst.
"""

import asyncio
import json
import threading
import time
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Optional

import anyio.to_thread
import pytest
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
)
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.pool import (
    NullPool,
    QueuePool,
)
from starlette.responses import (
    FileResponse,
    JSONResponse,
)

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ObjectNotFound
from galaxy.managers.agents import AgentService
from galaxy.managers.chat import ChatManager
from galaxy.model.base import ModelMapping
from galaxy.schema.agents import AgentResponse
from galaxy.schema.fields import Security
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util.config_parsers import parse_allowlist_ips
from galaxy.webapps.base.api import (
    add_exception_handler,
    add_request_id_middleware,
    GalaxyFileResponse,
    GalaxyStreamingResponse,
    release_request_sessions,
    request_session_limit,
)
from galaxy.webapps.galaxy.api import (
    agents,
    chat,
    datasets,
    depends,
    DependsOnApp,
    get_required_user,
    get_trans,
    plugins,
    proxy,
)
from galaxy.webapps.galaxy.fast_app import limiter
from galaxy.webapps.galaxy.services.datasets import DatasetsService

# Fewer threads than connections, as in production (40 threads, 50 connections).
THREADS = 4
POOL_SIZE = 6
# request_session_limit(pool of 6, 4 threads): 2 connections stay reserved, and 4 threads cap the rest.
SESSION_LIMIT = 4
# A quarter of the session slots, see long_request_turn.
LONG_REQUEST_LIMIT = 1
REQUESTS = 60
# How long a request may wait before a test calls it stuck.
STUCK = 10


class Service:
    """Resolved with ``depends``, the dependency most endpoints get their services from."""


class OtherService:
    pass


@pytest.fixture
def gx_app(monkeypatch, tmp_path):
    engines = []

    def make_app(pool_size: int = POOL_SIZE):
        def mapping(name: str) -> ModelMapping:
            engine = create_engine(
                f"sqlite:///{tmp_path / name}",
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=0,
                pool_timeout=1,
            )
            engines.append(engine)
            return ModelMapping([], engine)

        app = SimpleNamespace(
            model=mapping("galaxy.sqlite"),
            install_model=mapping("install.sqlite"),
            resolve=lambda dep_type: dep_type(),
        )
        monkeypatch.setattr("galaxy.app.app", app)
        return app

    yield make_app
    for engine in engines:
        engine.dispose()


@pytest.fixture
async def thread_limit():
    """Shrink the threadpool that sync dependencies and endpoints run in."""
    limiter = anyio.to_thread.current_default_thread_limiter()
    total_tokens = limiter.total_tokens
    limiter.total_tokens = THREADS
    yield
    limiter.total_tokens = total_tokens


@pytest.fixture
def security(monkeypatch) -> IdEncodingHelper:
    """Encodes and decodes the ids of Galaxy's API models."""
    security = IdEncodingHelper(id_secret="testing")
    monkeypatch.setattr(Security, "security", security, raising=False)
    return security


def make_api() -> FastAPI:
    api = FastAPI()
    add_request_id_middleware(api)
    add_exception_handler(api)
    return api


def client(api: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=api), base_url="http://galaxy", timeout=None)


def get_session(app=DependsOnApp):
    # The first query of a request, like the dependency that loads the Galaxy session.
    return app.model.session.execute(text("select 1")).scalar_one()


def get_user(session=Depends(get_session)):
    # A second sync dependency: the request queues for a thread again, holding its connection.
    return session


USER = SimpleNamespace(id=1, username="someone")


def galaxy_api(app, routers: list[APIRouter], services: Optional[dict[type, object]] = None) -> FastAPI:
    """Serve Galaxy's own ``routers`` with stub ``services`` and a ``trans`` that queries the database."""

    def trans(session=Depends(get_session)):
        return SimpleNamespace(
            anonymous=False,
            user=USER,
            user_is_admin=False,
            sa_session=app.model.session,
            app=SimpleNamespace(config=SimpleNamespace(fetch_url_allowlist_ips=parse_allowlist_ips(["127.0.0.1"]))),
        )

    app.resolve = lambda dep_type: (services or {}).get(dep_type, SimpleNamespace())
    api = make_api()
    for router in routers:
        api.include_router(router)
    api.dependency_overrides[get_trans] = trans
    api.dependency_overrides[get_required_user] = lambda: USER

    @api.get("/thing")
    def thing(session=Depends(get_session)):
        return {}

    return api


async def test_burst_larger_than_pool_is_served_without_pool_timeouts(gx_app, thread_limit):
    app = gx_app()
    api = make_api()
    pool = app.model.engine.pool
    checked_out = []

    @api.get("/thing")
    def thing(user=Depends(get_user), app=DependsOnApp):
        app.model.session.execute(text("select 1"))
        checked_out.append(pool.checkedout())
        time.sleep(0.01)
        return {}

    async with client(api) as http:
        responses = await asyncio.gather(*(http.get("/thing") for _ in range(REQUESTS)))

    assert [response.status_code for response in responses] == [200] * REQUESTS
    # Connections stay free for the other users of the pool, e.g. the database heartbeat.
    assert max(checked_out) <= SESSION_LIMIT < POOL_SIZE
    assert pool.checkedout() == 0


async def test_pool_user_outside_requests_gets_a_connection_during_burst(gx_app, thread_limit):
    app = gx_app()
    api = make_api()
    heartbeats = []

    @api.get("/thing")
    def thing(user=Depends(get_user), app=DependsOnApp):
        time.sleep(0.01)
        return {}

    def heartbeat(stop: threading.Event) -> None:
        # Like DatabaseHeartbeat: its own thread, a session of its own from the same pool.
        while not stop.is_set():
            with app.model.new_session() as session, session.begin():
                heartbeats.append(session.execute(text("select 1")).scalar_one())

    stop = threading.Event()
    heartbeat_thread = threading.Thread(target=heartbeat, args=(stop,))
    heartbeat_thread.start()
    try:
        async with client(api) as http:
            responses = await asyncio.gather(*(http.get("/thing") for _ in range(REQUESTS)))
    finally:
        stop.set()
        # Raises the pool's TimeoutError here if the heartbeat could not get a connection.
        await asyncio.to_thread(heartbeat_thread.join)

    assert [response.status_code for response in responses] == [200] * REQUESTS
    assert heartbeats


async def test_stream_gives_its_slot_up_before_the_body(gx_app, thread_limit):
    gx_app()
    api = make_api()
    finish_streams = asyncio.Event()

    @api.get("/stream")
    async def stream(session=Depends(get_session)):
        async def body():
            yield b"open"
            await finish_streams.wait()

        return GalaxyStreamingResponse(body())

    @api.get("/thing")
    def thing(session=Depends(get_session)):
        return {}

    async def request_while_streams_are_open(http: AsyncClient):
        try:
            return await asyncio.wait_for(http.get("/thing"), STUCK)
        finally:
            finish_streams.set()

    async with client(api) as http:
        # More open streams than there are slots: none of them may keep one.
        *streams, response = await asyncio.gather(
            *(http.get("/stream") for _ in range(SESSION_LIMIT + 2)),
            request_while_streams_are_open(http),
        )

    assert response.status_code == 200
    assert [stream.status_code for stream in streams] == [200] * (SESSION_LIMIT + 2)


def get_scope(path: str) -> dict:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "server": ("galaxy", 80),
        "client": ("client", 1),
        "root_path": "",
    }


async def download_without_reading(api: FastAPI, path: str, sending: asyncio.Event, read: asyncio.Event) -> None:
    """Request ``path`` as a client that does not read the response body until ``read`` is set."""
    scope = get_scope(path)

    async def receive():
        await read.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.body":
            sending.set()
            await read.wait()

    await api(scope, receive, send)


@pytest.mark.parametrize("path", ["/galaxy_file", "/released_file"])
async def test_download_gives_its_slot_up_before_the_body(gx_app, thread_limit, tmp_path, path):
    gx_app(pool_size=3)  # a single slot
    api = make_api()
    dataset = tmp_path / "dataset"
    dataset.write_bytes(b"content")

    @api.get("/galaxy_file")
    def galaxy_file(session=Depends(get_session)):
        return GalaxyFileResponse(dataset)

    @api.get("/released_file")
    def released_file(session=Depends(get_session)):
        release_request_sessions()
        return FileResponse(dataset)

    @api.get("/thing")
    def thing(session=Depends(get_session)):
        return {}

    sending, read = asyncio.Event(), asyncio.Event()
    download = asyncio.create_task(download_without_reading(api, path, sending, read))
    try:
        await asyncio.wait_for(sending.wait(), STUCK)
        async with client(api) as http:
            response = await asyncio.wait_for(http.get("/thing"), STUCK)
    finally:
        read.set()
        await download

    assert response.status_code == 200


async def test_request_takes_one_slot_for_all_its_dependencies(gx_app, thread_limit):
    gx_app(pool_size=3)  # a single slot
    api = make_api()

    @api.get("/thing")
    def thing(
        service: Service = depends(Service),
        other_service: OtherService = depends(OtherService),
        user=Depends(get_user),
        app=DependsOnApp,
    ):
        return {}

    async with client(api) as http:
        response = await asyncio.wait_for(http.get("/thing"), STUCK)

    assert response.status_code == 200


async def test_released_sessions_give_the_slot_up_from_a_worker_thread(gx_app, thread_limit):
    gx_app(pool_size=3)  # a single slot
    api = make_api()
    finish_upload = threading.Event()

    @api.post("/upload")
    def upload(session=Depends(get_session)):
        release_request_sessions()
        # Long work that does not use the database, e.g. reading a large request body.
        assert finish_upload.wait(STUCK)
        return {}

    @api.get("/thing")
    def thing(session=Depends(get_session)):
        return {}

    async def request_during_upload(http: AsyncClient):
        try:
            return await asyncio.wait_for(http.get("/thing"), STUCK)
        finally:
            finish_upload.set()

    async with client(api) as http:
        uploaded, response = await asyncio.gather(http.post("/upload"), request_during_upload(http))

    assert uploaded.status_code == 200
    assert response.status_code == 200


async def test_failed_request_gives_its_slot_up(gx_app, thread_limit):
    gx_app(pool_size=3)  # a single slot
    api = make_api()

    @api.get("/missing")
    def missing(service: Service = depends(Service)):
        raise ObjectNotFound("no such thing")

    @api.get("/thing")
    def thing(service: Service = depends(Service)):
        return {}

    async with client(api) as http:
        for _ in range(3):
            assert (await http.get("/missing")).status_code == 404
        response = await asyncio.wait_for(http.get("/thing"), STUCK)

    assert response.status_code == 200


async def test_failed_request_closes_its_session_before_the_error_response(gx_app, thread_limit):
    app = gx_app()
    api = make_api()
    pool = app.model.engine.pool
    checked_out = []

    class Failure(Exception):
        pass

    @api.exception_handler(Failure)
    async def failure(request, exc):
        checked_out.append(pool.checkedout())
        return JSONResponse({}, status_code=500)

    @api.get("/failing")
    def failing(service: Service = depends(Service)):
        app.model.session.execute(text("select 1"))
        raise Failure()

    async with client(api) as http:
        assert (await http.get("/failing")).status_code == 500

    assert checked_out == [0]


async def test_queued_request_is_dropped_when_its_client_goes_away(gx_app, thread_limit):
    gx_app(pool_size=3)  # a single slot
    api = make_api()
    holding, finish_slow = threading.Event(), threading.Event()
    served: list[str] = []

    @api.get("/slow")
    def slow(session=Depends(get_session)):
        holding.set()
        assert finish_slow.wait(STUCK)
        return {}

    @api.get("/thing")
    def thing(session=Depends(get_session)):
        served.append("thing")
        return {}

    listening, gone = asyncio.Event(), asyncio.Event()
    received: list[str] = []
    statuses: list[int] = []

    async def receive():
        if not received:
            received.append("body")
            return {"type": "http.request", "body": b"", "more_body": False}
        listening.set()
        await gone.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            statuses.append(message["status"])

    async with client(api) as http:
        slow_request = asyncio.create_task(http.get("/slow"))
        try:
            assert await asyncio.to_thread(holding.wait, STUCK)
            queued = asyncio.create_task(api(get_scope("/thing"), receive, send))
            await asyncio.wait_for(listening.wait(), STUCK)
            gone.set()
            await asyncio.wait_for(queued, STUCK)
        finally:
            finish_slow.set()
            gone.set()
        assert (await slow_request).status_code == 200
        response = await asyncio.wait_for(http.get("/thing"), STUCK)

    assert statuses == [499]
    assert served == ["thing"]
    assert response.status_code == 200




async def test_structured_content_gives_its_slot_up_before_the_body(gx_app, thread_limit, security):
    app = gx_app(pool_size=3)  # a single slot

    def get_structured_content(trans, dataset_id, content_type, **params):
        # Like the HDF5 datatype streaming a dataset's data from its file.
        return iter([b"chunk"] * 3), {"Content-Type": "application/octet-stream"}

    api = galaxy_api(
        app,
        [datasets.router],
        {DatasetsService: SimpleNamespace(get_structured_content=get_structured_content)},
    )
    path = f"/api/datasets/{security.encode_id(1)}/content/data"
    sending, read = asyncio.Event(), asyncio.Event()
    download = asyncio.create_task(download_without_reading(api, path, sending, read))
    try:
        await asyncio.wait_for(sending.wait(), STUCK)
        async with client(api) as http:
            response = await asyncio.wait_for(http.get("/thing"), STUCK)
    finally:
        read.set()
        await download

    assert response.status_code == 200


@asynccontextmanager
async def slow_upstream(body: bytes, content_type: str = "text/plain"):
    """An HTTP server that answers once ``answer`` is set, yielding ``(url, asked, answer)``."""
    asked, answer = asyncio.Event(), asyncio.Event()

    async def respond(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await reader.readuntil(b"\r\n\r\n")
        asked.set()
        await answer.wait()
        writer.write(
            b"HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s"
            % (content_type.encode(), len(body), body)
        )
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(respond, "127.0.0.1", 0)
    try:
        yield f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}", asked, answer
    finally:
        server.close()
        await server.wait_closed()


async def request_while_upstream_is_slow(http: AsyncClient, asked: asyncio.Event, answer: asyncio.Event):
    try:
        await asyncio.wait_for(asked.wait(), STUCK)
        # Shorter than the proxy's read timeout, after which the proxy request would give its slot up anyway.
        return await asyncio.wait_for(http.get("/thing"), 5)
    finally:
        answer.set()


async def test_proxy_gives_its_slot_up_while_it_waits_for_the_upstream(gx_app, thread_limit):
    app = gx_app(pool_size=3)  # a single slot
    api = galaxy_api(app, [proxy.router])

    async with slow_upstream(b"ok") as (url, asked, answer), client(api) as http:
        proxied, response = await asyncio.gather(
            http.get("/api/proxy", params={"url": f"{url}/file"}),
            request_while_upstream_is_slow(http, asked, answer),
        )

    assert response.status_code == 200
    assert proxied.status_code == 200
    assert proxied.content == b"ok"


async def test_plugin_chat_gives_its_slot_up_while_it_waits_for_the_model(gx_app, thread_limit):
    app = gx_app(pool_size=3)  # a single slot
    app.visualizations_registry = SimpleNamespace(
        get_plugin=lambda name: SimpleNamespace(config={"specs": {"ai_prompt": "Help with notebooks."}})
    )
    completion = {
        "id": "completion",
        "object": "chat.completion",
        "created": 0,
        "model": "model",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "answer"}}],
    }

    async with slow_upstream(json.dumps(completion).encode(), "application/json") as (url, asked, answer):
        config = SimpleNamespace(inference_services=None, ai_model="model", ai_api_key="key", ai_api_base_url=url)
        api = galaxy_api(app, [plugins.router], {GalaxyAppConfiguration: config})
        api.state.limiter = limiter
        async with client(api) as http:
            reply, response = await asyncio.gather(
                http.post(
                    "/api/plugins/jupyterlite/chat/completions",
                    json={"messages": [{"role": "user", "content": "why did my job fail?"}]},
                ),
                request_while_upstream_is_slow(http, asked, answer),
            )

    assert response.status_code == 200
    assert reply.status_code == 200
    assert reply.json()["choices"][0]["message"]["content"] == "answer"


@pytest.mark.parametrize(
    "path,params,body",
    [
        ("/api/chat", {"query": "why did my job fail?"}, None),
        ("/api/ai/agents/query", None, {"query": "why did my job fail?"}),
    ],
)
async def test_language_model_queries_leave_slots_to_other_requests(gx_app, thread_limit, security, path, params, body):
    app = gx_app()
    answer = asyncio.Event()
    queries = []

    async def route_and_execute(query, trans, user, context, agent_type):
        # The agents query Galaxy while they wait for the model, so they keep the request's session.
        queries.append(query)
        await answer.wait()
        return AgentResponse(content="answer", confidence="high", agent_type="router")

    api = galaxy_api(
        app,
        [chat.router, agents.router],
        {
            AgentService: SimpleNamespace(route_and_execute=route_and_execute),
            ChatManager: SimpleNamespace(
                resolve_page_from_interface_context=lambda trans, query_context: (None, None),
                create_general_chat=lambda trans, query, result, agent_type: SimpleNamespace(id=1),
            ),
        },
    )
    asking = []

    async def request_while_model_is_slow(http: AsyncClient):
        try:
            while not queries:
                await asyncio.sleep(0.01)
            # Give the other queries time to take whatever slots they may.
            await asyncio.sleep(0.5)
            asking.append(len(queries))
            return await asyncio.wait_for(http.get("/thing"), STUCK)
        finally:
            answer.set()

    async with client(api) as http:
        *replies, response = await asyncio.gather(
            *(http.post(path, params=params, json=body) for _ in range(SESSION_LIMIT + 1)),
            asyncio.wait_for(request_while_model_is_slow(http), STUCK * 2),
        )

    assert response.status_code == 200
    assert asking == [LONG_REQUEST_LIMIT]
    assert [reply.status_code for reply in replies] == [200] * (SESSION_LIMIT + 1)
    # /api/chat answers errors with a 200 too.
    assert [reply.json().get("error_code", 0) for reply in replies] == [0] * (SESSION_LIMIT + 1)
    assert len(queries) == SESSION_LIMIT + 1


@pytest.mark.parametrize(
    "pool_size,max_overflow,thread_tokens,expected",
    [
        (20, 30, 40, 40),  # usegalaxy.org: a fifth of the pool stays reserved
        (30, 40, 40, 40),  # usegalaxy.eu: no more sessions than threads to use them
        (30, 40, 100, 56),
        (5, 10, 40, 12),  # SQLAlchemy defaults
        (2, 0, 40, 1),  # always at least one
        (5, -1, 40, None),  # unlimited overflow
        (0, 0, 40, None),  # unlimited pool
    ],
)
def test_request_session_limit(pool_size, max_overflow, thread_tokens, expected):
    engine = create_engine("sqlite://", poolclass=QueuePool, pool_size=pool_size, max_overflow=max_overflow)
    assert request_session_limit(engine.pool, thread_tokens) == expected


def test_request_session_limit_only_applies_to_bounded_pools():
    assert request_session_limit(create_engine("sqlite://", poolclass=NullPool).pool, 40) is None
