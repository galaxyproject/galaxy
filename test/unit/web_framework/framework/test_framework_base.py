import pytest
import webob
import webob.exc

from galaxy.web.framework.base import WebApplication
from galaxy.web.framework.decorators import expose


class MockWebApplication(WebApplication):
    def assert_maps(self, url, method="GET", **parts):
        map_result = self.mapper.match(url, environ={"REQUEST_METHOD": method})
        for key, expected_value in parts.items():
            actual_value = map_result[key]
            assert (
                actual_value == expected_value
            ), f"Problem mapping route [{url}], part {key} expected value [{expected_value}] but obtained [{actual_value}]"


def test_add_route():
    test_webapp = MockWebApplication()
    test_webapp.add_route("/authnz/", controller="authnz", action="index", provider=None)
    test_webapp.assert_maps("/authnz/", controller="authnz", action="index")


CLIENT_MATCH = {"controller": "root", "action": "client"}


class StubRequest:
    def __init__(self, environ):
        self.params = webob.Request(environ).params


class StubResponse:
    def send_redirect(self, url):
        raise AssertionError(f"Unexpected redirect to {url}")


class StubTransaction:
    def __init__(self, environ):
        self.request = StubRequest(environ)
        self.response = StubResponse()


class RootController:
    @expose
    def client(self, trans, **kwd):
        # route variables from a match that couldn't be resolved shouldn't leak through
        return f"client {kwd}" if kwd else "client"

    @expose
    def welcome(self, trans, **kwd):
        return "root.welcome"


class AdminController:
    @expose
    def index(self, trans, **kwd):
        return "admin.index"


class DatasetController:
    @expose
    def default(self, trans, **kwd):
        return "dataset.default"


def _client_fallback_webapp(client_match=CLIENT_MATCH):
    webapp = WebApplication()
    webapp.client_match = client_match
    webapp.add_ui_controller("root", RootController())
    # an API controller that could serve the client match, so only the API guards keep it from doing so
    webapp.add_api_controller("root", RootController())
    webapp.add_ui_controller("admin", AdminController())
    webapp.add_ui_controller("dataset", DatasetController())
    webapp.add_route("/api/{controller}/{action}")
    webapp.add_route("/{controller}/{action}/{id}")
    webapp.add_route("/{controller}/{action}", action="index")
    webapp.add_route("/{action}", controller="root", action="index")
    webapp.set_transaction_factory(StubTransaction)
    webapp.finalize_config()
    return webapp


def _handle(webapp, path):
    environ = webob.Request.blank(path).environ
    return webapp.handle_request("request-id", path, environ, None, body_renderer=lambda trans, body, *args: body)


@pytest.mark.parametrize(
    "path, expected",
    [
        # server handlers still win
        ("/", "client"),
        ("/welcome", "root.welcome"),
        ("/admin", "admin.index"),
        ("/dataset/display", "dataset.default"),
        # no route matches at all
        ("/histories/list", "client"),
        # a route matches, but there's no handler behind it
        ("/histories", "client"),
        ("/admin/users", "client"),
        ("/admin/users/123", "client"),
    ],
)
def test_unhandled_paths_fall_back_to_client(path, expected):
    assert _handle(_client_fallback_webapp(), path) == expected


@pytest.mark.parametrize("path", ["/api/nope", "/api/histories/list", "/api/root/nope"])
def test_unhandled_api_paths_still_404(path):
    with pytest.raises(webob.exc.HTTPNotFound):
        _handle(_client_fallback_webapp(), path)


@pytest.mark.parametrize("path", ["/histories", "/histories/list"])
def test_unhandled_paths_404_without_client_match(path):
    with pytest.raises(webob.exc.HTTPNotFound):
        _handle(_client_fallback_webapp(client_match=None), path)
