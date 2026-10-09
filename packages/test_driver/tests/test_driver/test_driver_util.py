from unittest.mock import Mock

from fastapi import FastAPI
from starlette.routing import Mount

from galaxy.webapps.galaxy.fast_app import include_tus
from galaxy_test.driver import driver_util
from galaxy_test.driver.driver_util import attempt_ports


def test_attempt_ports():
    port = int(attempt_ports())
    assert port >= 8000 and port <= 10000


def _gx_app(new_file_path: str) -> Mock:
    # Spell out every setting caching_fast_app_factory reads: an unset Mock attribute is
    # a truthy Mock, which sends the factory down the uncached path.
    return Mock(
        config=Mock(
            galaxy_url_prefix="/",
            enable_mcp_server=False,
            use_access_logging_middleware=False,
            tus_upload_store=None,
            tus_upload_store_job_files=None,
            new_file_path=new_file_path,
            maximum_upload_file_size=1073741824,
        )
    )


async def _noop_asgi_app(scope, receive, send) -> None:
    """Stands in for the WSGI handler mounted at the root by initialize_fast_app."""


def _app_with_tus(new_file_path: str) -> FastAPI:
    app = FastAPI()
    app.router.routes.append(Mount("/", app=_noop_asgi_app))
    include_tus(app, _gx_app(new_file_path))
    return app


def _tus_entries(app: FastAPI) -> list:
    return [route for route in app.router.routes if driver_util._is_tus_route(route)]


def _bound_upload_dirs(app: FastAPI) -> set[str]:
    """The files_dir each TUS route handler closed over when it was built."""
    dirs = set()
    for entry in _tus_entries(app):
        for route in entry.original_router.routes:
            for cell in route.endpoint.__closure__ or ():
                options = cell.cell_contents
                if hasattr(options, "files_dir"):
                    dirs.add(options.files_dir)
    return dirs


def test_tus_routes_are_recognized():
    # FastAPI may store an included router as one entry carrying no path of its own, so
    # matching on route.path alone finds nothing.
    assert _tus_entries(_app_with_tus("/tmp/first"))


def test_rebinding_tus_routes_repoints_the_upload_store():
    app = _app_with_tus("/tmp/first")
    lifespan_context = app.router.lifespan_context
    assert _bound_upload_dirs(app) == {"/tmp/first"}

    driver_util._rebind_tus_routes(app, _gx_app("/tmp/second"), lifespan_context)

    assert _bound_upload_dirs(app) == {"/tmp/second"}


def test_repeated_rebinding_does_not_accumulate_routes():
    app = _app_with_tus("/tmp/first")
    lifespan_context = app.router.lifespan_context
    route_count = len(app.router.routes)

    for launch in range(5):
        driver_util._rebind_tus_routes(app, _gx_app(f"/tmp/{launch}"), lifespan_context)

    assert len(app.router.routes) == route_count
    assert isinstance(app.router.routes[-1], Mount), "root WSGI mount must stay last"


def test_caching_fast_app_factory_reuses_and_rebinds_across_launches(monkeypatch):
    driver_util._test_fast_app_slot.cache_clear()
    init_calls = []
    rebind_calls = []

    def fake_init(_gx_wsgi_webapp, gx_app):
        init_calls.append(gx_app.config.new_file_path)
        return Mock(router=Mock(lifespan_context="lifespan"))

    monkeypatch.setattr(driver_util, "init_galaxy_fast_app", fake_init)
    monkeypatch.setattr(driver_util, "_rebind_fast_app_for_launch", lambda *a, **kw: rebind_calls.append(a))

    first = driver_util.caching_fast_app_factory(object(), _gx_app("/tmp/first"))
    second = driver_util.caching_fast_app_factory(object(), _gx_app("/tmp/second"))

    # Every test class gets its own temp upload store, so launches differing only in that
    # path must still reuse the cached app.
    assert first is second
    assert init_calls == ["/tmp/first"]
    assert len(rebind_calls) == 1


def test_caching_fast_app_factory_does_not_cache_when_topology_differs(monkeypatch):
    driver_util._test_fast_app_slot.cache_clear()
    monkeypatch.setattr(driver_util, "init_galaxy_fast_app", lambda *a: Mock(router=Mock()))

    gx_app = _gx_app("/tmp/first")
    gx_app.config.galaxy_url_prefix = "/galaxy"
    driver_util.caching_fast_app_factory(object(), gx_app)

    assert driver_util._test_fast_app_slot().get("app") is None
