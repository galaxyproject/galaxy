from __future__ import print_function

import logging
import os
import unittest

from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy_test.base.env import setup_keep_outdir, target_url_parts

log = logging.getLogger(__name__)


class FunctionalTestCase(unittest.TestCase):
    """Base class for tests targetting actual Galaxy servers.

    Subclass should override galaxy_driver_class if a Galaxy server
    needs to be launched to run the test, this base class assumes a
    server is already running.
    """
    galaxy_driver_class = None

    def setUp(self):
        self.history_id = os.environ.get('GALAXY_TEST_HISTORY_ID', None)
        self.host, self.port, self.url = target_url_parts()
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

    def get_filename(self, filename):
        # No longer used by tool tests - drop if isn't used else where.
        return self.test_data_resolver.get_filename(filename)
