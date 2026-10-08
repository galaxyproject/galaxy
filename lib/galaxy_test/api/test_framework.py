# This file doesn't test any API in particular but is meant to functionally
# test the API framework itself.
from requests import post

from galaxy_test.base.decorators import requires_admin
from ._framework import ApiTestCase


class TestApiFramework(ApiTestCase):
    def test_default_xframe_options(self):
        get_response = self._get("licenses")
        assert get_response.headers["x-frame-options"] == "SAMEORIGIN"

    def test_xframe_options_on_non_embed_published(self):
        get_response = self._get("/published/page")
        # Pages served through the WSGI app currently get this from both the WSGI and FastAPI layers
        assert "SAMEORIGIN" in get_response.headers["x-frame-options"]

    def test_xframe_options_skipped_for_embed(self):
        get_response = self._get("/published/page", data={"embed": "true"})
        assert "x-frame-options" not in get_response.headers

    def test_client_paths_serve_the_client_app(self):
        # "/" and "/histories" match the legacy /{action} route, "/admin/users" matches a real
        # controller and "/datasets/..." matches the dataset controller's routes, but none of them
        # have a server handler, so they should still get the client.
        for path in (
            "/",
            "/histories",
            "/histories/list",
            "/admin/users",
            "/datasets/list",
            "/datasets/f2db41e1fa331b3e",
            "/datasets/f2db41e1fa331b3e/details",
        ):
            response = self._get(path)
            self._assert_status_code_is(response, 200)
            assert "text/html" in response.headers["content-type"]
            assert '<div id="app">' in response.text, f"{path} did not serve the client app"

    def test_multipart_empty_boundary(self):
        # /api/tools POST is still served by the legacy WSGI app.
        response = post(
            self._api_url("tools"),
            data=b"x",
            headers={"Content-Type": "multipart/form-data; boundary="},
        )
        self._assert_status_code_is(response, 400)
        assert "Invalid boundary" in response.text

    # Next several tests test the API's run_as functionality.
    def test_user_cannont_run_as(self):
        run_as_user = self._setup_user("for_run_as@bx.psu.edu")
        post_data = dict(name="TestHistory1")
        # Normal user cannot run_as...
        create_response = self._post(
            "histories",
            data=post_data,
            headers={"run-as": run_as_user["id"]},
        )
        self._assert_status_code_is(create_response, 403)

    @requires_admin
    def test_run_as_invalid_user(self):
        post_data = dict(name="TestHistory1")
        # admin user can run_as, but this user doesn't exist, expect 400.
        create_response = self._post(
            "histories",
            data=post_data,
            headers={"run-as": "another_user"},
            admin=True,
        )
        self._assert_status_code_is(create_response, 400)

    @requires_admin
    def test_run_as_valid_user(self):
        run_as_user = self._setup_user("for_run_as@bx.psu.edu")
        post_data = dict(name="TestHistory1")
        # Use run_as with admin user and for another user just created, this
        # should work.
        create_response = self._post(
            "histories",
            data=post_data,
            headers={"run-as": run_as_user["id"]},
            admin=True,
        )
        self._assert_status_code_is(create_response, 200)
