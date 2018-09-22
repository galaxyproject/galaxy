import os

import pytest
from base.driver_util import GalaxyTestDriver


@pytest.fixture(scope='session', autouse=True)
def test_driver(request):
    if os.environ.get("GALAXY_TEST_ENVIRONMENT_CONFIGURED"):
        _test_driver = None
    else:
        _test_driver = GalaxyTestDriver()
        _test_driver.setup(config_object=request._parent_request.cls)
    request.session.test_driver = test_driver
    yield
    _test_driver.tear_down()
