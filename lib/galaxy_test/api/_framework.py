from typing import Optional
from unittest import (
    SkipTest,
    TestCase,
)

from galaxy_test.base.api import (
    UsesApiTestCaseMixin,
    UsesCeleryTasks,
)
from galaxy_test.base.testcase import FunctionalTestCase

try:
    from galaxy_test.driver.driver_util import GalaxyTestDriver
except ImportError:
    # Galaxy libraries and galaxy test driver not available, just assume we're
    # targetting a remote Galaxy.
    GalaxyTestDriver = None  # type: ignore[misc,assignment]


class ApiTestCase(FunctionalTestCase, UsesApiTestCaseMixin, UsesCeleryTasks, TestCase):
    galaxy_driver_class = GalaxyTestDriver
    _test_driver: Optional[GalaxyTestDriver]

    def setUp(self):
        super().setUp()
        self._setup_interactor()

    def driver_or_skip_test_if_remote(self) -> GalaxyTestDriver:
        if self._test_driver is None:
            raise SkipTest("This test does not work with remote Galaxy instances.")
        return self._test_driver


__all__ = ("ApiTestCase",)
