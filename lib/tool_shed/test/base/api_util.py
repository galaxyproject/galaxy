import os
import re
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
)
from urllib.parse import urljoin

import requests
from typing_extensions import Literal

from galaxy_test.base.api_asserts import (
    assert_has_keys,
    assert_status_code_is,
    assert_status_code_is_ok,
)
from galaxy_test.base.api_util import baseauth_headers

DEFAULT_TOOL_SHED_BOOTSTRAP_ADMIN_API_KEY = "TEST1234"
DEFAULT_TOOL_SHED_USER_API_KEY = None


def get_admin_api_key() -> str:
    """Test admin API key to use for functional tests.

    This key should be configured as a admin API key and should be able
    to create additional users and keys.
    """
    for key in ["TOOL_SHED_CONFIG_BOOTSTRAP_ADMIN_API_KEY", "TOOL_SHED_CONFIG_OVERRIDE_BOOTSTRAP_ADMIN_API_KEY"]:
        value = os.environ.get(key, None)
        if value:
            return value
    return DEFAULT_TOOL_SHED_BOOTSTRAP_ADMIN_API_KEY


def get_user_api_key() -> Optional[str]:
    """Test user API key to use for functional tests.

    If set, this should drive API based testing - if not set an admin API key will
    be used to create a new user and API key for tests.
    """
    return os.environ.get("TOOL_SHED_TEST_USER_API_KEY", DEFAULT_TOOL_SHED_USER_API_KEY)


def decorate_method(method: Callable):
    @wraps(method)
    def wrapper(self: "ShedApiInteractor", route: str, **kwd) -> requests.Response:
        url = urljoin(self.url, f"api/{route}")
        kwd = self._append_headers(kwd)
        return method(url, **kwd)

    return wrapper


class ShedApiInteractor:
    url: str
    api_key: str

    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key

    def create_api_key(self, email: str, password: str) -> str:
        headers = baseauth_headers(email, password)
        url = urljoin(self.url, "api/authenticate/baseauth")
        auth_response = requests.get(url, headers=headers)
        assert_status_code_is(auth_response, 200)
        auth_dict = auth_response.json()
        assert_has_keys(auth_dict, "api_key")
        return auth_dict["api_key"]

    def _append_headers(self, kwd):
        if "admin" in kwd:
            key = get_admin_api_key()
        else:
            key = self.api_key

        headers = kwd.get("headers", {})
        headers["x-api-key"] = key
        kwd["headers"] = headers
        return kwd

    get = decorate_method(requests.get)
    post = decorate_method(requests.post)
    put = decorate_method(requests.put)
    delete = decorate_method(requests.delete)

    @property
    def api_version(self) -> Literal["v1", "v2"]:
        config = self.version()
        api_version = config.get("api_version", "v1")
        return api_version

    def version(self) -> Dict[str, Any]:
        response = self.get("version")
        response.raise_for_status()
        return response.json()

    @property
    def hg_url_base(self):
        return self.url


def create_user(admin_interactor: ShedApiInteractor, user_dict: Dict[str, Any], assert_ok=True) -> Dict[str, Any]:
    email = user_dict["email"]
    if "password" not in user_dict:
        user_dict["password"] = "testpass"
    if "remote_user_email" not in user_dict:
        user_dict["remote_user_email"] = email
    response = admin_interactor.post("users", json=user_dict)
    if assert_ok:
        assert_status_code_is_ok(response)
    return response.json()


def ensure_user_with_email(
    admin_api_interactor: ShedApiInteractor, email: str, password: Optional[str]
) -> Dict[str, Any]:
    all_users_response = admin_api_interactor.get("users")
    try:
        all_users_response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise Exception(
            f"Failed to verify user with email [{email}] exists - perhaps you're targeting the wrong ToolShed server or using an incorrect admin API key. HTTP error: {e}"
        )
    username = email_to_username(email)
    all_users = all_users_response.json()
    try:
        test_user = [user for user in all_users if user["username"] == username][0]
    except IndexError:
        request = {"email": email, "username": username, "password": password}
        test_user = create_user(admin_api_interactor, request, assert_ok=False)
    return test_user


def email_to_username(email: str) -> str:
    """Pattern used for test user generation - does not use the API."""
    return re.sub(r"[^a-z-\d]", "--", email.lower())
