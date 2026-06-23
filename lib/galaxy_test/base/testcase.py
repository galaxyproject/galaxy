import logging
from typing import (
    Any,
    Optional,
)

import pytest

from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.util.unittest import TestCase
from galaxy_test.base.env import (
    GalaxyTarget,
    setup_keep_outdir,
    target_url_parts,
)

log = logging.getLogger(__name__)


def host_port_and_url(test_driver: Optional[Any]) -> GalaxyTarget:
    host, port, url = target_url_parts()
    server_wrapper = test_driver and test_driver.server_wrappers and test_driver.server_wrappers[0]
    if server_wrapper:
        host = server_wrapper.host
        port = server_wrapper.port
        url = f"http://{host}:{port}{server_wrapper.prefix.rstrip('/')}/"
    return host, port, url


@pytest.mark.usefixtures("embedded_driver")
class FunctionalTestCase(TestCase):
    """Base class for tests targetting actual Galaxy servers.

    Subclass should override galaxy_driver_class if a Galaxy server
    needs to be launched to run the test, this base class assumes a
    server is already running.
    """

    galaxy_driver_class: Optional[type] = None
    host: str
    port: Optional[str]
    url: str
    keepOutdir: str
    test_data_resolver: TestDataResolver
    _test_driver: Optional[Any]

    def setUp(self) -> None:
        self.host, self.port, self.url = host_port_and_url(self._test_driver)
        self.test_data_resolver = TestDataResolver()
        self.keepOutdir = setup_keep_outdir()

    @classmethod
    def setUpClass(cls):
        """Configure and start Galaxy for a test."""
        pass

    @classmethod
    def tearDownClass(cls):
        """Shutdown Galaxy server and cleanup temp directory."""
        pass

    def get_filename(self, filename: str) -> str:
        # No longer used by tool tests - drop if isn't used else where.
        return self.test_data_resolver.get_filename(filename)
