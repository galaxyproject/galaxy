import os
from pathlib import Path
from typing import List

import yaml

from galaxy.tool_util.models import Tests
from galaxy.util import galaxy_directory
from galaxy.util.unittest_utils import skip_unless_environ

TEST_WORKFLOW_DIRECTORY = os.path.join(galaxy_directory(), "lib", "galaxy_test", "workflow")
IWC_WORKFLOWS_USING_UNVERIFIED_SYNTAX: List[str] = []


def test_validate_workflow_tests():
    path = Path(TEST_WORKFLOW_DIRECTORY)
    test_files = path.glob("*.gxwf-tests.yml")
    for test_file in test_files:
        with open(test_file) as f:
            json = yaml.safe_load(f)
        Tests.model_validate(json)


@skip_unless_environ("GALAXY_TEST_IWC_DIRECTORY")
def test_iwc_directory():
    path = Path(os.environ["GALAXY_TEST_IWC_DIRECTORY"])
    test_files = path.glob("workflows/**/*-test*.yml")

    for test_file in test_files:
        print(test_file)
        skip_file = False
        for unverified in IWC_WORKFLOWS_USING_UNVERIFIED_SYNTAX:
            if str(test_file).endswith(unverified):
                skip_file = True
        if skip_file:
            continue
        with open(test_file) as f:
            json = yaml.safe_load(f)
        Tests.model_validate(json)
