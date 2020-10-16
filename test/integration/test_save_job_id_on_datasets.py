"""
A Dataset should have a reference to the Job that created it.
Here we test the creation of this reference in various contexts:
- job creates one dataset
- job creates multiple datasets
- job uploads a dataset
- job creates dynamically discovered datasets (after the tool is run)
"""

import pytest

from galaxy import model
from galaxy_test.driver.driver_util import GalaxyTestDriver

TEST_TOOL_IDS = [
    'boolean_conditional',  # 1 job >> 1 dataset
    'color_param',          # 1 job >> multiple datasets
    'multi_output',         # 1 job >> 1 dataset + 1 discovered dataset
    # test upload?            # not implemented
]


@pytest.fixture(scope='module')
def driver(request):
    request.addfinalizer(DRIVER.tear_down)
    return DRIVER


def create_driver():
    # Same approach as in functional/test_toolbox_pytest.py:
    # We setup a global driver, so that the driver fixture can tear down the driver.
    # Ideally `create_driver` would be a fixture and clean up after the yield,
    # but that's not compatible with the use use of pytest.mark.parametrize:
    # a fixture is not directly callable, so it cannot be used in place of get_config_data.
    global DRIVER
    DRIVER = GalaxyTestDriver()
    DRIVER.setup(TestConfig)


class TestConfig:
    framework_tool_and_types = True


@pytest.mark.parametrize('tool_id', TEST_TOOL_IDS)
def test_tool_datasets(tool_id, driver):
    driver.run_tool_test(tool_id)
    session = driver.app.model.context.current
    job = session.query(model.Job).order_by(model.Job.id.desc()).first()
    datasets = session.query(model.Dataset).filter(model.Dataset.job_id == job.id).all()

    if tool_id == 'boolean_conditional':
        assert len(datasets) == 1
    elif tool_id in ('color_param', 'multi_output'):
        assert len(datasets) == 2


create_driver()
