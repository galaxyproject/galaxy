from routes import request_config

from galaxy.util.bunch import Bunch
from galaxy.web import url_for
from galaxy.webapps.base.webapp import WebApplication
from galaxy.webapps.galaxy import buildapp as galaxy_buildapp


class MockWebApplication(WebApplication):
    def _instantiate_controller(self, type, app):
        # Stub out all actual controllers - just want to test routes.
        return object()

    def assert_maps(self, url, method="GET", **parts):
        map_result = self.mapper.match(url, environ={"REQUEST_METHOD": method})
        for key, expected_value in parts.items():
            actual_value = map_result[key]
            assert (
                actual_value == expected_value
            ), f"Problem mapping route [{url}], part {key} expected value [{expected_value}] but obtained [{actual_value}]"


def test_galaxy_routes():
    test_config = Bunch(template_cache_path="/tmp")
    app = Bunch(config=test_config, security=object(), trace_logger=None, name="galaxy")
    test_webapp = MockWebApplication(app)

    galaxy_buildapp.populate_api_routes(test_webapp, app)
    config = request_config()
    config.host = "usegalaxy.org"
    config.protocol = "https"
    assert_url_is(url_for("api_key_retrieval", qualified=True), "https://usegalaxy.org/api/authenticate/baseauth")
    assert_url_is(url_for("/tool_runner/biomart", qualified=True), "https://usegalaxy.org/tool_runner/biomart")

    # Test previously problematic tool ids with slashes.
    test_webapp.assert_maps(
        "/api/tools/testtoolshed.g2.bx.psu.edu/devteam/tool1",
        controller="tools",
        id="testtoolshed.g2.bx.psu.edu/devteam/tool1",
    )

    test_webapp.assert_maps("/api/dependency_resolvers", controller="tool_dependencies", action="index")

    test_webapp.assert_maps(
        "/api/dependency_resolvers/dependency", controller="tool_dependencies", action="manager_dependency"
    )

    test_webapp.assert_maps("/api/dependency_resolvers/0", controller="tool_dependencies", action="show")

    test_webapp.assert_maps(
        "/api/dependency_resolvers/0/dependency", controller="tool_dependencies", action="resolver_dependency"
    )


def assert_url_is(actual, expected):
    assert actual == expected, f"Expected URL [{expected}] but obtained [{actual}]"
