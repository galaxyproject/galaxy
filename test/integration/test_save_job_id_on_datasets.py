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
    # 'multi_output',         # 1 job >> dataset + discovered dataset? (maybe; not implemented yet)
    # test upload?            # not implemented
]


class TestConfig:
    framework_tool_and_types = True


@pytest.mark.parametrize('tool_id', TEST_TOOL_IDS)
def test_tool_datasets(tool_id):
    driver = GalaxyTestDriver()
    driver.setup(TestConfig)
    driver.run_tool_test(tool_id)
    session = driver.app.model.context.current
    job = session.query(model.Job).one()
    datasets = session.query(model.Dataset).all()

    assert len(datasets) > 0
    for d in datasets:
        assert d.job_id == job.id  # this works because we are not reusing the driver

    driver.tear_down()
