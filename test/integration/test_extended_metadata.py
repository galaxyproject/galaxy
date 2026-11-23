"""Integration tests for the Pulsar embedded runner."""

import json
import os
from collections.abc import (
    Callable,
    Iterator,
)
from contextlib import contextmanager
from typing import Any
from unittest import mock

from sqlalchemy import (
    func,
    select,
)

from galaxy.model import (
    DatasetCollectionElement,
    HistoryDatasetCollectionAssociation,
    Job,
    store,
)
from galaxy.tool_util_models import UserToolSource
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    LibraryPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from galaxy_test.driver import integration_util
from .objectstore._purged_handling import purge_while_job_running

TEST_TOOL_IDS = [
    "from_work_dir_glob",
    "from_work_dir_glob_output_written",
    "job_properties",
    "multi_output",
    "multi_output_configured",
    "multi_output_assign_primary",
    "multi_output_assign_primary_ext_dbkey",
    "multi_output_recurse",
    "tool_provided_metadata_1",
    "tool_provided_metadata_2",
    "tool_provided_metadata_3",
    "tool_provided_metadata_4",
    "tool_provided_metadata_5",
    "tool_provided_metadata_6",
    "tool_provided_metadata_7",
    "tool_provided_metadata_8",
    "tool_provided_metadata_9",
    "tool_provided_metadata_10",
    "tool_provided_metadata_11",
    "tool_provided_metadata_12",
    "composite_output",
    "composite_output_tests",
    "metadata",
    "metadata_defaults",
    "metadata_bam",
    "discover_metadata_files",
    "output_format",
    "output_auto_format",
    "collection_paired_test",
    "collection_paired_structured_like",
    "collection_nested_test",
    "collection_creates_list",
    "collection_creates_dynamic_nested",
    "collection_creates_dynamic_nested_from_json",
    "collection_creates_dynamic_nested_from_json_elements",
    "implicit_conversion",
    "environment_variables",
    "all_output_types",
    "discover_sort_by",
    "discover_unknown_ext",
    "discover_format_tokens",
    "create_directory_index",
    "zarr_store_in_wrapper_folder",
    "discover_zarr_store_in_wrapper_folder",
]


def _rewrite_attrs(archive_dir: str, filename: str, rewrite: Callable[[list[dict[str, Any]]], None]) -> None:
    path = os.path.join(archive_dir, filename)
    with open(path) as f:
        attrs = json.load(f)
    rewrite(attrs)
    with open(path, "w") as f:
        json.dump(attrs, f)


@contextmanager
def _tamper_outputs_populated(tamper: Callable[[str], None]) -> Iterator[list[str]]:
    """Rewrite the model store a job wrote to ``metadata/outputs_populated`` before Galaxy imports it."""
    tampered: list[str] = []
    get_import_model_store_for_directory = store.get_import_model_store_for_directory

    def tampering_get_import_model_store_for_directory(archive_dir, **kwd):
        if archive_dir.endswith(os.path.join("metadata", "outputs_populated")):
            tamper(archive_dir)
            tampered.append(archive_dir)
        return get_import_model_store_for_directory(archive_dir, **kwd)

    with mock.patch.object(
        store, "get_import_model_store_for_directory", tampering_get_import_model_store_for_directory
    ):
        yield tampered


class TestExtendedMetadataIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["metadata_strategy"] = "extended"
        config["tool_evaluation_strategy"] = "remote"
        config["object_store_store_by"] = "uuid"
        config["retry_metadata_internally"] = False
        config["new_user_dataset_access_role_default_private"] = True

    def test_fetch_data_hda(self):
        history_id = self.dataset_populator.new_history()
        element = dict(src="files")
        target = {
            "destination": {"type": "hdas"},
            "elements": [element],
        }
        targets = [target]
        upload_content = "abcdef"
        payload = {"history_id": history_id, "targets": targets, "__files": {"files_0|file_data": upload_content}}
        new_dataset = self.dataset_populator.fetch(payload, assert_ok=True).json()["outputs"][0]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        content = self.dataset_populator.get_history_dataset_content(
            history_id=history_id,
            dataset_id=new_dataset["id"],
        )
        assert content == upload_content

    def test_fetched_list_elements_get_default_permissions(self, history_id):
        self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["a\n", "b\n"], direct_upload=True, wait=True
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        self.dataset_populator.assert_history_datasets_permissions(history_id, expected_count=2, access_private=True)

    def test_discovered_datasets_get_default_permissions(self, history_id):
        response = self.dataset_populator.run_tool("multi_output", {"input": 7}, history_id)
        self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
        self.dataset_populator.assert_history_datasets_permissions(history_id, expected_count=2, access_private=True)

    def test_all_output_types_get_default_permissions(self, history_id):
        response = self.dataset_populator.run_tool("all_output_types", {}, history_id)
        self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
        # 4 static outputs, discovered_output plus its discovered dataset, discovered_output_replaced,
        # the static pair's 2 elements, and discovered_list's element.
        self.dataset_populator.assert_history_datasets_permissions(history_id, expected_count=10, access_private=True)

    def test_dynamic_collection_elements_get_default_permissions(self, history_id):
        response = self.dataset_populator.run_tool(
            "collection_creates_dynamic_list_of_pairs", {"foo": "bar"}, history_id
        )
        self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
        self.dataset_populator.assert_history_datasets_permissions(history_id, expected_count=6, access_private=True)

    def test_unknown_output_extension_job_message(self, history_id):
        self._assert_unknown_datatype_job_message("discover_unknown_ext", history_id, "2 output datasets")

    def test_unknown_unnamed_output_extension_job_message(self, history_id):
        self._assert_unknown_datatype_job_message("unnamed_output_unknown_ext", history_id, "1 output dataset")
        (unnamed,) = self.dataset_populator.get_history_contents(history_id)
        assert unnamed["extension"] == "data"

    def _assert_unknown_datatype_job_message(self, tool_id: str, history_id: str, datasets: str) -> None:
        response = self.dataset_populator.run_tool(tool_id, {}, history_id)
        job_id = response["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id, assert_ok=True)
        job_messages = self.dataset_populator.get_job_details(job_id, full=True).json()["job_messages"]
        assert [message["desc"] for message in job_messages if message["type"] == "unknown_datatype"] == [
            f"Extension 'notadatatype' is not a datatype on this Galaxy server, {datasets} set to 'data'"
        ]

    def test_fetch_data_library(self):
        history_id, library, destination = self.library_populator.setup_fetch_to_folder("extended_metadata")
        items = [{"src": "files", "dbkey": "hg19", "info": "my cool bed", "created_from_basename": "4.bed"}]
        targets = [{"destination": destination, "items": items}]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
            "__files": {"files_0|file_data": open(self.test_data_resolver.get_filename("4.bed"))},
        }
        self.dataset_populator.fetch(payload, wait=True)
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["file_size"] == 61, dataset
        assert dataset["genome_build"] == "hg19", dataset
        assert dataset["misc_info"] == "my cool bed", dataset
        assert dataset["file_ext"] == "bed", dataset
        assert dataset["created_from_basename"] == "4.bed"

    def test_no_duplicate_elements_in_dynamic_list_output(self, history_id):
        """Run a tool with dynamic collection output and verify no duplicate elements."""
        response = self.dataset_populator.run_tool(
            "collection_creates_dynamic_list_of_pairs",
            {"foo": "bar"},
            history_id,
        )
        job_api_id = response["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_api_id, assert_ok=True)

        output_collections = response["output_collections"]
        hdca_details = self.dataset_populator.get_history_collection_details(
            history_id, content_id=output_collections[0]["id"]
        )

        sa_session = self._app.model.session
        hdca_id = self._app.security.decode_id(hdca_details["id"])
        hdca = sa_session.get(HistoryDatasetCollectionAssociation, hdca_id)
        assert hdca is not None
        dc = hdca.collection

        # Verify exactly 3 outer elements (samp1, samp2, samp3) - no duplicates
        outer_count = sa_session.scalar(
            select(func.count()).where(DatasetCollectionElement.dataset_collection_id == dc.id)
        )
        assert outer_count == 3, f"Expected 3 outer elements but found {outer_count}. Duplicate elements detected!"

        # Verify each inner pair has exactly 2 elements (forward, reverse)
        for element in dc.elements:
            assert element.child_collection is not None
            inner_count = sa_session.scalar(
                select(func.count()).where(
                    DatasetCollectionElement.dataset_collection_id == element.child_collection.id
                )
            )
            assert inner_count == 2, (
                f"Expected 2 inner elements for '{element.element_identifier}' "
                f"but found {inner_count}. Duplicate elements detected!"
            )

    def test_no_duplicate_elements_in_mapped_dynamic_collection(self, history_id):
        """Map a tool with dynamic collection output over a list and verify no duplicate elements."""
        # Create a list of 2 tabular datasets
        fetch_response = self.dataset_collection_populator.create_list_in_history(
            history_id,
            contents=["101\t1\n101\t2\n105\t3\n", "201\t10\n201\t20\n205\t30\n"],
            ext="tabular",
            wait=True,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        hdca_id = fetch_response.json()["output_collections"][0]["id"]

        # Map collection_split_on_column over the list
        inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
        }
        response = self.dataset_populator.run_tool(
            "collection_split_on_column",
            inputs,
            history_id,
        )

        # Wait for all mapping jobs to complete
        for job in response["jobs"]:
            self.dataset_populator.wait_for_job(job["id"], assert_ok=True)

        # The implicit output should be a list:list collection
        implicit_collections = response["implicit_collections"]
        assert len(implicit_collections) == 1
        implicit_hdca_details = self.dataset_populator.get_history_collection_details(
            history_id, content_id=implicit_collections[0]["id"]
        )

        sa_session = self._app.model.session
        implicit_hdca_id = self._app.security.decode_id(implicit_hdca_details["id"])
        implicit_hdca = sa_session.get(HistoryDatasetCollectionAssociation, implicit_hdca_id)
        assert implicit_hdca is not None
        outer_dc = implicit_hdca.collection

        # The outer collection should have exactly 2 elements (one per input)
        outer_count = sa_session.scalar(
            select(func.count()).where(DatasetCollectionElement.dataset_collection_id == outer_dc.id)
        )
        assert (
            outer_count == 2
        ), f"Expected 2 outer elements but found {outer_count}. Duplicate elements detected in mapped output!"

        # Each inner collection should have no duplicate elements
        for element in outer_dc.elements:
            inner_dc = element.child_collection
            assert inner_dc is not None, f"Inner collection for '{element.element_identifier}' is None"
            inner_count = sa_session.scalar(
                select(func.count()).where(DatasetCollectionElement.dataset_collection_id == inner_dc.id)
            )
            # Each input has 2 unique first-column values, so 2 split files
            assert (
                inner_count is not None and inner_count > 0
            ), f"Inner collection for '{element.element_identifier}' has no elements"
            # Check for duplicates: element_identifiers should be unique
            inner_elements = sa_session.scalars(
                select(DatasetCollectionElement).where(DatasetCollectionElement.dataset_collection_id == inner_dc.id)
            ).all()
            identifiers = [e.element_identifier for e in inner_elements]
            assert len(identifiers) == len(set(identifiers)), (
                f"Duplicate element identifiers found in inner collection "
                f"for '{element.element_identifier}': {identifiers}"
            )

    def test_no_duplicate_elements_in_mapped_static_collection(self, history_id):
        """Map a tool with a static collection output over a list and verify no duplicate elements.

        This covers the case where a tool declares a static collection output
        (e.g. paired with forward/reverse) and is mapped over a list input,
        producing a list:paired output. The per-job DC contains fully
        initialized elements and must be included in io_dicts for metadata
        serialization.
        """
        hdca = self.dataset_collection_populator.create_list_in_history(
            history_id,
            contents=["line1\nline2\nline3\nline4\n", "lineA\nlineB\nlineC\nlineD\n"],
            ext="txt",
            wait=True,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        hdca_id = hdca.json()["output_collections"][0]["id"]

        inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
        }
        response = self.dataset_populator.run_tool(
            "collection_creates_pair",
            inputs,
            history_id,
        )

        for job in response["jobs"]:
            self.dataset_populator.wait_for_job(job["id"], assert_ok=True)

        implicit_collections = response["implicit_collections"]
        assert len(implicit_collections) == 1
        implicit_hdca_details = self.dataset_populator.get_history_collection_details(
            history_id, content_id=implicit_collections[0]["id"]
        )

        sa_session = self._app.model.session
        implicit_hdca_id = self._app.security.decode_id(implicit_hdca_details["id"])
        implicit_hdca = sa_session.get(HistoryDatasetCollectionAssociation, implicit_hdca_id)
        assert implicit_hdca is not None
        outer_dc = implicit_hdca.collection

        # The outer collection should have exactly 2 elements (one per input)
        outer_count = sa_session.scalar(
            select(func.count()).where(DatasetCollectionElement.dataset_collection_id == outer_dc.id)
        )
        assert (
            outer_count == 2
        ), f"Expected 2 outer elements but found {outer_count}. Duplicate elements detected in mapped output!"

        # Each inner pair should have exactly 2 elements (forward, reverse) with no duplicates
        for element in outer_dc.elements:
            inner_dc = element.child_collection
            assert inner_dc is not None, f"Inner collection for '{element.element_identifier}' is None"
            inner_count = sa_session.scalar(
                select(func.count()).where(DatasetCollectionElement.dataset_collection_id == inner_dc.id)
            )
            assert inner_count == 2, (
                f"Expected 2 inner elements for '{element.element_identifier}' "
                f"but found {inner_count}. Duplicate elements detected!"
            )
            inner_elements = sa_session.scalars(
                select(DatasetCollectionElement).where(DatasetCollectionElement.dataset_collection_id == inner_dc.id)
            ).all()
            identifiers = [e.element_identifier for e in inner_elements]
            assert set(identifiers) == {
                "forward",
                "reverse",
            }, f"Expected forward/reverse but got {identifiers} for '{element.element_identifier}'"

    def test_remote_tool_eval_failure_surfaced_as_job_error(self):
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.run_tool("cheetah_problem_unbound_var", inputs={}, history_id=history_id)
            job_id = response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=False)
            job_details = self.dataset_populator.get_job_details(job_id, full=True).json()
            assert job_details["state"] == "error"
            output = self.dataset_populator.get_history_dataset_details(
                history_id=history_id, content_id=response["outputs"][0]["id"], assert_ok=False
            )
            assert "Galaxy failed to prepare this job, so the tool was not run" in output["misc_info"]
            assert "Error occurred while building command line" in output["misc_info"]
            assert "NotFound: cannot find 'out_file2'" in output["misc_info"]

    def test_purge_while_job_running(self):
        # The longer sleep keeps the job running while all outputs are purged.
        purge_while_job_running(
            self.dataset_populator, sleep_param=15, job_working_directory=self._job_working_directory
        )

    def _job_working_directory(self, job_id: str) -> str:
        job = self._app.model.session.get(Job, self._app.security.decode_id(job_id))
        return self._app.object_store.get_filename(job, base_dir="job_work", dir_only=True, obj_dir=True)


class TestExtendedMetadataSecurityIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["metadata_strategy"] = "extended"
        config["object_store_store_by"] = "uuid"
        config["retry_metadata_internally"] = False

    def test_tool_provided_metadata_cannot_collect_outside_working_directory(self):
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.run_tool(
                "tool_provided_metadata_security",
                inputs={},
                history_id=history_id,
            )
            job_id = response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=False)

            job_details_response = self.dataset_populator.get_job_details(job_id, full=True)
            job_details_response.raise_for_status()
            job_details = job_details_response.json()
            assert job_details["state"] == "error"
            assert "output_collection_security" in {
                message["type"] for message in (job_details.get("job_messages") or [])
            }

            history_contents = self.dataset_populator.get_history_contents(history_id)
            assert "outside working directory sentinel" not in {content["name"] for content in history_contents}

    def _run_tampered_job(
        self, history_id: str, tool_id: str | None, inputs: dict[str, Any], tamper: Callable[[str], None], **kwds
    ) -> dict[str, Any]:
        """Run a job whose ``outputs_populated`` is rewritten by ``tamper`` and check that Galaxy refuses it."""
        contents_before = {content["id"] for content in self.dataset_populator.get_history_contents(history_id)}
        with _tamper_outputs_populated(tamper) as tampered:
            response = self.dataset_populator.run_tool_raw(tool_id, inputs, history_id, **kwds).json()
            job_id = response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=False)
        assert len(tampered) == 1
        # Nothing the refused import created before the refusal is kept.
        new_contents = {content["id"] for content in self.dataset_populator.get_history_contents(history_id)}
        assert new_contents - contents_before == {
            output["id"] for output in response["outputs"] + response["output_collections"]
        }
        assert self.dataset_populator.get_job_details(job_id).json()["state"] == "error"
        for output in response["outputs"]:
            output = self.dataset_populator.get_history_dataset_details(
                history_id, content_id=output["id"], assert_ok=False
            )
            assert output["state"] == "error"
            assert "Model store may not" in output["misc_info"], output
        return response

    def _run_tampered_cat(self, history_id: str, tamper: Callable[[str], None]) -> dict[str, Any]:
        hda = self.dataset_populator.new_dataset(history_id, content="mine\n", wait=True)
        return self._run_tampered_job(history_id, "cat1", {"input1": {"src": "hda", "id": hda["id"]}}, tamper)

    def test_job_cannot_edit_another_users_dataset(self):
        with self._different_user_history() as other_history_id:
            victim = self.dataset_populator.new_dataset(other_history_id, content="victim\n", wait=True)
        victim_id = self._app.security.decode_id(victim["id"])

        def tamper(archive_dir):
            def rewrite(datasets_attrs):
                datasets_attrs[0].update(id=victim_id, name="pwned")
                datasets_attrs[0].pop("dataset", None)

            _rewrite_attrs(archive_dir, store.ATTRS_FILENAME_DATASETS, rewrite)

        with self.dataset_populator.test_history() as history_id:
            self._run_tampered_cat(history_id, tamper)

        with self._different_user():
            details = self.dataset_populator.get_history_dataset_details(other_history_id, content_id=victim["id"])
            assert details["name"] == victim["name"]
            content = self.dataset_populator.get_history_dataset_content(other_history_id, content_id=victim["id"])
            assert content == "victim\n"

    def test_job_cannot_edit_another_users_job(self):
        with self._different_user_history() as other_history_id:
            victim_hda = self.dataset_populator.new_dataset(other_history_id, content="victim\n", wait=True)
            victim_run = self.dataset_populator.run_tool(
                "cat1", inputs={"input1": {"src": "hda", "id": victim_hda["id"]}}, history_id=other_history_id
            )
            victim_job_id = victim_run["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(victim_job_id, assert_ok=True)
            victim_job = self.dataset_populator.get_job_details(victim_job_id, full=True).json()
            victim_outputs = self.dataset_populator.job_outputs(victim_job_id)

        def tamper(archive_dir):
            def rewrite(jobs_attrs):
                jobs_attrs[0].update(id=self._app.security.decode_id(victim_job_id), info="pwned", stdout="pwned")

            _rewrite_attrs(archive_dir, store.ATTRS_FILENAME_JOBS, rewrite)

        with self.dataset_populator.test_history() as history_id:
            # multi_output discovers a dataset, which the import creates before it refuses the job edit.
            self._run_tampered_job(history_id, "multi_output", {"input": 7}, tamper)

        with self._different_user():
            job = self.dataset_populator.get_job_details(victim_job_id, full=True).json()
            assert job["tool_stdout"] == victim_job["tool_stdout"] != "pwned"
            assert self.dataset_populator.job_outputs(victim_job_id) == victim_outputs

    def test_job_cannot_edit_another_users_collection(self):
        with self._different_user_history() as other_history_id:
            victim = self.dataset_collection_populator.create_list_in_history(
                other_history_id, contents=["a\n", "b\n"], wait=True
            ).json()["outputs"][0]
            victim_elements = self.dataset_populator.get_history_collection_details(
                other_history_id, content_id=victim["id"]
            )["elements"]
        victim_hdca = self._app.model.session.get(
            HistoryDatasetCollectionAssociation, self._app.security.decode_id(victim["id"])
        )
        assert victim_hdca
        victim_collection_id = victim_hdca.collection_id

        def tamper(archive_dir):
            def rewrite(collections_attrs):
                (hdca_attrs,) = collections_attrs
                hdca_attrs["collection"]["id"] = victim_collection_id

            _rewrite_attrs(archive_dir, store.ATTRS_FILENAME_COLLECTIONS, rewrite)

        with self.dataset_populator.test_history() as history_id:
            self._run_tampered_job(history_id, "collection_creates_dynamic_list_of_pairs", {"foo": "bar"}, tamper)

        with self._different_user():
            elements = self.dataset_populator.get_history_collection_details(other_history_id, content_id=victim["id"])[
                "elements"
            ]
            assert [(e["element_identifier"], e["object"]["id"]) for e in elements] == [
                (e["element_identifier"], e["object"]["id"]) for e in victim_elements
            ]

    def test_user_defined_tool_cannot_link_output_to_server_file(self):
        server_file = os.path.join(self._tempdir, "server_secret.txt")
        with open(server_file, "w") as f:
            f.write("server secret\n")

        def tamper(archive_dir):
            def rewrite(datasets_attrs):
                datasets_attrs[0]["dataset"]["external_filename"] = server_file

            _rewrite_attrs(archive_dir, store.ATTRS_FILENAME_DATASETS, rewrite)

        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            hda = self.dataset_populator.new_dataset(history_id, content="abc", wait=True)
            inputs = {"input": {"src": "hda", "id": hda["id"]}}
            # The restrictions on user-defined tools leave their untampered outputs alone.
            untampered = self.dataset_populator.run_tool_raw(
                None, inputs, history_id, tool_uuid=dynamic_tool["uuid"]
            ).json()
            self.dataset_populator.wait_for_job(untampered["jobs"][0]["id"], assert_ok=True)
            response = self._run_tampered_job(history_id, None, inputs, tamper, tool_uuid=dynamic_tool["uuid"])
            output_content = self.dataset_populator.get_history_dataset_content_raw(
                history_id, content_id=response["outputs"][0]["id"], assert_ok=False
            ).text
            assert "server secret" not in output_content


class TestExtendedMetadataDeferredIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["metadata_strategy"] = "extended"
        config["object_store_store_by"] = "uuid"
        config["retry_metadata_internally"] = False

    def test_deferred_upload_with_metadata_files(self, test_http_server):
        history_id = self.dataset_populator.new_history()
        uri = test_http_server.get_url(
            remote_url="https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bam",
            file_path="test-data/1.bam",
        )
        deferred_dataset = self.dataset_populator.create_deferred_hda(
            history_id=history_id,
            uri=uri,
            ext="bam",
        )
        inputs = {"input1": {"src": "hda", "id": deferred_dataset["id"]}}
        run_response = self.dataset_populator.run_tool("cat1", inputs=inputs, history_id=history_id)
        self.dataset_populator.wait_for_job(run_response["jobs"][0]["id"], assert_ok=True)
        bam_dataset = self.dataset_populator.get_history_dataset_details(
            history_id=history_id, content_id=run_response["outputs"][0]["id"]
        )
        assert bam_dataset["state"] == "ok"
        assert bam_dataset["extension"] == "bam"
        metadata_response = self._get(f"datasets/{bam_dataset['id']}/metadata_file?metadata_file=bam_index")
        metadata_response.raise_for_status()
        assert metadata_response.content.startswith(b"BAI")


class ExtendedMetadataIntegrationInstance(integration_util.IntegrationInstance):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["metadata_strategy"] = "extended"
        config["tool_evaluation_strategy"] = "remote"
        config["object_store_store_by"] = "uuid"
        config["retry_metadata_internally"] = False


instance = integration_util.integration_module_instance(ExtendedMetadataIntegrationInstance)

test_tools = integration_util.integration_tool_runner(TEST_TOOL_IDS)
