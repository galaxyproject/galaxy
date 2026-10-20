from fastapi import (
    APIRouter,
    FastAPI,
)

from galaxy.webapps.base.api import build_route_name_index


def test_index_holds_routes_of_included_routers():
    inner = APIRouter()
    outer = APIRouter()

    @inner.get("/api/histories/{history_id}/contents/{id}", name="history_content")
    def show(history_id: str, id: str):
        return id

    @outer.get("/api/version", name="version")
    def version():
        return 1

    outer.include_router(inner)
    app = FastAPI()
    app.include_router(outer)

    index = build_route_name_index(app)

    assert [route.url_path_for("version") for route in index["version"]] == ["/api/version"]
    (route,) = index["history_content"]
    assert route.url_path_for("history_content", history_id="h", id="i") == "/api/histories/h/contents/i"
    assert app.url_path_for("history_content", history_id="h", id="i") == "/api/histories/h/contents/i"
