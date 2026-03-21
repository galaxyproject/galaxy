import os
from contextlib import contextmanager
from typing import (
    Any,
    Optional,
    TYPE_CHECKING,
)
from urllib.parse import (
    urlencode,
    urljoin,
)

import pytest
import requests
from typing_extensions import Protocol

from galaxy.util.properties import get_from_env
from .api_asserts import (
    assert_error_code_is,
    assert_has_keys,
    assert_not_has_keys,
    assert_status_code_is,
    assert_status_code_is_ok,
)
from .api_util import (
    ADMIN_TEST_USER,
    get_admin_api_key,
    get_user_api_key,
    OTHER_USER,
    TEST_USER,
)
from .interactor import TestCaseGalaxyInteractor as BaseInteractor

if TYPE_CHECKING:
    from requests import Response

CONFIG_PREFIXES = ["GALAXY_TEST_CONFIG_", "GALAXY_CONFIG_OVERRIDE_", "GALAXY_CONFIG_"]
CELERY_BROKER = get_from_env("CELERY_BROKER", CONFIG_PREFIXES, "memory://")
CELERY_BACKEND = get_from_env("CELERY_BACKEND", CONFIG_PREFIXES, "rpc://localhost")

DEFAULT_CELERY_CONFIG = {
    "broker_url": CELERY_BROKER,
    "result_backend": CELERY_BACKEND,
}


@pytest.fixture(scope="session")
def celery_config():
    return DEFAULT_CELERY_CONFIG


class UsesCeleryTasks:
    @classmethod
    def handle_galaxy_config_kwds(cls, config: dict[str, Any]) -> None:
        config["enable_celery_tasks"] = True
        config["metadata_strategy"] = f'{config.get("metadata_strategy", "directory")}_celery'
        celery_conf: dict[str, Any] = config.get("celery_conf", {})
        celery_conf.update(DEFAULT_CELERY_CONFIG)
        config["celery_conf"] = celery_conf

    @pytest.fixture(autouse=True, scope="session")
    def _request_celery_app(self, celery_session_app, celery_config):
        try:
            self._celery_app = celery_session_app
            yield
        finally:
            if os.environ.get("GALAXY_TEST_EXTERNAL") is None:
                from galaxy.celery import celery_app

                celery_app.fork_pool.stop()
                celery_app.fork_pool.join(timeout=5)

    @pytest.fixture(autouse=True, scope="session")
    def _request_celery_worker(self, celery_session_worker, celery_config, celery_worker_parameters):
        self._celery_worker = celery_session_worker

    @pytest.fixture(scope="session", autouse=True)
    def celery_worker_parameters(self):
        return {
            "queues": ("galaxy.internal", "galaxy.external"),
        }

    @pytest.fixture(scope="session")
    def celery_parameters(self):
        return {
            "task_create_missing_queues": True,
            "task_default_queue": "galaxy.internal",
        }


class HasAnonymousGalaxyInteractor(Protocol):
    @property
    def anonymous_galaxy_interactor(self) -> "ApiTestInteractor":
        """Return an optionally anonymous galaxy interactor."""


class UsesApiTestCaseMixin:
    url: str
    _galaxy_interactor: Optional["ApiTestInteractor"] = None

    def tearDown(self):
        if os.environ.get("GALAXY_TEST_EXTERNAL") is None:
            # Only kill running jobs after test for managed test instances.
            # Use low-level methods to bypass aiocop blocking-I/O checks —
            # tearDown cleanup should not fail the test for server-side
            # blocking events.
            response = self.galaxy_interactor._get("jobs?state=running")
            if response.ok:
                for job in response.json():
                    self.galaxy_interactor._delete(f"jobs/{job['id']}")

    def _api_url(self, path, params=None, use_key=None, use_admin_key=None):
        if not params:
            params = {}
        url = urljoin(self.url, f"api/{path}")
        if use_key:
            params["key"] = self.galaxy_interactor.api_key
        if use_admin_key:
            params["key"] = self.galaxy_interactor.master_api_key
        if query := urlencode(params):
            url = f"{url}?{query}"
        return url

    def _setup_interactor(self):
        self.user_api_key = get_user_api_key()
        self.master_api_key = get_admin_api_key()
        self._galaxy_interactor = self._get_interactor()

    @property
    def anonymous_galaxy_interactor(self) -> "ApiTestInteractor":
        """Return an optionally anonymous galaxy interactor.

        Lighter requirements for use with API requests that may not required an API key.
        """
        return self.galaxy_interactor

    @property
    def galaxy_interactor(self) -> "ApiTestInteractor":
        assert self._galaxy_interactor is not None
        return self._galaxy_interactor

    def _get_interactor(self, api_key=None, allow_anonymous=False) -> "ApiTestInteractor":
        if allow_anonymous and api_key is None:
            return AnonymousGalaxyInteractor(self)
        else:
            return ApiTestInteractor(self, api_key=api_key)

    def _setup_user(self, email, password=None):
        return self.galaxy_interactor.ensure_user_with_email(email, password=password)

    def _setup_user_get_key(self, email, password=None):
        user = self._setup_user(email, password)
        return user, self._post(f"users/{user['id']}/api_key", admin=True).json()

    @contextmanager
    def _different_user(self, email: Optional[str] = None, anon=False):
        """Use in test cases to switch get/post operations to act as new user

        ..code-block:: python

            with self._different_user("other_user@bx.psu.edu"):
                self._get("histories")  # Gets other_user@bx.psu.edu histories.

        """
        original_api_key = self.user_api_key
        original_interactor_key = self.galaxy_interactor.api_key
        original_cookies = self.galaxy_interactor.cookies
        if anon:
            cookies = requests.get(self.url).cookies
            self.galaxy_interactor.cookies = cookies
            new_key = None
        else:
            email = OTHER_USER if email is None else email
            _, new_key = self._setup_user_get_key(email)
        try:
            self.user_api_key = new_key
            self.galaxy_interactor.api_key = new_key
            yield
        finally:
            self.user_api_key = original_api_key
            self.galaxy_interactor.api_key = original_interactor_key
            self.galaxy_interactor.cookies = original_cookies

    def _get_current_history_id(self) -> str:
        """Return the current session's history ID (works for anonymous users)."""
        return self._get(urljoin(self.url, "history/current_history_json")).json()["id"]

    def _get(self, *args, **kwds):
        return self.galaxy_interactor.get(*args, **kwds)

    def _head(self, *args, **kwds):
        return self.galaxy_interactor.head(*args, **kwds)

    def _post(self, *args, **kwds):
        return self.galaxy_interactor.post(*args, **kwds)

    def _options(self, *args, **kwds):
        return self.galaxy_interactor.options(*args, **kwds)

    def _delete(self, *args, **kwds):
        return self.galaxy_interactor.delete(*args, **kwds)

    def _put(self, *args, **kwds):
        return self.galaxy_interactor.put(*args, **kwds)

    def _patch(self, *args, **kwds):
        return self.galaxy_interactor.patch(*args, **kwds)

    def _assert_status_code_is_ok(self, response):
        assert_status_code_is_ok(response)

    def _assert_status_code_is(self, response: "Response", expected_status_code: int) -> None:
        assert_status_code_is(response, expected_status_code)

    def _assert_has_keys(self, response, *keys):
        assert_has_keys(response, *keys)

    def _assert_not_has_keys(self, response, *keys):
        assert_not_has_keys(response, *keys)

    def _assert_error_code_is(self, response, error_code):
        assert_error_code_is(response, error_code)

    def _random_key(self):  # Used for invalid request testing...
        return "1234567890123456"

    _assert_has_key = _assert_has_keys


