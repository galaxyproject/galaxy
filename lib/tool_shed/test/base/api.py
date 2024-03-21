import os
from functools import wraps
from typing import (
    Any,
    Dict,
    Optional,
)

import pytest

from galaxy.tool_util.verify.interactor import GalaxyInteractorApi
from galaxy_test.base.api_util import (
    get_admin_api_key as get_galaxy_admin_api_key,
    get_user_api_key as get_galaxy_user_key,
    TEST_USER,
)
from galaxy_test.base.uses_shed_api import UsesShedApi
from galaxy_test.driver.testcase import DrivenFunctionalTestCase
from . import driver
from .api_util import (
    ensure_user_with_email,
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
            self._populator = self._get_populator(self.api_interactor)
        return self._populator

    @property
    def admin_api_interactor(self) -> ShedApiInteractor:
        return ShedApiInteractor(self.url, get_admin_api_key())

    def _api_interactor_for_key(self, key: str) -> ShedApiInteractor:
        return self._api_interactor(key)

    def populator_for_key(self, key: str) -> ToolShedPopulator:
        return self._get_populator(self._api_interactor_for_key(key))

    @property
    def api_interactor(self) -> ShedApiInteractor:
        user_api_key = get_user_api_key()
        if user_api_key is None:
            email = TEST_USER
            password = "testpassword"
            ensure_user_with_email(self.admin_api_interactor, email, password)
            user_api_key = self.admin_api_interactor.create_api_key(email, password)
        return self._api_interactor_for_key(user_api_key)

    def _api_interactor_by_credentials(self, email: str, password: str) -> ShedApiInteractor:
        ensure_user_with_email(self.admin_api_interactor, email, password)
        user_api_key = self.admin_api_interactor.create_api_key(email, password)
        return self._api_interactor(user_api_key)

    def _api_interactor(self, api_key: str) -> ShedApiInteractor:
        return ShedApiInteractor(self.url, api_key)

    def _get_populator(self, user_api_interactor) -> ToolShedPopulator:
        return ToolShedPopulator(self.admin_api_interactor, user_api_interactor)

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
    def _get_driver(self, embedded_driver):
        self._test_driver = embedded_driver


class ShedGalaxyInteractorApi(GalaxyInteractorApi):
    def __init__(self, galaxy_url: str):
        interactor_kwds: Dict[str, Any] = {}
        interactor_kwds["galaxy_url"] = galaxy_url
        interactor_kwds["master_api_key"] = get_galaxy_admin_api_key()
        interactor_kwds["api_key"] = get_galaxy_user_key()
        super().__init__(**interactor_kwds)


def make_skip_if_api_version_wrapper(version):
    def wrapper(method):
        @wraps(method)
        def wrapped_method(api_test_case, *args, **kwd):
            interactor: ShedApiInteractor = api_test_case.api_interactor
            api_version = interactor.api_version
            if api_version == version:
                raise pytest.skip(f"{version} tool shed API found, skipping test")
            return method(api_test_case, *args, **kwd)

        return wrapped_method

    return wrapper


skip_if_api_v1 = make_skip_if_api_version_wrapper("v1")
skip_if_api_v2 = make_skip_if_api_version_wrapper("v2")


class ShedApiTestCase(ShedBaseTestCase, UsesShedApi):
    _galaxy_interactor: Optional[GalaxyInteractorApi] = None

    @property
    def galaxy_interactor(self) -> GalaxyInteractorApi:
        if self._galaxy_interactor is None:
            self._galaxy_interactor = ShedGalaxyInteractorApi(self.galaxy_url)
        return self._galaxy_interactor
