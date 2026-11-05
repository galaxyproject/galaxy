"""
Original implementation by David Montague (@dmontagu)
https://github.com/dmontagu/fastapi-utils
"""

from collections.abc import (
    AsyncIterator,
    Callable,
    Coroutine,
)
from typing import (
    Any,
    ClassVar,
)

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    Request,
    Response,
)
from starlette.testclient import TestClient

from galaxy.webapps.galaxy.api.cbv import cbv


def test_cbv() -> None:
    router = APIRouter()

    def dependency() -> int:
        return 1

    @cbv(router)
    class CBV:
        x: int = Depends(dependency)
        cx: ClassVar[int] = 1
        cy: ClassVar[int]

        def __init__(self, z: int = Depends(dependency)):
            self.y = 1
            self.z = z

        @router.get("/", response_model=int)
        def f(self) -> int:
            return self.cx + self.x + self.y + self.z

        @router.get("/classvar", response_model=bool)
        def g(self) -> bool:
            return hasattr(self, "cy")

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response_1 = client.get("/")
    assert response_1.status_code == 200
    assert response_1.content == b"4"

    response_2 = client.get("/classvar")
    assert response_2.status_code == 200
    assert response_2.content == b"false"


def test_method_order_preserved() -> None:
    router = APIRouter()

    @cbv(router)
    class TestCBV:
        @router.get("/test")
        def get_test(self) -> int:
            return 1

        @router.get("/{item_id}")
        def get_item(self) -> int:  # Alphabetically before `get_test`
            return 2

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    assert client.get("/test").json() == 1
    assert client.get("/other").json() == 2


def test_multiple_decorators() -> None:
    app = FastAPI()
    router = APIRouter()

    @cbv(router)
    class RootHandler:
        @router.get("/items/?")
        @router.get("/items/{item_path:path}")
        @router.get("/database/{item_path:path}")
        def root(self, item_path: str | None = None, item_query: str | None = None) -> Any:
            if item_path:
                return {"item_path": item_path}
            if item_query:
                return {"item_query": item_query}
            return []

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    assert client.get("/items").json() == []
    assert client.get("/items/1").json() == {"item_path": "1"}
    assert client.get("/database/abc").json() == {"item_path": "abc"}


def test_cbv_rebuilds_direct_route_dependencies() -> None:
    """Exercise rebuilt handlers directly, without include_router rebuilding them again."""
    app = FastAPI()
    router = APIRouter(dependency_overrides_provider=app)
    events: list[str] = []

    async def dependency() -> AsyncIterator[int]:
        events.append("enter")
        try:
            yield 3
        finally:
            events.append("exit")

    @cbv(router)
    class View:
        value: int = Depends(dependency)

        @router.get("/direct")
        async def show(self) -> int:
            return self.value

    # This is also a structural regression check: ordinary CBVs need no nested router.
    from fastapi.routing import APIRoute

    assert len(router.routes) == 1
    assert isinstance(router.routes[0], APIRoute)
    app.router.routes.extend(router.routes)
    with TestClient(app) as client:
        assert client.get("/direct").json() == 3
        assert events == ["enter", "exit"]

        async def override() -> int:
            return 7

        app.dependency_overrides[dependency] = override
        assert client.get("/direct").json() == 7
        assert events == ["enter", "exit"]


def test_cbv_included_router_mutation() -> None:
    router = APIRouter()

    @router.get("/existing")
    async def existing() -> str:
        return "existing"

    app = FastAPI()
    app.include_router(router, prefix="/api")
    with TestClient(app) as client:
        assert client.get("/api/existing").json() == "existing"
        assert client.get("/api/new").status_code == 404

        @cbv(router)
        class View:
            @router.get("/new")
            async def show(self) -> str:
                return type(self).__name__

        assert client.get("/api/new").json() == "View"

        class Override:
            pass

        app.dependency_overrides[View] = Override
        assert client.get("/api/new").json() == "Override"

        @router.get("/later")
        async def later() -> str:
            return "later"

        assert client.get("/api/later").json() == "later"


