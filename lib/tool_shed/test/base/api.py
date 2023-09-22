import os
import re
from typing import (
    Any,
    Dict,
    Optional,
)
from urllib.parse import urljoin

import pytest
import requests

from galaxy.tool_util.verify.interactor import GalaxyInteractorApi
from galaxy_test.base import api_asserts
from galaxy_test.base.api_util import (
    baseauth_headers,
    get_admin_api_key as get_galaxy_admin_api_key,
    get_user_api_key as get_galaxy_user_key,
    TEST_USER,
)
from galaxy_test.base.uses_shed_api import UsesShedApi
from galaxy_test.driver.testcase import DrivenFunctionalTestCase
from . import driver
from .api_util import (
    get_admin_api_key,
    get_user_api_key,
    ShedApiInteractor,
)
from .populators import ToolShedPopulator


class ShedBaseTestCase(DrivenFunctionalTestCase):
    _populator: Optional[ToolShedPopulator] = None

    @property
    def populator(self) -> ToolShedPopulator:
        if self._populator is None:
            self._populator = ToolShedPopulator(self.admin_api_interactor, self.api_interactor)
        return self._populator

    @property
    def admin_api_interactor(self) -> ShedApiInteractor:
        return ShedApiInteractor(self.url, get_admin_api_key())

    @property
    def api_interactor(self) -> ShedApiInteractor:
        user_api_key = get_user_api_key()
        if user_api_key is None:
            email = TEST_USER
            password = "testpassword"
            ensure_user_with_email(self.admin_api_interactor, email, password)
            user_api_key = self._api_key(email, password)
        return ShedApiInteractor(self.url, user_api_key)

    def _api_key(self, email: str, password: str) -> str:
        headers = baseauth_headers(email, password)
        url = urljoin(self.url, "api/authenticate/baseauth")
        auth_response = requests.get(url, headers=headers)
        api_asserts.assert_status_code_is(auth_response, 200)
        auth_dict = auth_response.json()
        api_asserts.assert_has_keys(auth_dict, "api_key")
        return auth_dict["api_key"]

    def setUp(self):
        host = os.environ.get("TOOL_SHED_TEST_HOST")
        assert host
        self.host = host
        self.port = os.environ.get("TOOL_SHED_TEST_PORT")
        self.url = f"http://{self.host}:{self.port}"
        self.galaxy_host = os.environ.get("GALAXY_TEST_HOST")
        self.galaxy_port = os.environ.get("GALAXY_TEST_PORT")
        self.galaxy_url = f"http://{self.galaxy_host}:{self.galaxy_port}"

    __test__ = True
    galaxy_driver_class = driver.ToolShedTestDriver

    @classmethod
    def setUpClass(cls):
        """Configure and start Galaxy for a test."""
        pass

    @classmethod
    def tearDownClass(cls):
        """Shutdown Galaxy server and cleanup temp directory."""
        pass

    @pytest.fixture(autouse=True)
    def _get_driver(self, tool_shed_test_driver):
        self._test_driver = tool_shed_test_driver


def ensure_user_with_email(admin_api_interactor: ShedApiInteractor, email: str, password: Optional[str]):
    all_users_response = admin_api_interactor.get("users")
    try:
        all_users_response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise Exception(
            f"Failed to verify user with email [{email}] exists - perhaps you're targetting the wrong Galaxy server or using an incorrect admin API key. HTTP error: {e}"
        )
    username = email_to_username(email)
    all_users = all_users_response.json()
    try:
        test_user = [user for user in all_users if user["username"] == username][0]
    except IndexError:
        password = password or "testpass"
        data = dict(
            remote_user_email=email,
            email=email,
            password=password,
            username=username,
        )
        test_user = admin_api_interactor.post("users", json=data).json()
    return test_user


def email_to_username(email: str) -> str:
    """Pattern used for test user generation - does not use the API."""
    return re.sub(r"[^a-z-\d]", "--", email.lower())


class ShedGalaxyInteractorApi(GalaxyInteractorApi):
    def __init__(self, galaxy_url: str):
        interactor_kwds: Dict[str, Any] = {}
        interactor_kwds["galaxy_url"] = galaxy_url
        interactor_kwds["master_api_key"] = get_galaxy_admin_api_key()
        interactor_kwds["api_key"] = get_galaxy_user_key()
        super().__init__(**interactor_kwds)


class ShedApiTestCase(ShedBaseTestCase, UsesShedApi):
    _galaxy_interactor: Optional[GalaxyInteractorApi] = None

    @property
    def galaxy_interactor(self) -> GalaxyInteractorApi:
        if self._galaxy_interactor is None:
            self._galaxy_interactor = ShedGalaxyInteractorApi(self.galaxy_url)
        return self._galaxy_interactor
