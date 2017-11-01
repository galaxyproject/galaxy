"""Utilities for constructing Galaxy integration tests.

Tests that start an actual Galaxy server with a particular configuration in
order to test something that cannot be tested with the default functional/api
tessting configuration.
"""
from unittest import TestCase

from .api import UsesApiTestCaseMixin
from .driver_util import GalaxyTestDriver

NO_APP_MESSAGE = "test_case._app called though no Galaxy has been configured."


class IntegrationTestCase(TestCase, UsesApiTestCaseMixin):
    """Unit test case with utilities for spinning up Galaxy."""

    @classmethod
    def setUpClass(cls):
        """Configure and start Galaxy for a test."""
        cls._app_available = False
        cls._test_driver = GalaxyTestDriver()
        cls._prepare_galaxy()
        cls._test_driver.setup(config_object=cls)
        cls._app_available = True
        cls._configure_app()

    @classmethod
    def tearDownClass(cls):
        """Shutdown Galaxy server and cleanup temp directory."""
        cls._test_driver.tear_down()
        cls._app_available = False

    def setUp(self):
        # Setup attributes needed for API testing...
        server_wrapper = self._test_driver.server_wrappers[0]
        host = server_wrapper.host
        port = server_wrapper.port
        self.url = "http://%s:%s" % (host, port)
        self._setup_interactor()

    @property
    def _app(self):
        assert self._app_available, NO_APP_MESSAGE
        return self._test_driver.app

    @property
    def _tempdir(self):
        return self._test_driver.galaxy_test_tmp_dir

    @classmethod
    def _prepare_galaxy(cls):
        """Extension point for subclasses called before Galaxy is launched."""

    @classmethod
    def _configure_app(cls):
        """Extension point for subclasses called after Galaxy is launched.

        ```self._app``` can be used to access Galaxy core app.
        """

    @classmethod
    def handle_galaxy_config_kwds(cls, galaxy_config_kwds):
        """Extension point for subclasses to modify arguments used to configure Galaxy.

        This method will be passed the keyword argument pairs used to call
        Galaxy Config object and can modify the Galaxy instance created for
        the test as needed.
        """

    def _run_tool_test(self, *args, **kwargs):
        return self._test_driver.run_tool_test(*args, **kwargs)