def _legacy_cbv(router: APIRouter) -> Callable[[type[Any]], type[Any]]:
    """The previous inclusion behavior, for behavioral/OpenAPI comparisons."""
    import inspect

    from starlette.routing import (
        Route,
        WebSocketRoute,
    )

    from galaxy.webapps.galaxy.api.cbv import (
        _init_cbv,
        _update_cbv_route_endpoint_signature,
    )

    def decorate(cls: type[Any]) -> type[Any]:
        _init_cbv(cls)
        methods = {method for _, method in inspect.getmembers(cls, inspect.isfunction)}
        inner = APIRouter()
        for route in list(router.routes):
            if isinstance(route, (Route, WebSocketRoute)) and route.endpoint in methods:
                router.routes.remove(route)
                _update_cbv_route_endpoint_signature(cls, route)
                inner.routes.append(route)
        router.include_router(inner)
        return cls

    return decorate


def _build_compatibility_app(
    decorator: Callable[[APIRouter], Callable[[type[Any]], type[Any]]],
) -> tuple[FastAPI, FastAPI, list[str]]:
    from contextlib import asynccontextmanager

    from fastapi.responses import JSONResponse
    from fastapi.routing import APIRoute
    from pydantic import (
        BaseModel,
        Field,
    )

    from galaxy.webapps.base.api import build_route_name_index

    events: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        events.append("startup")
        yield
        events.append("shutdown")

    async def dependency() -> AsyncIterator[int]:
        events.append("dependency enter")
        try:
            yield 4
        finally:
            events.append("dependency exit")

    class Result(BaseModel):
        value: int = Field(alias="result")
        hidden: int = 10

    class WrappedRoute(APIRoute):
        def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
            handler = super().get_route_handler()

            async def wrapped(request: Request) -> Response:
                response = await handler(request)
                response.headers["x-wrapped"] = "yes"
                return response

            return wrapped

    router = APIRouter(
        lifespan=lifespan,
        route_class=WrappedRoute,
        tags=["router"],
        dependencies=[Depends(dependency)],
        responses={418: {"description": "teapot"}},
    )

    @router.get("/standalone", name="standalone")
    async def standalone() -> str:
        return "standalone"

    @decorator(router)
    class View:
        value: int = Depends(dependency)

        @router.get(
            "/fixed",
            name="fixed",
            response_model=Result,
            response_model_exclude={"hidden"},
            summary="Summary",
            description="Description",
            response_description="Result",
            tags=["endpoint"],
            operation_id="fixed_operation",
            deprecated=True,
            openapi_extra={"x-example": True},
            response_class=JSONResponse,
        )
        async def fixed(self) -> Result:
            return Result(result=self.value)

        @router.get("/items/{item_id:int}", name="item")
        async def item(self, item_id: int, request: Request) -> dict[str, int | str]:
            index = request.app.state.route_name_index
            return {
                "id": item_id,
                "value": self.value,
                "url": str(request.url_for("item", item_id=item_id)),
                "indexed": str(index["item"][0].url_path_for("item", item_id=item_id)),
            }

        @router.get("/same", name="same_get")
        async def get_same(self) -> str:
            return "get"

        @router.post("/same", name="same_post", status_code=201)
        async def post_same(self) -> str:
            return "post"

        @router.get("/hidden", include_in_schema=False)
        async def hidden(self) -> str:
            return "hidden"

        @router.get("/nested/slash/")
        async def slash(self) -> str:
            return "slash"

        @router.get("/{other}")
        async def catch_all(self, other: str) -> str:
            return other

    outer = APIRouter()
    outer.include_router(router, prefix="/v1", tags=["included"])
    app = FastAPI(root_path="/galaxy")
    app.include_router(outer, prefix="/api")
    app.state.route_name_index = build_route_name_index(app)
    app.dependency_overrides[dependency] = lambda: 9
    parent = FastAPI()
    parent.mount("/galaxy", app)
    return parent, app, events


