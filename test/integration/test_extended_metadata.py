"""Integration tests for the Pulsar embedded runner."""
from galaxy_test.base.populators import (
    DatasetPopulator,
    LibraryPopulator,
)
from galaxy_test.driver import integration_util

TEST_TOOL_IDS = [
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
]


class ExtendedMetadataIntegrationTestCase(integration_util.IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
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


class ExtendedMetadataDeferredIntegrationTestCase(integration_util.IntegrationTestCase):
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
