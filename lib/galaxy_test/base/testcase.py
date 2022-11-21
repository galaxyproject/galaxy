import logging
import os
from typing import (
    Optional,
    Generic,
    Type,
    TypeVar,
    TYPE_CHECKING,
)
from unittest import SkipTest

from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.util.unittest import TestCase
from galaxy_test.base.env import (
    setup_keep_outdir,
    target_url_parts,
)

if TYPE_CHECKING:
    from galaxy_test.driver.driver_util import (
        GalaxyTestDriver,
        TestDriver,
    )


log = logging.getLogger(__name__)


TestDriverType = TypeVar("TestDriverType", bound="TestDriver")


class FunctionalTestCase(TestCase, Generic[TestDriverType]):
    """Base class for tests targetting actual Galaxy servers.

    Subclass should override galaxy_driver_class if a Galaxy server
    needs to be launched to run the test, this base class assumes a
    server is already running.
    """

    galaxy_driver_class: Optional[Type[TestDriverType]] = None
    host: str
    port: Optional[str]
    url: str
    keepOutdir: str
    test_data_resolver: TestDataResolver
    _test_driver: Optional[TestDriverType]

    def setUp(self) -> None:
        self.host, self.port, self.url = target_url_parts()
        server_wrapper = (
            self._test_driver and self._test_driver.server_wrappers and self._test_driver.server_wrappers[0]
        )
        if server_wrapper:
            self.host = server_wrapper.host
            self.port = server_wrapper.port
            self.url = f"http://{self.host}:{self.port}{server_wrapper.prefix.rstrip('/')}/"
        self.test_data_resolver = TestDataResolver()
        self.keepOutdir = setup_keep_outdir()

    @classmethod
    def setUpClass(cls):
        """Configure and start Galaxy for a test."""
        cls._test_driver = None

        if cls.galaxy_driver_class is not None and not os.environ.get("GALAXY_TEST_ENVIRONMENT_CONFIGURED"):
            cls._test_driver = cls.galaxy_driver_class()
            cls._test_driver.setup(config_object=cls)

    @classmethod
    def tearDownClass(cls):
        """Shutdown Galaxy server and cleanup temp directory."""
        if cls._test_driver:
            cls._test_driver.tear_down()

    def get_filename(self, filename: str) -> str:
        # No longer used by tool tests - drop if isn't used else where.
        return self.test_data_resolver.get_filename(filename)

    def driver_or_skip_test_if_remote(self) -> TestDriverType:
        if self._test_driver is None:
            raise SkipTest("This test does not work with remote Galaxy instances.")
        return self._test_driver


class GalaxyFunctionalTestCase(FunctionalTestCase["GalaxyTestDriver"]):
    """A functional test case with Galaxy test drivers.

    The base class is also used by the tool shed test framework to driver tool
    shed test servers for instance.
    """
