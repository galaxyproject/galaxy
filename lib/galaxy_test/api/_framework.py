from unittest import TestCase

from galaxy_test.base.api import UsesApiTestCaseMixin
from galaxy_test.base.testcase import FunctionalTestCase
try:
    from galaxy_test.driver.driver_util import GalaxyTestDriver
except ImportError:
    # Galaxy libraries and galaxy test driver not available, just assume we're
    # targetting a remote Galaxy.
    GalaxyTestDriver = None


class ApiTestCase(FunctionalTestCase, UsesApiTestCaseMixin, TestCase):
    galaxy_driver_class = GalaxyTestDriver

    def setUp(self):
        super(ApiTestCase, self).setUp()
        self._setup_interactor()


__all__ = ('ApiTestCase', )
