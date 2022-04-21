from galaxy_test.base.testcase import FunctionalTestCase
from .driver_util import GalaxyTestDriver


class DrivenFunctionalTestCase(FunctionalTestCase):
    """Variant of FunctionalTestCase that can launch Galaxy instances."""

    galaxy_driver_class = GalaxyTestDriver
