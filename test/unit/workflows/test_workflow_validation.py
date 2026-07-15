import os
from typing import Optional

from gxformat2.yaml import ordered_load

from galaxy.util import galaxy_directory
from galaxy.workflow.gx_validator import validate_workflow

TEST_WORKFLOW_DIRECTORY = os.path.join(galaxy_directory(), "lib", "galaxy_test", "workflow")
TEST_BASE_DATA_DIRECTORY = os.path.join(galaxy_directory(), "lib", "galaxy_test", "base", "data")
SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))


def test_validate_simple_functional_test_case_workflow():
    validate_workflow(framework_test_workflow_as_dict("multiple_versions"))
    validate_workflow(framework_test_workflow_as_dict("zip_collection"))
    validate_workflow(framework_test_workflow_as_dict("empty_collection_sort"))
    validate_workflow(framework_test_workflow_as_dict("flatten_collection"))
    validate_workflow(framework_test_workflow_as_dict("flatten_collection_over_execution"))


def test_validate_native_workflows():
    validate_workflow(base_package_workflow_as_dict("test_workflow_two_random_lines.ga"))
    # disconnected input...
    # validate_workflow(base_package_workflow_as_dict("test_workflow_topoambigouity.ga"))
    # double nested JSON?
    # validate_workflow(base_package_workflow_as_dict("test_Workflow_map_reduce_pause.ga"))
    # handle subworkflows...
    # validate_workflow(base_package_workflow_as_dict("test_subworkflow_with_integer_input.ga"))
    # handle gx_text....
    # validate_workflow(base_package_workflow_as_dict("test_workflow_batch.ga"))


def test_validate_unit_test_workflows():
    validate_workflow(unit_test_workflow_as_dict("valid/simple_int"))
    validate_workflow(unit_test_workflow_as_dict("valid/simple_data"))


def test_invalidate_with_extra_attribute():
    e = _assert_validation_failure("invalid/extra_attribute")
    assert "parameter2" in str(e)


def test_invalidate_with_wrong_link_name():
    e = _assert_validation_failure("invalid/wrong_link_name")
    assert "parameterx" in str(e)


def test_invalidate_with_missing_link():
    e = _assert_validation_failure("invalid/missing_link")
    assert "parameter" in str(e)
    assert "type=missing" in str(e)


def _assert_validation_failure(workflow_name: str) -> Exception:
    as_dict = unit_test_workflow_as_dict(workflow_name)
    exc: Optional[Exception] = None
    try:
        validate_workflow(as_dict)
    except Exception as e:
        exc = e
    assert exc, f"Target workflow ({workflow_name}) did not failure validation as expected."
    return exc


def base_package_workflow_as_dict(file_name: str) -> dict:
    return _load(os.path.join(TEST_BASE_DATA_DIRECTORY, file_name))


def unit_test_workflow_as_dict(workflow_name: str) -> dict:
    return _load(os.path.join(SCRIPT_DIRECTORY, f"{workflow_name}.gxwf.yml"))


def framework_test_workflow_as_dict(workflow_name: str) -> dict:
    return _load(os.path.join(TEST_WORKFLOW_DIRECTORY, f"{workflow_name}.gxwf.yml"))


def _load(path: str) -> dict:
    with open(path) as f:
        return ordered_load(f)
