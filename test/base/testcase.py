from __future__ import print_function

import logging
import os
import time
import unittest

from galaxy.tools.verify.test_data import TestDataResolver
from galaxy.web import security
from .driver_util import GalaxyTestDriver

log = logging.getLogger(__name__)

DEFAULT_TOOL_TEST_WAIT = os.environ.get("GALAXY_TEST_DEFAULT_WAIT", 86400)


class FunctionalTestCase(unittest.TestCase):

    def setUp(self):
        # Security helper
        self.security = security.SecurityHelper(id_secret='changethisinproductiontoo')
        self.history_id = os.environ.get('GALAXY_TEST_HISTORY_ID', None)
        self.host = os.environ.get('GALAXY_TEST_HOST')
        self.port = os.environ.get('GALAXY_TEST_PORT')
        default_url = "http://%s:%s" % (self.host, self.port)
        self.url = os.environ.get('GALAXY_TEST_EXTERNAL', default_url)
        self.test_data_resolver = TestDataResolver()
        self.keepOutdir = os.environ.get('GALAXY_TEST_SAVE', '')
        if self.keepOutdir > '':
            try:
                os.makedirs(self.keepOutdir)
            except Exception:
                pass

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

    # TODO: Make this more generic, shouldn't be related to tool stuff I guess.
    def wait_for(self, func, **kwd):
        sleep_amount = 0.2
        slept = 0
        walltime_exceeded = kwd.get("maxseconds", None)
        if walltime_exceeded is None:
            walltime_exceeded = DEFAULT_TOOL_TEST_WAIT

        exceeded = True
        while slept <= walltime_exceeded:
            result = func()
            if result:
                time.sleep(sleep_amount)
                slept += sleep_amount
                sleep_amount *= 2
            else:
                exceeded = False
                break

        if exceeded:
            message = 'Tool test run exceeded walltime [total %s, max %s], terminating.' % (slept, walltime_exceeded)
            log.info(message)
            raise AssertionError(message)