def test_cbv_routing_and_openapi_compatibility() -> None:
    snapshots = []
    for decorator in (_legacy_cbv, cbv):
        parent, app, events = _build_compatibility_app(decorator)
        responses = []
        # The server runs only the outer lifespan; start the API's lifespan too,
        # just as Galaxy does when serving a prefixed app.
        with TestClient(app), TestClient(parent) as client:
            assert events == ["startup"]
            for method, path, status in [
                ("GET", "/fixed", 200),
                ("GET", "/items/42", 200),
                ("POST", "/items/42", 405),
                ("GET", "/same", 200),
                ("POST", "/same", 201),
                ("DELETE", "/same", 405),
                ("GET", "/standalone", 200),
                ("GET", "/hidden", 200),
                ("GET", "/nested/slash", 307),
                ("GET", "/nested/slash/", 200),
                ("GET", "/unknown", 200),
            ]:
                response = client.request(method, f"/galaxy/api/v1{path}", follow_redirects=False)
                assert response.status_code == status
                responses.append((response.status_code, response.content, dict(response.headers)))
            assert client.get("/galaxy/api/v1/fixed").json() == {"result": 9}
            assert client.get("/galaxy/api/v1/items/42").json() == {
                "id": 42,
                "value": 9,
                "url": "http://testserver/galaxy/api/v1/items/42",
                "indexed": "/api/v1/items/42",
            }
            assert app.url_path_for("fixed") == "/api/v1/fixed"
            assert client.get("/galaxy/api/v1/fixed").headers["x-wrapped"] == "yes"
            schema = app.openapi()
            assert "self" not in str(schema)
            assert "/api/v1/hidden" not in schema["paths"]
            # Use Galaxy's OpenAPI implementation as well as FastAPI's.
            from galaxy.webapps.openapi.utils import get_openapi

            galaxy_schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        assert events == ["startup", "shutdown"]
        snapshots.append((responses, schema, galaxy_schema))
    assert snapshots[0] == snapshots[1]


def test_cbv_galaxy_custom_routes_and_wsgi_fallback() -> None:
    from a2wsgi import WSGIMiddleware

    from galaxy.webapps.galaxy.api import (
        APIContentTypeRoute,
        FrameworkRouter,
    )

    class JsonRoute(APIContentTypeRoute):
        match_content_type = "application/json"

    class TextRoute(APIContentTypeRoute):
        match_content_type = "text/plain"

    snapshots = []
    for decorator in (_legacy_cbv, cbv):
        router = FrameworkRouter()

        @decorator(router)
        class View:
            @router.post("/content", route_class_override=JsonRoute)
            async def json_content(self) -> str:
                return "json"

            @router.post("/content", route_class_override=TextRoute)
            async def text_content(self) -> str:
                return "text"

            @router.get("/cors", allow_cors=True)
            async def cors(self) -> Response:
                return Response(b"cors")

        def legacy(environ: Any, start_response: Any) -> list[bytes]:
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [f"legacy:{environ['PATH_INFO']}".encode()]

        app = FastAPI()
        app.include_router(router, prefix="/api")
        # A full mount match can win over a prior partial API match.
        app.mount("/", WSGIMiddleware(legacy))  # type: ignore[arg-type]
        with TestClient(app) as client:
            responses = []
            for method, path, headers in [
                ("POST", "/api/content", {"content-type": "application/json"}),
                ("POST", "/api/content", {"content-type": "text/plain"}),
                ("POST", "/api/content", {"content-type": "image/png"}),
                ("POST", "/api/content", {}),
                ("GET", "/api/content", {}),
                ("GET", "/api/cors", {"origin": "https://example.org"}),
                ("OPTIONS", "/api/cors", {"origin": "https://example.org"}),
                ("GET", "/histories/example/export", {}),
                ("GET", "/api/content/", {}),
            ]:
                response = client.request(method, path, headers=headers)
                responses.append((response.status_code, response.content, dict(response.headers)))
            assert responses[0][1] == b'"json"'
            assert responses[1][1] == b'"text"'
            assert responses[2][1] == b"legacy:/api/content"
            assert responses[5][2]["access-control-allow-origin"] == "https://example.org"
            assert responses[7][1] == b"legacy:/histories/example/export"
            snapshots.append(responses)
    assert snapshots[0] == snapshots[1]


