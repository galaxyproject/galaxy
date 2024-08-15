from urllib.parse import urljoin

from requests import get

from galaxy_test.base.api_util import baseauth_headers
from galaxy_test.base.decorators import requires_new_user
from galaxy_test.base.populators import skip_without_tool
from ._framework import ApiTestCase

TEST_USER_EMAIL = "auth_user_test@bx.psu.edu"
TEST_USER_PASSWORD = "testpassword1"


class TestAuthenticateApi(ApiTestCase):
    @requires_new_user
    def test_auth(self):
        self._setup_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        baseauth_url = self._api_url("authenticate/baseauth", use_key=False)
        headers = baseauth_headers(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        auth_response = get(baseauth_url, headers=headers)
        self._assert_status_code_is(auth_response, 200)
        auth_dict = auth_response.json()
        self._assert_has_keys(auth_dict, "api_key")

        # Verify key...
        random_api_url = self._api_url("users", use_key=False)
        random_api_response = get(random_api_url, params=dict(key=auth_dict["api_key"]))
        self._assert_status_code_is(random_api_response, 200)

    @skip_without_tool("test_data_source")
    def test_tool_runner_session_cookie_handling(self):
        response = get(self.url)
        tool_runner_session_cookie = response.cookies["galaxytoolrunnersession"]
        galaxy_session_cookie = response.cookies["galaxysession"]
        assert tool_runner_session_cookie != galaxy_session_cookie
        root_response = get(self.url, cookies={"galaxytoolrunnersession": tool_runner_session_cookie})
        root_response.raise_for_status()
        # Browser will only send cookie to /tool_runner path, but let's make sure it isn't accepted.
        # Galaxy responds with a new session and sessioncookie in that case.
        # (We might want to redirect to the login page instead if require_login is set?)
        assert root_response.cookies["galaxysession"] != galaxy_session_cookie
        tool_runner_response = get(
            urljoin(self.url, "tool_runner?tool_id=test_data_source"),
            cookies={"galaxytoolrunnersession": tool_runner_session_cookie},
        )
        tool_runner_response.raise_for_status()
        # Verify that we're not returning the sessioncookie
        assert "galaxysession" not in tool_runner_response.cookies
        # Make sure history for original session received job
        current_history_json_response = get(
            urljoin(self.url, "history/current_history_json"), cookies={"galaxysession": galaxy_session_cookie}
        )
        current_history_json_response.raise_for_status()
        current_history = current_history_json_response.json()
        assert current_history["contents_active"]["active"] == 1

    def test_anon_history_creation(self):
        # First request:
        # We don't create any histories, just return a session cookie
        response = get(self.url)
        cookie = {"galaxysession": response.cookies["galaxysession"]}
        # Check that we don't have any histories (API doesn't auto-create new histories)
        histories_response = get(
            urljoin(
                self.url,
                "api/histories",
            )
        )
        assert not histories_response.json()
        # Second request, we know client follows conventions by including cookies,
        # default history is created.
        get(self.url, cookies=cookie)
        second_histories_response = get(
            urljoin(self.url, "history/current_history_json"),
            cookies=cookie,
        )
        assert second_histories_response.json()
