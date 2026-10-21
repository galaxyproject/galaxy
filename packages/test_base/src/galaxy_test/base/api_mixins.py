"""API test case mixins shared by the API and integration test suites."""

import time
from typing import ClassVar
from unittest import SkipTest
from uuid import uuid4

from requests import put

from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy_test.base.api import UsesApiTestCaseMixin
from galaxy_test.base.api_asserts import (
    assert_has_keys,
    assert_status_code_is,
)
from galaxy_test.base.populators import (
    BaseDatasetCollectionPopulator,
    DatasetCollectionPopulator,
    DatasetPopulator,
    RunJobsSummary,
    skip_without_tool,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import (
    WORKFLOW_INPUTS_AS_OUTPUTS,
    WORKFLOW_WITH_BAD_COLUMN_PARAMETER,
    WORKFLOW_WITH_BAD_COLUMN_PARAMETER_GOOD_TEST_DATA,
    WORKFLOW_WITH_MAPPED_OUTPUT_COLLECTION,
)


class TestsTools:
    dataset_populator: DatasetPopulator
    dataset_collection_populator: BaseDatasetCollectionPopulator

    def _build_pair(self, history_id, contents):
        create_response = self.dataset_collection_populator.create_pair_in_history(
            history_id,
            contents=contents,
            direct_upload=True,
            wait=True,
        )
        hdca_id = create_response.json()["outputs"][0]["id"]
        return hdca_id

    def _get_build_option_values(self, build, input_name):
        matching = [i for i in build["inputs"] if i["name"] == input_name][0]
        return [o[1] for o in matching["options"]]

    def _run_cat(self, history_id, inputs, assert_ok=False, **kwargs):
        return self._run("cat", history_id, inputs, assert_ok=assert_ok, **kwargs)

    def _run(
        self,
        tool_id=None,
        history_id=None,
        inputs=None,
        tool_uuid=None,
        assert_ok=False,
        tool_version=None,
        use_cached_job=False,
        wait_for_job=False,
        input_format="legacy",
    ):
        if inputs is None:
            inputs = {}
        if tool_id is None:
            assert tool_uuid is not None
        payload = self.dataset_populator.run_tool_payload(
            tool_id=tool_id,
            inputs=inputs,
            history_id=history_id,
            input_format=input_format,
        )
        if tool_uuid:
            payload["tool_uuid"] = tool_uuid
        if tool_version is not None:
            payload["tool_version"] = tool_version
        if use_cached_job:
            payload["use_cached_job"] = True
        create_response = self.dataset_populator._post("tools", data=payload)
        if wait_for_job:
            self.dataset_populator.wait_for_job(job_id=create_response.json()["jobs"][0]["id"])
        if assert_ok:
            assert_status_code_is(create_response, 200)
            create = create_response.json()
            assert_has_keys(create, "outputs")
            return create
        else:
            return create_response


class RunsWorkflowFixtures:
    workflow_populator: WorkflowPopulator

    def _run_workflow_with_inputs_as_outputs(self, history_id: str) -> RunJobsSummary:
        summary = self.workflow_populator.run_workflow(
            WORKFLOW_INPUTS_AS_OUTPUTS,
            test_data={"input1": "hello world", "text_input": {"value": "A text variable", "type": "raw"}},
            history_id=history_id,
        )
        return summary

    def _run_workflow_with_output_collections(self, history_id: str) -> RunJobsSummary:
        summary = self.workflow_populator.run_workflow(
            WORKFLOW_WITH_MAPPED_OUTPUT_COLLECTION,
            test_data="""
input1:
  collection_type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""",
            history_id=history_id,
            round_trip_format_conversion=True,
        )
        return summary

    def _run_workflow_with_runtime_data_column_parameter(self, history_id: str) -> RunJobsSummary:
        return self.workflow_populator.run_workflow(
            WORKFLOW_WITH_BAD_COLUMN_PARAMETER,
            test_data=WORKFLOW_WITH_BAD_COLUMN_PARAMETER_GOOD_TEST_DATA,
            history_id=history_id,
        )

    def _run_workflow_once_get_invocation(self, name: str):
        workflow = self.workflow_populator.load_workflow(name=name)
        workflow_request, history_id, workflow_id = self.workflow_populator.setup_workflow_run(workflow)
        usages = self.workflow_populator.workflow_invocations(workflow_id)
        assert len(usages) == 0
        self.workflow_populator.invoke_workflow_raw(workflow_id, workflow_request, assert_ok=True)
        usages = self.workflow_populator.workflow_invocations(workflow_id)
        assert len(usages) == 1
        return workflow_id, usages[0]


class ChangeDatatypeTests:
    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    def test_assign_column_pja(self):
        with self.dataset_populator.test_history() as history_id:
            self.workflow_populator.run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
    out:
      out_file1:
        change_datatype: bed
        set_columns:
          chromCol: 1
          endCol: 2
          startCol: 3
""",
                test_data="""
input1:
  value: 1.bed
  type: File
""",
                history_id=history_id,
            )
            details_dataset_new_col = self.dataset_populator.get_history_dataset_details(
                history_id, hid=2, wait=True, assert_ok=True
            )
            assert details_dataset_new_col["history_content_type"] == "dataset", details_dataset_new_col
            assert details_dataset_new_col["metadata_endCol"] == 2
            assert details_dataset_new_col["metadata_startCol"] == 3


class BaseHistories(UsesApiTestCaseMixin):
    def _show(self, history_id):
        return self._get(f"histories/{history_id}").json()

    def _update(self, history_id, data):
        update_url = self._api_url(f"histories/{history_id}", use_key=True)
        put_response = put(update_url, json=data)
        return put_response

    def _create_history(self, name):
        post_data = dict(name=name)
        create_response = self._post("histories", data=post_data).json()
        self._assert_has_keys(create_response, "name", "id")
        assert create_response["name"] == name
        return create_response

    def _assert_history_length(self, history_id, n):
        contents_response = self._get(f"histories/{history_id}/contents")
        self._assert_status_code_is(contents_response, 200)
        contents = contents_response.json()
        assert len(contents) == n, contents


class ImportExportTests(BaseHistories):
    task_based: ClassVar[bool]
    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator
    test_data_resolver: TestDataResolver

    def _set_up_populators(self):
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_import_export(self):
        history_name = f"for_export_default_{uuid4()}"
        history_id = self.dataset_populator.setup_history_for_export_testing(history_name)
        imported_history_id = self._reimport_history(history_id, history_name, wait_on_history_length=2)

        def upload_job_check(job):
            assert job["tool_id"] == "__DATA_FETCH__"

        def check_discarded(hda):
            assert hda["deleted"]
            assert hda["state"] == "discarded", hda
            assert hda["purged"] is True

        self._check_imported_dataset(history_id=imported_history_id, hid=1, job_checker=upload_job_check)
        self._check_imported_dataset(
            history_id=imported_history_id,
            hid=2,
            has_job=False,
            hda_checker=check_discarded,
            job_checker=upload_job_check,
        )

        imported_content = self.dataset_populator.get_history_dataset_content(
            history_id=imported_history_id,
            hid=1,
        )
        assert imported_content == "1 2 3\n"

    def test_import_1901_histories(self):
        f = open(self.test_data_resolver.get_filename("exports/1901_two_datasets.tgz"), "rb")
        import_data = dict(archive_source="", archive_file=f)
        self._import_history_and_wait(import_data, "API Test History", wait_on_history_length=2)

    def test_import_export_include_deleted(self):
        history_name = f"for_export_include_deleted_{uuid4()}"
        history_id = self.dataset_populator.new_history(name=history_name)
        self.dataset_populator.new_dataset(history_id, content="1 2 3")
        deleted_hda = self.dataset_populator.new_dataset(history_id, content="1 2 3", wait=True)
        self.dataset_populator.delete_dataset(history_id, deleted_hda["id"])

        imported_history_id = self._reimport_history(
            history_id, history_name, wait_on_history_length=2, export_kwds={"include_deleted": True}
        )
        self._assert_history_length(imported_history_id, 2)

        def upload_job_check(job):
            assert job["tool_id"] == "__DATA_FETCH__"

        def check_deleted_not_purged(hda):
            assert hda["state"] == "ok", hda
            assert hda["deleted"] is True, hda
            assert hda["purged"] is False, hda

        self._check_imported_dataset(history_id=imported_history_id, hid=1, job_checker=upload_job_check)
        self._check_imported_dataset(
            history_id=imported_history_id, hid=2, hda_checker=check_deleted_not_purged, job_checker=upload_job_check
        )

        imported_content = self.dataset_populator.get_history_dataset_content(
            history_id=imported_history_id,
            hid=1,
        )
        assert imported_content == "1 2 3\n"

    @skip_without_tool("job_properties")
    def test_import_export_failed_job(self):
        history_name = f"for_export_include_failed_job_{uuid4()}"
        history_id = self.dataset_populator.new_history(name=history_name)
        self.dataset_populator.run_tool_raw("job_properties", inputs={"failbool": True}, history_id=history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=False)

        imported_history_id = self._reimport_history(
            history_id, history_name, assert_ok=False, wait_on_history_length=4, export_kwds={"include_deleted": True}
        )
        self._assert_history_length(imported_history_id, 4)

        def check_failed(hda_or_job):
            print(hda_or_job)
            assert hda_or_job["state"] == "error", hda_or_job

        self.dataset_populator._summarize_history(imported_history_id)

        self._check_imported_dataset(
            history_id=imported_history_id, hid=1, assert_ok=False, hda_checker=check_failed, job_checker=check_failed
        )

        # Also check collection state is preserved - regression test for issue #20450
        imported_collection = self.dataset_populator.get_history_collection_details(
            history_id=imported_history_id,
            history_content_type="dataset_collection",
            assert_ok=False,
        )
        assert "job_state_summary" in imported_collection, imported_collection
        assert imported_collection["job_state_summary"].get("error", 0) == 1, (
            f"Expected error count of 1 after import, got {imported_collection['job_state_summary']}. "
            "Collection job state was not preserved during history export/import (issue #20450)."
        )

    def test_import_metadata_regeneration(self):
        if self.task_based:
            raise SkipTest("skipping test_import_metadata_regeneration for task based...")
        history_name = f"for_import_metadata_regeneration_{uuid4()}"
        history_id = self.dataset_populator.new_history(name=history_name)
        self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver)
        imported_history_id = self._reimport_history(history_id, history_name)
        self._assert_history_length(imported_history_id, 1)
        self._check_imported_dataset(history_id=imported_history_id, hid=1)
        import_bam_metadata = self.dataset_populator.get_history_dataset_details(
            history_id=imported_history_id,
            hid=1,
        )
        # The cleanup() method of the __IMPORT_HISTORY__ job (which is executed
        # after the job has entered its final state):
        # - creates a new dataset with 'ok' state and adds it to the history
        # - starts a __SET_METADATA__ job to regenerate the dataset metadata, if
        #   needed
        # We need to wait a bit for the creation of the __SET_METADATA__ job.
        time.sleep(1)
        self.dataset_populator.wait_for_history_jobs(imported_history_id, assert_ok=True)
        bai_metadata = import_bam_metadata["meta_files"][0]
        assert bai_metadata["file_type"] == "bam_index"
        assert "api/" in bai_metadata["download_url"], bai_metadata["download_url"]
        api_url = bai_metadata["download_url"].split("api/", 1)[1]
        bai_response = self._get(api_url)
        self._assert_status_code_is(bai_response, 200)
        assert len(bai_response.content) > 4

    def test_import_export_collection(self):
        history_name = f"for_export_with_collections_{uuid4()}"
        history_id = self.dataset_populator.new_history(name=history_name)
        self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["Hello", "World"], direct_upload=True, wait=True
        )

        imported_history_id = self._reimport_history(history_id, history_name, wait_on_history_length=3)
        self._assert_history_length(imported_history_id, 3)

        def check_elements(elements):
            assert len(elements) == 2
            element0 = elements[0]["object"]
            element1 = elements[1]["object"]
            for element in [element0, element1]:
                assert not element["visible"]
                assert not element["deleted"]
                assert element["state"] == "ok"

            assert element0["hid"] == 2
            assert element1["hid"] == 3

        self._check_imported_collection(
            imported_history_id, hid=1, collection_type="list", elements_checker=check_elements
        )

    def test_import_export_nested_collection(self):
        history_name = f"for_export_with_nested_collections_{uuid4()}"
        history_id = self.dataset_populator.new_history(name=history_name)
        fetch_response = self.dataset_collection_populator.create_list_of_pairs_in_history(history_id, wait=True).json()
        dataset_collection = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)

        imported_history_id = self._reimport_history(history_id, history_name, wait_on_history_length=3)
        self._assert_history_length(imported_history_id, 3)

        def check_elements(elements):
            assert len(elements) == 1
            element0 = elements[0]["object"]
            self._assert_has_keys(element0, "elements", "collection_type")

            child_elements = element0["elements"]

            assert len(child_elements) == 2
            assert element0["collection_type"] == "paired"

        self._check_imported_collection(
            imported_history_id,
            hid=dataset_collection["hid"],
            collection_type="list:paired",
            elements_checker=check_elements,
        )

    def _reimport_history(
        self, history_id, history_name, wait_on_history_length=None, assert_ok=True, export_kwds=None
    ):
        # Ensure the history is ready to go...
        export_kwds = export_kwds or {}
        self.dataset_populator.wait_for_history(history_id, assert_ok=assert_ok)

        return self.dataset_populator.reimport_history(
            history_id,
            history_name,
            wait_on_history_length=wait_on_history_length,
            export_kwds=export_kwds,
            task_based=self.task_based,
        )

    def _import_history_and_wait(self, import_data, history_name, wait_on_history_length=None):
        imported_history_id = self.dataset_populator.import_history_and_wait_for_name(import_data, history_name)

        if wait_on_history_length:
            self.dataset_populator.wait_on_history_length(imported_history_id, wait_on_history_length)

        return imported_history_id

    def _check_imported_dataset(
        self, history_id, hid, assert_ok=True, has_job=True, hda_checker=None, job_checker=None
    ):
        imported_dataset_metadata = self.dataset_populator.get_history_dataset_details(
            history_id=history_id,
            hid=hid,
            assert_ok=assert_ok,
        )
        assert imported_dataset_metadata["history_content_type"] == "dataset"
        assert imported_dataset_metadata["history_id"] == history_id

        if hda_checker is not None:
            hda_checker(imported_dataset_metadata)

        assert "creating_job" in imported_dataset_metadata
        job_id = imported_dataset_metadata["creating_job"]
        if has_job:
            assert job_id

            job_details = self.dataset_populator.get_job_details(job_id, full=True)
            assert job_details.status_code == 200, job_details.content
            job = job_details.json()
            assert "history_id" in job, job
            assert job["history_id"] == history_id, job

            if job_checker is not None:
                job_checker(job)

    def _check_imported_collection(self, history_id, hid, collection_type=None, elements_checker=None):
        imported_collection_metadata = self.dataset_populator.get_history_collection_details(
            history_id=history_id,
            hid=hid,
        )
        assert imported_collection_metadata["history_content_type"] == "dataset_collection"
        assert imported_collection_metadata["history_id"] == history_id
        assert "collection_type" in imported_collection_metadata
        assert "elements" in imported_collection_metadata
        if collection_type is not None:
            assert imported_collection_metadata["collection_type"] == collection_type, imported_collection_metadata

        if elements_checker is not None:
            elements_checker(imported_collection_metadata["elements"])
