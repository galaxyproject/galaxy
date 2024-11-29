import glob
import os
import tempfile
from pathlib import Path

import pytest
import requests
import yaml
from gxformat2.yaml import ordered_load

from galaxy.tool_util.models import (
    OutputChecks,
    OutputsDict,
    TestDicts,
    TestJobDict,
)
from galaxy.tool_util.parser.interface import TestCollectionOutputDef
from galaxy.tool_util.verify import verify_file_contents_against_dict
from galaxy.tool_util.verify.interactor import (
    compare_expected_metadata_to_api_response,
    get_metadata_to_test,
    verify_collection,
)
from galaxy.util import asbool
from galaxy_test.api._framework import ApiTestCase
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    RunJobsSummary,
    WorkflowPopulator,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
TEST_WORKFLOW_AFTER_RERUN = asbool(os.environ.get("GALAXY_TEST_WORKFLOW_AFTER_RERUN", "0"))


def find_workflows():
    return [Path(p) for p in glob.glob(f"{SCRIPT_DIRECTORY}/*.gxwf.yml")]


def pytest_generate_tests(metafunc):
    parameter_combinations = []
    test_ids = []
    for workflow_path in find_workflows():
        for index, test_job in enumerate(_test_jobs(workflow_path)):
            parameter_combinations.append([workflow_path, test_job])
            workflow_test_name = workflow_path.name[0 : -len(".gxwf.yml")]
            test_ids.append(f"{workflow_test_name}_{index}")
    if "workflow_path" in metafunc.fixturenames:
        metafunc.parametrize("workflow_path,test_job", parameter_combinations, ids=test_ids)


class TestWorkflow(ApiTestCase):
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    @pytest.mark.workflow
    def test_workflow(self, workflow_path: Path, test_job: TestJobDict):
        with workflow_path.open() as f:
            yaml_content = ordered_load(f)
        with self.dataset_populator.test_history() as history_id:
            exc = None
            try:
                run_summary = self.workflow_populator.run_workflow(
                    yaml_content,
                    test_data=test_job["job"],
                    history_id=history_id,
                )
                if TEST_WORKFLOW_AFTER_RERUN:
                    run_summary = self.workflow_populator.rerun(run_summary)
                self._verify(run_summary, test_job["outputs"])
            except Exception as e:
                exc = e
            if test_job.get("expect_failure"):
                if not exc:
                    raise Exception("Expected workflow test to fail but it passed")
            elif exc:
                raise exc

    def _verify(self, run_summary: RunJobsSummary, output_definitions: OutputsDict):
        for output_name, output_definition in output_definitions.items():
            self._verify_output(run_summary, output_name, output_definition)

    def _verify_output(self, run_summary: RunJobsSummary, output_name, test_properties: OutputChecks):
        is_collection_test = isinstance(test_properties, dict) and (
            "elements" in test_properties or test_properties.get("class") == "Collection"
        )
        item_label = f"Output named {output_name}"

        def get_filename(name):
            return tempfile.NamedTemporaryFile(prefix=f"gx_workflow_framework_test_file_{output_name}", delete=False)

        def verify_dataset(dataset: dict, test_properties: OutputChecks):
            output_content = self.dataset_populator.get_history_dataset_content(
                run_summary.history_id, dataset=dataset, type="bytes"
            )
            verify_file_contents_against_dict(get_filename, _get_location, item_label, output_content, test_properties)
            if isinstance(test_properties, dict):
                metadata = get_metadata_to_test(test_properties)
                if metadata:
                    dataset_details = self.dataset_populator.get_history_dataset_details(
                        run_summary.history_id, content_id=dataset["id"]
                    )
                    compare_expected_metadata_to_api_response(metadata, dataset_details)

        if is_collection_test:
            assert isinstance(test_properties, dict)
            test_properties["name"] = output_name
            output_def = TestCollectionOutputDef.from_yaml_test_format(test_properties)
            invocation_details = self.workflow_populator.get_invocation(run_summary.invocation_id, step_details=True)
            assert output_name in invocation_details["output_collections"]
            test_output = invocation_details["output_collections"][output_name]
            output_collection = self.dataset_populator.get_history_collection_details(
                run_summary.history_id, content_id=test_output["id"]
            )

            def verify_dataset_element(element, test_properties, element_outfile):
                hda = element["object"]
                verify_dataset(hda, test_properties)

            verify_collection(output_def, output_collection, verify_dataset_element)
        else:
            if isinstance(test_properties, dict):
                test_properties["name"] = output_name
            invocation_details = self.workflow_populator.get_invocation(run_summary.invocation_id, step_details=True)
            assert output_name in invocation_details["outputs"]
            test_output = invocation_details["outputs"][output_name]
            verify_dataset(test_output, test_properties)


def _test_jobs(workflow_path: Path) -> TestDicts:
    test_path = _workflow_test_path(workflow_path)
    with test_path.open() as f:
        jobs = yaml.safe_load(f)
    return jobs


def _workflow_test_path(workflow_path: Path) -> Path:
    base_name = workflow_path.name[0 : -len(".gxwf.yml")]
    test_path = workflow_path.parent / f"{base_name}.gxwf-tests.yml"
    return test_path


def _get_location(location: str) -> str:
    data_file = tempfile.NamedTemporaryFile(prefix="gx_workflow_framework_test_file_", delete=False)
    with requests.get(location, stream=True) as r:
        r.raise_for_status()

        for chunk in r.iter_content():
            if chunk:
                data_file.write(chunk)
        return data_file.name
