from __future__ import print_function

import logging
import os
import unittest

from galaxy.tools.verify.test_data import TestDataResolver
from galaxy.web import security
from .driver_util import GalaxyTestDriver, setup_keep_outdir, target_url_parts

log = logging.getLogger(__name__)


class FunctionalTestCase(unittest.TestCase):

    def setUp(self):
        # Security helper
        self.security = security.SecurityHelper(id_secret='changethisinproductiontoo')
        self.history_id = os.environ.get('GALAXY_TEST_HISTORY_ID', None)
        self.host, self.port, self.url = target_url_parts()
        self.test_data_resolver = TestDataResolver()
        self.keepOutdir = setup_keep_outdir()

    @classmethod
    def setUpClass(cls):
        """Configure and start Galaxy for a test."""
        cls._test_driver = None

        if not os.environ.get("GALAXY_TEST_ENVIRONMENT_CONFIGURED"):
            cls._test_driver = GalaxyTestDriver()
            cls._test_driver.setup(config_object=cls)

    @classmethod
    def tearDownClass(cls):
        """Shutdown Galaxy server and cleanup temp directory."""
        if cls._test_driver:
            cls._test_driver.tear_down()

    def get_filename(self, filename):
        # No longer used by tool tests - drop if isn't used else where.
        return self.test_data_resolver.get_filename(filename)
