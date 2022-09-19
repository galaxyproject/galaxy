import os
from functools import wraps
from typing import (
    Callable,
    Optional,
)
from urllib.parse import urljoin

import requests

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
