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


class TestConfig:
    framework_tool_and_types = True


TEST_TOOL_IDS = [
    "boolean_conditional",  # 1 job >> 1 dataset
    "color_param",  # 1 job >> multiple datasets
    "multi_output",  # 1 job >> 1 dataset + 1 discovered dataset
    # test upload?            # not implemented
]


@pytest.fixture()
def test_driver():
    driver = GalaxyTestDriver()
    driver.setup(TestConfig)
    try:
        yield driver
    finally:
        driver.tear_down()


@pytest.mark.parametrize("tool_id", TEST_TOOL_IDS)
def test_tool_datasets(tool_id, test_driver):
    test_driver.run_tool_test(tool_id)
    session = test_driver.app.model.context.current
    job = session.query(model.Job).order_by(model.Job.id.desc()).first()
    datasets = session.query(model.Dataset).filter(model.Dataset.job_id == job.id).all()

    if tool_id == "boolean_conditional":
        assert len(datasets) == 1
    elif tool_id in ("color_param", "multi_output"):
        assert len(datasets) == 2
