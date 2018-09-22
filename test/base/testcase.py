from __future__ import print_function

import logging
import os
import unittest

import pytest

from galaxy.tools.verify.test_data import TestDataResolver
from galaxy.web import security
from .driver_util import setup_keep_outdir, target_url_parts

log = logging.getLogger(__name__)
pytestmark = pytest.mark.usefixtures("test_driver")


class FunctionalTestCase(unittest.TestCase):

    def setUp(self):
        # Security helper
        self.security = security.SecurityHelper(id_secret='changethisinproductiontoo')
        self.history_id = os.environ.get('GALAXY_TEST_HISTORY_ID', None)
        self.host, self.port, self.url = target_url_parts()
        self.test_data_resolver = TestDataResolver()
        self.keepOutdir = setup_keep_outdir()

    def get_filename(self, filename):
        # No longer used by tool tests - drop if isn't used else where.
        return self.test_data_resolver.get_filename(filename)
