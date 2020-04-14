import pytest

from galaxy_test.driver.driver_util import GalaxyConfigTestDriver as Driver


@pytest.fixture(scope='module')
def driver(request):
    request.addfinalizer(DRIVER.tear_down)
    return DRIVER


def create_driver():
    global DRIVER
    DRIVER = Driver()
    DRIVER.setup()


def get_config_data():
    create_driver()
    config = DRIVER.app.config
    return [config.schema.app_schema['admin_users']]


@pytest.mark.parametrize('data', get_config_data())
def test_one(data, driver):
    assert True
