"""Utilities for constructing Galaxy integration tests.

Tests that start an actual Galaxy server with a particular configuration in
order to test something that cannot be tested with the default functional/api
testing configuration.
"""
import os
from unittest import skip, SkipTest, TestCase

import pytest

from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.util.commands import which
from galaxy_test.base.api import UsesApiTestCaseMixin
from .driver_util import GalaxyTestDriver

NO_APP_MESSAGE = "test_case._app called though no Galaxy has been configured."
# Following should be for Homebrew Rabbitmq and Docker on Mac "amqp://guest:guest@localhost:5672//"
AMQP_URL = os.environ.get("GALAXY_TEST_AMQP_URL", None)
POSTGRES_CONFIGURED = 'postgres' in os.environ.get("GALAXY_TEST_DBURI", '')


def _identity(func):
    return func


def skip_if_jenkins(cls):
    if os.environ.get("BUILD_NUMBER", ""):
        return skip

    return cls


def skip_unless_amqp():
    if AMQP_URL is not None:
        return _identity
    return pytest.mark.skip("AMQP_URL is not set, required for this test.")


def skip_unless_postgres():
    if POSTGRES_CONFIGURED:
        return _identity
    return pytest.mark.skip("GALAXY_TEST_DBURI does not point to postgres database, required for this test.")


def skip_unless_executable(executable):
    if which(executable):
        return _identity
    return pytest.mark.skip("PATH doesn't contain executable %s" % executable)


def skip_unless_docker():
    return skip_unless_executable("docker")


def skip_unless_kubernetes():
    return skip_unless_executable("kubectl")


def k8s_config_path():
    return os.environ.get('GALAXY_TEST_KUBE_CONFIG_PATH', '~/.kube/config')


def skip_unless_fixed_port():
    if os.environ.get("GALAXY_TEST_PORT_RANDOM") != "1":
        return _identity

    return pytest.mark.skip("GALAXY_TEST_PORT must be set for this test.")


def skip_if_github_workflow():
    if os.environ.get("GITHUB_ACTIONS", None) is None:
        return _identity

    return pytest.mark.skip("This test is skipped for Github actions.")


class IntegrationInstance(UsesApiTestCaseMixin):
    """Unit test case with utilities for spinning up Galaxy."""

    prefer_template_database = True
    # Subclasses can override this to force uwsgi for tests.
    require_uwsgi = False

    # Don't pull in default configs for un-configured things from Galaxy's
    # config directory and such.
    isolate_galaxy_config = True

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
        self.test_data_resolver = TestDataResolver()
        self._configure_interactor()

    def _configure_interactor(self):
        # Setup attributes needed for API testing...
        server_wrapper = self._test_driver.server_wrappers[0]
        host = server_wrapper.host
        port = server_wrapper.port
        self.url = "http://{}:{}".format(host, port)
        self._setup_interactor()

    def restart(self, handle_reconfig=None):
        self._test_driver.restart(config_object=self.__class__, handle_config=handle_reconfig)
        self._configure_app()
        self._configure_interactor()

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

    def _skip_unless_postgres(self):
        if not self._app.config.database_connection.startswith("post"):
            raise SkipTest("Test only valid for postgres")

    @classmethod
    def handle_galaxy_config_kwds(cls, galaxy_config_kwds):
        """Extension point for subclasses to modify arguments used to configure Galaxy.

        This method will be passed the keyword argument pairs used to call
        Galaxy Config object and can modify the Galaxy instance created for
        the test as needed.
        """

    @classmethod
    def handle_uwsgi_cli_command(cls, command):
        """Extension point sub subclasses to modify arguments used to launch uWSGI server.

        Command will a list that can be modified.
        """

    def _run_tool_test(self, *args, **kwargs):
        return self._test_driver.run_tool_test(*args, **kwargs)

    @classmethod
    def temp_config_dir(cls, name):
        # realpath here to get around problems with symlinks being blocked.
        return os.path.realpath(os.path.join(cls._test_driver.galaxy_test_tmp_dir, name))


class IntegrationTestCase(IntegrationInstance, TestCase):
    """Unit TestCase with utilities for spinning up Galaxy."""


def integration_module_instance(clazz):

    def _instance():
        instance = clazz()
        instance.setUpClass()
        instance.setUp()
        yield instance
        instance.tearDownClass()

    return pytest.fixture(scope='module')(_instance)


def integration_tool_runner(tool_ids):

    def test_tools(instance, tool_id):
        instance._run_tool_test(tool_id)

    return pytest.mark.parametrize("tool_id", tool_ids)(test_tools)
