# This file doesn't test any API in particular but is meant to functionally
# test the API framework itself.
from ._framework import ApiTestCase


class ApiFrameworkTestCase(ApiTestCase):
    def test_default_xframe_options(self):
        get_response = self._get("licenses")
        assert get_response.headers["x-frame-options"] == "SAMEORIGIN"

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
