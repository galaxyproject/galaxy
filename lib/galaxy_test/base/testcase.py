import logging
from typing import (
    Any,
    Optional,
)

import pytest

from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.util.unittest import TestCase
from galaxy_test.base.env import (
    setup_keep_outdir,
    target_url_parts,
)

log = logging.getLogger(__name__)


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
        pass

    @classmethod
    def tearDownClass(cls):
        """Shutdown Galaxy server and cleanup temp directory."""
        pass

    def get_filename(self, filename: str) -> str:
        # No longer used by tool tests - drop if isn't used else where.
        return self.test_data_resolver.get_filename(filename)