AIOCOP_ENABLED = os.environ.get("GALAXY_TEST_AIOCOP", "").lower() in ("1", "true", "yes")
# Matches aiocop's THRESHOLD_HIGH — high-severity events (socket.connect,
# subprocess, etc.) fail the request; lower-severity stat-like calls are
# logged but not treated as test failures.
AIOCOP_FAIL_SEVERITY = 50


def _check_aiocop_violations(response: "Response") -> None:
    """Fail the test if the server reported a high-severity aiocop violation.

    When the Galaxy test server has ``GALAXY_TEST_AIOCOP=1`` set, each
    response includes an ``X-Aiocop-Violations`` header summarizing any
    blocking-I/O events caught by the aiocop audit hook during that
    request.  See ``galaxy.web.framework.middleware.aiocop_integration``.
    """
    header = response.headers.get("x-aiocop-violations")
    if not header:
        return
    fields = dict(part.split("=", 1) for part in header.split(";") if "=" in part)
    try:
        severity = int(fields.get("severity", "0"))
    except ValueError:
        severity = 0
    if severity >= AIOCOP_FAIL_SEVERITY:
        raise AssertionError(
            f"aiocop detected high-severity blocking I/O (severity={severity}, "
            f"count={fields.get('count', '?')}, first={fields.get('first', '?')}) "
            f"during {response.request.method} {response.request.path_url}"
        )


class ApiTestInteractor(BaseInteractor):
    """Specialized variant of the API interactor (originally developed for
    tool functional tests) for testing the API generally.
    """

    def __init__(self, test_case, api_key=None):
        self.cookies = None
        admin = getattr(test_case, "require_admin_user", False)
        test_user = TEST_USER if not admin else ADMIN_TEST_USER
        super().__init__(test_case, test_user=test_user, api_key=api_key)

    # This variant the lower level get and post methods are meant to be used
    # directly to test API - instead of relying on higher-level constructs for
    # specific pieces of the API (the way it is done with the variant for tool)
    # testing.
    def _maybe_check_aiocop(self, response: "Response") -> "Response":
        if AIOCOP_ENABLED:
            _check_aiocop_violations(response)
        return response

    def get(self, *args, **kwds):
        return self._maybe_check_aiocop(self._get(*args, **kwds))

    def head(self, *args, **kwds):
        return self._maybe_check_aiocop(self._head(*args, **kwds))

    def post(self, *args, **kwds):
        return self._maybe_check_aiocop(self._post(*args, **kwds))

    def options(self, *args, **kwds):
        return self._maybe_check_aiocop(self._options(*args, **kwds))

    def delete(self, *args, **kwds):
        return self._maybe_check_aiocop(self._delete(*args, **kwds))

    def patch(self, *args, **kwds):
        return self._maybe_check_aiocop(self._patch(*args, **kwds))

    def put(self, *args, **kwds):
        return self._maybe_check_aiocop(self._put(*args, **kwds))


class AnonymousGalaxyInteractor(ApiTestInteractor):
    def __init__(self, test_case):
        super().__init__(test_case)

    def _get_user_key(
        self, user_key: Optional[str], admin_key: Optional[str], test_user: Optional[str] = None
    ) -> Optional[str]:
        return None
