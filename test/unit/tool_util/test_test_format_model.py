import os
from pathlib import Path
from typing import List

import pytest
import yaml
from pydantic import ValidationError

from galaxy.tool_util_models import Tests
from galaxy.tool_util_models.test_job import Job
from galaxy.util import galaxy_directory
from galaxy.util.unittest_utils import skip_unless_environ

TEST_WORKFLOW_DIRECTORY = os.path.join(galaxy_directory(), "lib", "galaxy_test", "workflow")
IWC_WORKFLOWS_USING_UNVERIFIED_SYNTAX: List[str] = []

# replacement_parameters_legacy.gxwf-tests.yml is a deliberate regression test
# for Planemo-era implicit replacement_parameters: {...} dicts embedded in
# job:. That key is popped out by WorkflowPopulator.run_workflow before
# staging, so the runtime accepts it but it is not canonical workflow-test
# input syntax and the strict Job schema does not model it.
WORKFLOW_TESTS_SKIP_STRICT_VALIDATION: List[str] = [
    "replacement_parameters_legacy.gxwf-tests.yml",
]

TEST_JOB_FIXTURES_DIR = Path(__file__).parent / "test_data" / "test_job_fixtures"


def _load_fixture(name: str):
    with open(TEST_JOB_FIXTURES_DIR / name) as f:
        return yaml.safe_load(f)


JOB_POSITIVE_FIXTURES = [
    "file_path.yml",
    "file_location.yml",
    "file_composite.yml",
    "file_contents.yml",
    "file_with_tags_and_dbkey.yml",
    "collection_list.yml",
    "collection_paired.yml",
    "collection_nested.yml",
    "directory.yml",
    "scalars.yml",
    "list_of_files.yml",
    "list_of_scalars.yml",
]

JOB_NEGATIVE_FIXTURES = [
    "neg_legacy_type_file.yml",
    "neg_legacy_type_raw.yml",
    "neg_elements_without_class.yml",
    "neg_file_no_path_or_location.yml",
    "neg_unknown_field.yml",
    "neg_bad_collection_type.yml",
    "neg_top_level_not_dict.yml",
]


@pytest.mark.parametrize("fixture", JOB_POSITIVE_FIXTURES)
def test_job_positive_fixtures(fixture: str) -> None:
    Job.model_validate(_load_fixture(fixture))


@pytest.mark.parametrize("fixture", JOB_NEGATIVE_FIXTURES)
def test_job_negative_fixtures(fixture: str) -> None:
    with pytest.raises(ValidationError):
        Job.model_validate(_load_fixture(fixture))


def test_validate_workflow_tests():
    path = Path(TEST_WORKFLOW_DIRECTORY)
    test_files = path.glob("*.gxwf-tests.yml")
    for test_file in test_files:
        if test_file.name in WORKFLOW_TESTS_SKIP_STRICT_VALIDATION:
            continue
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
