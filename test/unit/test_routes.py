from galaxy.util.bunch import Bunch
from galaxy.web import url_for
from galaxy.web.framework.webapp import WebApplication
from galaxy.webapps.galaxy import buildapp as galaxy_buildapp


class TestWebapp( WebApplication ):

    def _instantiate_controller( self, type, app ):
        # Stub out all actual controllers - just want to test routes.
        return object()

    def assert_maps( self, url, method="GET", **parts ):
        map_result = self.mapper.match( url, environ={"REQUEST_METHOD": method } )
        for key, expected_value in parts.items():
            actual_value = map_result[ key ]
            if actual_value != expected_value:
                message = "Problem mapping route [%s], part %s expected value [%s] but obtained [%s]"
                raise AssertionError(message % ( url, key, expected_value, actual_value ) )


def test_galaxy_routes( ):
    test_config = Bunch( template_path="/tmp", template_cache="/tmp" )
    app = Bunch( config=test_config, security=object(), trace_logger=None )
    test_webapp = TestWebapp( app )

    galaxy_buildapp.populate_api_routes( test_webapp, app )

    assert_url_is( url_for( "api_key_retrieval" ), "/api/authenticate/baseauth" )

    # Test previously problematic tool ids with slashes.
    test_webapp.assert_maps(
        "/api/tools/testtoolshed.g2.bx.psu.edu/devteam/tool1",
        controller="tools",
        id="testtoolshed.g2.bx.psu.edu/devteam/tool1"
    )

    test_webapp.assert_maps(
        "/api/datatypes/sniffers",
        controller="datatypes",
        action="sniffers"
    )

    test_webapp.assert_maps(
        "/api/histories/123/contents/456",
        controller="history_contents",
        action="show"
    )

    test_webapp.assert_maps(
        "/api/histories/123/contents/456",
        method="PUT",
        controller="history_contents",
        action="update",
    )

    # Test differeniating datasets and datasets collections
    # in history contents.
    test_webapp.assert_maps(
        "/api/histories/123/contents/datasets/456",
        method="PUT",
        controller="history_contents",
        action="update",
        type="dataset"
    )

    test_webapp.assert_maps(
        "/api/histories/123/contents/dataset_collections/456",
        method="PUT",
        controller="history_contents",
        action="update",
        type="dataset_collection"
    )

    assert_url_is(
        url_for( "history_content", history_id="123", id="456" ),
        "/api/histories/123/contents/456"
    )

    assert_url_is(
        url_for( "history_content_typed", history_id="123", id="456", type="dataset" ),
        "/api/histories/123/contents/datasets/456"
    )

    test_webapp.assert_maps(
        "/api/dependency_resolvers",
        controller="tool_dependencies",
        action="index"
    )

    test_webapp.assert_maps(
        "/api/dependency_resolvers/dependency",
        controller="tool_dependencies",
        action="manager_dependency"
    )

    test_webapp.assert_maps(
        "/api/dependency_resolvers/0",
        controller="tool_dependencies",
        action="show"
    )

    test_webapp.assert_maps(
        "/api/dependency_resolvers/0/dependency",
        controller="tool_dependencies",
        action="resolver_dependency"
    )


def assert_url_is( actual, expected ):
    assert actual == expected, "Expected URL [%s] but obtained [%s]" % ( expected, actual )
