import pytest

from galaxy.web.framework.middleware.remoteuser import RemoteUser

REMOTE_USER = "alex@example.org"


def _status_for(path_info: str) -> str:
    statuses = []

    def app(environ, start_response):
        start_response("200 OK", [])
        return [b"ok"]

    def start_response(status, headers, exc_info=None):
        statuses.append(status)

    RemoteUser(app)({"PATH_INFO": path_info, "HTTP_REMOTE_USER": REMOTE_USER}, start_response)
    return statuses[0]


@pytest.mark.parametrize(
    "path_info",
    [
        "/user",
        "/user/information",
        "/user/api_key",
        "/user/credentials",
        "/user/external_ids",
        "/user/notifications",
        "/user/notifications/preferences",
        "/user/permissions",
    ],
)
def test_client_preference_pages_load_for_remote_users(path_info):
    assert _status_for(path_info) == "200 OK"


@pytest.mark.parametrize("path_info", ["/user/login", "/user/create", "/user/change_password", "/user/reset_password"])
def test_account_actions_stay_blocked_for_remote_users(path_info):
    assert _status_for(path_info).startswith("403")