def test_cbv_websocket_fallback() -> None:
    from fastapi import WebSocket

    events: list[str] = []

    async def dependency() -> AsyncIterator[int]:
        events.append("enter")
        try:
            yield 7
        finally:
            events.append("exit")

    router = APIRouter()

    @cbv(router)
    class View:
        value: int = Depends(dependency)

        @router.websocket("/socket/{item_id}", name="socket")
        async def socket(self, websocket: WebSocket, item_id: str) -> None:
            await websocket.accept()
            await websocket.send_json({"value": self.value, "id": item_id})
            await websocket.close()

        @router.get("/http")
        async def http(self) -> int:
            return self.value

    app = FastAPI()
    app.include_router(router, prefix="/api")
    with TestClient(app) as client:
        with client.websocket_connect("/api/socket/example") as connection:
            assert connection.receive_json() == {"value": 7, "id": "example"}
        assert events == ["enter", "exit"]
        assert client.get("/api/http").json() == 7
        assert events == ["enter", "exit", "enter", "exit"]
    assert app.url_path_for("socket", item_id="example") == "/api/socket/example"


def test_cbv_custom_constructor_fallback() -> None:
    from fastapi.routing import (
        APIRoute,
        iter_route_contexts,
    )

    constructed: list[APIRoute] = []

    class StatefulRoute(APIRoute):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            constructed.append(self)

    router = APIRouter(route_class=StatefulRoute)

    @cbv(router)
    class View:
        @router.get("/stateful")
        async def show(self) -> str:
            return "stateful"

    assert len(constructed) == 1
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        assert client.get("/stateful").json() == "stateful"
    assert next(iter_route_contexts(router.routes)).original_route is constructed[0]


def test_cbv_streaming_fallback() -> None:
    from pydantic import BaseModel

    class Item(BaseModel):
        value: int

    router = APIRouter()

    @cbv(router)
    class View:
        @router.get("/stream")
        async def stream(self) -> AsyncIterator[Item]:
            yield Item(value=1)
            yield Item(value=2)

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/stream")
        assert response.status_code == 200
        assert response.text.splitlines() == ['{"value":1}', '{"value":2}']


def test_cbv_body_and_route_defaults_compatibility() -> None:
    from pydantic import (
        BaseModel,
        Field,
    )

    class Item(BaseModel):
        value: int = Field(alias="result")
        optional: str | None = None
        default: int = 5

    snapshots = []
    for decorator in (_legacy_cbv, cbv):
        router = APIRouter(
            prefix="/local",
            tags=["router"],
            strict_content_type=False,
            generate_unique_id_function=lambda route: f"custom_{route.name}",
        )

        @decorator(router)
        class View:
            @router.post(
                "/item",
                response_model=Item,
                response_model_by_alias=False,
                response_model_exclude_unset=True,
                response_model_exclude_defaults=True,
                response_model_exclude_none=True,
                response_model_include={"value", "optional", "default"},
            )
            async def create(self, payload: Item) -> Item:
                return payload

        app = FastAPI()
        app.include_router(router, prefix="/api")
        with TestClient(app) as client:
            # Preserve the existing CBV behavior of reapplying router defaults,
            # including its prefix, when registering the modified endpoints.
            response = client.post("/api/local/local/item", content=b'{"result": 3}')
            assert response.status_code == 200
            assert response.json() == {"value": 3}
            invalid = client.post("/api/local/local/item", content=b'{"result": "invalid"}')
            assert invalid.status_code == 422
            snapshots.append((response.content, invalid.content, app.openapi()))
    assert snapshots[0] == snapshots[1]
