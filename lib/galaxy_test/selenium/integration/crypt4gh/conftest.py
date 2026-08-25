"""Pytest configuration for Crypt4GH Selenium tests.

Overrides the parent ``real_driver`` fixture to start Galaxy with crypt4gh
configuration.  The mock recryptor server and test keys are created as
session-scoped fixtures and injected into the test class before the Galaxy
server starts.
"""

import os

import pytest

from .crypt4gh_test_utils import generate_test_keys
from .framework import Crypt4ghIntegrationSeleniumTestCase
from .mock_recryptor import MockRecryptorServer


@pytest.fixture(scope="session")
def crypt4gh_test_keys():
    return generate_test_keys()


@pytest.fixture(scope="session")
def mock_recryptor_server(crypt4gh_test_keys):
    server = MockRecryptorServer(crypt4gh_test_keys)
    server.start()
    yield server
    server.shutdown()


@pytest.fixture(scope="session")
def real_driver(mock_recryptor_server, crypt4gh_test_keys):
    if not os.environ.get("GALAXY_TEST_ENVIRONMENT_CONFIGURED"):
        from galaxy_test.driver.driver_util import GalaxyTestDriver

        # Inject crypt4gh config into the test class before Galaxy starts
        Crypt4ghIntegrationSeleniumTestCase.mock_recryptor_url = mock_recryptor_server.base_url
        Crypt4ghIntegrationSeleniumTestCase.crypt4gh_keys = crypt4gh_test_keys

        driver = GalaxyTestDriver()
        driver.setup(Crypt4ghIntegrationSeleniumTestCase)
        try:
            yield driver
        finally:
            driver.tear_down()
    else:
        yield None


@pytest.fixture(scope="class")
def embedded_driver(real_driver, request):
    request.cls._test_driver = real_driver
