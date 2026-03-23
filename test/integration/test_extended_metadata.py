"""Integration tests for the Pulsar embedded runner."""

from sqlalchemy import (
    func,
    select,
)

from galaxy.model import (
    DatasetCollectionElement,
    HistoryDatasetCollectionAssociation,
)
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    LibraryPopulator,
)
from galaxy_test.driver import integration_util
from .objectstore._purged_handling import purge_while_job_running

TEST_TOOL_IDS = [
    "from_work_dir_glob",
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
    "create_directory_index",
]


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

    def test_purge_while_job_running(self):
        # pass extra_sleep, since templating the command line will fail if the output
        # is deleted before remote_tool_eval runs.
        purge_while_job_running(self.dataset_populator, extra_sleep=10)


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

    def test_deferred_upload_with_metadata_files(self):
        history_id = self.dataset_populator.new_history()
        deferred_dataset = self.dataset_populator.create_deferred_hda(
            history_id=history_id,
            uri="https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bam",
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
