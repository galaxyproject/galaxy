import os

import pytest

from galaxy.model.unittest_utils.store_fixtures import (
    deferred_hda_model_store_dict,
    deferred_hda_model_store_dict_bam,
    one_ld_library_deferred_model_store_dict,
    TEST_LIBRARY_NAME,
)
from galaxy.util import galaxy_directory
from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.populators import (
    DatasetPopulator,
    LibraryPopulator,
)
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestMaterializeDatasetInstanceTasaksIntegration(IntegrationTestCase, UsesCeleryTasks):
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        test_data_root = os.path.join(galaxy_directory(), "test-data")
        config["file_sources"] = [
            {
                "id": "testdatafiles",
                "type": "posix",
                "root": test_data_root,
            }
        ]

    def setUp(self):
        super().setUp()
        self.library_populator = LibraryPopulator(self.galaxy_interactor)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @pytest.mark.require_new_history
    def test_materialize_history_dataset(self, history_id: str):
        as_list = self.dataset_populator.create_contents_from_store(
            history_id,
            store_dict=deferred_hda_model_store_dict(),
        )
        assert len(as_list) == 1
        deferred_hda = as_list[0]
        assert deferred_hda["model_class"] == "HistoryDatasetAssociation"
        assert deferred_hda["state"] == "deferred"
        assert not deferred_hda["deleted"]
        self.dataset_populator.materialize_dataset_instance(history_id, deferred_hda["id"])
        self.dataset_populator.wait_on_history_length(history_id, 2)
        new_hda_details = self.dataset_populator.get_history_dataset_details(
            history_id, hid=2, assert_ok=False, wait=False
        )
        assert new_hda_details["model_class"] == "HistoryDatasetAssociation"
        assert new_hda_details["state"] == "ok"
        assert not new_hda_details["deleted"]

    @pytest.mark.require_new_history
    def test_materialize_gxfiles_uri(self, history_id: str):
        as_list = self.dataset_populator.create_contents_from_store(
            history_id,
            store_dict=deferred_hda_model_store_dict(source_uri="gxfiles://testdatafiles/2.bed"),
        )
        assert len(as_list) == 1
        deferred_hda = as_list[0]
        assert deferred_hda["model_class"] == "HistoryDatasetAssociation"
        assert deferred_hda["state"] == "deferred"
        assert not deferred_hda["deleted"]

        self.dataset_populator.materialize_dataset_instance(history_id, deferred_hda["id"])
        self.dataset_populator.wait_on_history_length(history_id, 2)
        new_hda_details = self.dataset_populator.get_history_dataset_details(
            history_id, hid=2, assert_ok=False, wait=False
        )
        assert new_hda_details["model_class"] == "HistoryDatasetAssociation"
        assert new_hda_details["state"] == "ok"
        assert not new_hda_details["deleted"]

    @pytest.mark.require_new_history
    def test_materialize_hash_failure(self, history_id: str):
        store_dict = deferred_hda_model_store_dict(source_uri="gxfiles://testdatafiles/2.bed")
        store_dict["datasets"][0]["file_metadata"]["hashes"][0]["hash_value"] = "invalidhash"
        as_list = self.dataset_populator.create_contents_from_store(history_id, store_dict=store_dict)
        assert len(as_list) == 1
        deferred_hda = as_list[0]
        assert deferred_hda["model_class"] == "HistoryDatasetAssociation"
        assert deferred_hda["state"] == "deferred"
        assert not deferred_hda["deleted"]

        self.dataset_populator.materialize_dataset_instance(history_id, deferred_hda["id"])
        self.dataset_populator.wait_on_history_length(history_id, 2)
        new_hda_details = self.dataset_populator.get_history_dataset_details(
            history_id, hid=2, assert_ok=False, wait=False
        )
        assert new_hda_details["model_class"] == "HistoryDatasetAssociation"
        assert new_hda_details["state"] == "error"
        assert not new_hda_details["deleted"]

    @pytest.mark.require_new_history
    def test_materialize_history_dataset_bam(self, history_id: str):
        as_list = self.dataset_populator.create_contents_from_store(
            history_id,
            store_dict=deferred_hda_model_store_dict_bam(),
        )

        assert len(as_list) == 1
        deferred_hda = as_list[0]
        assert deferred_hda["model_class"] == "HistoryDatasetAssociation"
        assert deferred_hda["state"] == "deferred"
        assert not deferred_hda["deleted"]

        # assert bam metadata and such deferred...
        deferred_hda_details = self.dataset_populator.get_history_dataset_details(
            history_id, hid=1, assert_ok=False, wait=False
        )
        assert ">chrM" not in deferred_hda_details["metadata_reference_names"]
        assert "metadata_bam_index" not in deferred_hda_details

        self.dataset_populator.materialize_dataset_instance(history_id, deferred_hda["id"])
        self.dataset_populator.wait_on_history_length(history_id, 2)
        new_hda_details = self.dataset_populator.get_history_dataset_details(
            history_id, hid=2, assert_ok=False, wait=False
        )
        assert new_hda_details["model_class"] == "HistoryDatasetAssociation"
        assert new_hda_details["state"] == "ok"
        assert not new_hda_details["deleted"]

        assert ">chrM" in new_hda_details["metadata_reference_names"]
        assert "metadata_bam_index" in new_hda_details

    @pytest.mark.require_new_history
    def test_materialize_library_dataset(self, history_id: str):
        response = self.library_populator.create_from_store(store_dict=one_ld_library_deferred_model_store_dict())
        assert isinstance(response, list)
        assert len(response) == 1
        library_summary = response[0]
        assert library_summary["name"] == TEST_LIBRARY_NAME
        assert "id" in library_summary
        ld = self.library_populator.get_library_contents_with_path(library_summary["id"], "/my cool name")
        assert ld
        self.dataset_populator.materialize_dataset_instance(history_id, ld["id"], "ldda")
        self.dataset_populator.wait_on_history_length(history_id, 1)
        new_hda_details = self.dataset_populator.get_history_dataset_details(
            history_id, hid=1, assert_ok=False, wait=False
        )
        assert new_hda_details["model_class"] == "HistoryDatasetAssociation"
        assert new_hda_details["state"] == "ok"
        assert not new_hda_details["deleted"]

    @pytest.mark.require_new_history
    def test_upload_vs_materialize_simplest_upload(self, history_id: str):
        item = {"src": "url", "url": "gxfiles://testdatafiles/simple_line_no_newline.txt", "ext": "txt"}
        output = self.dataset_populator.fetch_hda(history_id, item)
        uploaded_details = self.dataset_populator.get_history_dataset_details(
            history_id, dataset=output, assert_ok=True
        )
        assert "sources" in uploaded_details
        assert len(uploaded_details["sources"]) == 1
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output, assert_ok=True)
        assert content == "This is a line of text."
        new_history_id = self._reupload_and_then_materialize(history_id, output)
        content = self.dataset_populator.get_history_dataset_content(new_history_id, hid=2, assert_ok=False)
        assert content == "This is a line of text."

    @pytest.mark.require_new_history
    def test_upload_vs_materialize_to_posix_lines(self, history_id: str):
        item = {
            "src": "url",
            "url": "gxfiles://testdatafiles/simple_line_no_newline.txt",
            "ext": "txt",
            "to_posix_lines": True,
        }
        output = self.dataset_populator.fetch_hda(history_id, item)
        uploaded_details = self.dataset_populator.get_history_dataset_details(
            history_id, dataset=output, assert_ok=True
        )
        assert "sources" in uploaded_details
        sources = uploaded_details["sources"]
        assert len(sources) == 1
        source_0 = sources[0]
        assert "transform" in source_0
        transform = source_0["transform"]
        assert isinstance(transform, list)
        assert len(transform) == 1
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output, assert_ok=True)
        assert content == "This is a line of text.\n"
        new_history_id = self._reupload_and_then_materialize(history_id, output)
        content = self.dataset_populator.get_history_dataset_content(new_history_id, hid=2, assert_ok=False)
        assert content == "This is a line of text.\n"

    @pytest.mark.require_new_history
    def test_upload_vs_materialize_space_to_tab(self, history_id: str):
        item = {
            "src": "url",
            "url": "gxfiles://testdatafiles/simple_line_no_newline.txt",
            "ext": "txt",
            "space_to_tab": True,
        }
        output = self.dataset_populator.fetch_hda(history_id, item)
        uploaded_details = self.dataset_populator.get_history_dataset_details(
            history_id, dataset=output, assert_ok=True
        )
        assert "sources" in uploaded_details
        sources = uploaded_details["sources"]
        assert len(sources) == 1
        source_0 = sources[0]
        assert "transform" in source_0
        transform = source_0["transform"]
        assert isinstance(transform, list)
        assert len(transform) == 1
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output, assert_ok=True)
        assert content == "This\tis\ta\tline\tof\ttext."
        new_history_id = self._reupload_and_then_materialize(history_id, output)
        content = self.dataset_populator.get_history_dataset_content(new_history_id, hid=2, assert_ok=False)
        assert content == "This\tis\ta\tline\tof\ttext."

    @pytest.mark.require_new_history
    def test_upload_vs_materialize_to_posix_and_space_to_tab(self, history_id: str):
        item = {
            "src": "url",
            "url": "gxfiles://testdatafiles/simple_line_no_newline.txt",
            "ext": "txt",
            "space_to_tab": True,
            "to_posix_lines": True,
        }
        output = self.dataset_populator.fetch_hda(history_id, item)
        uploaded_details = self.dataset_populator.get_history_dataset_details(
            history_id, dataset=output, assert_ok=True
        )
        assert "sources" in uploaded_details
        sources = uploaded_details["sources"]
        assert len(sources) == 1
        source_0 = sources[0]
        assert "transform" in source_0
        transform = source_0["transform"]
        assert isinstance(transform, list)
        assert len(transform) == 2
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output, assert_ok=True)
        assert content == "This\tis\ta\tline\tof\ttext.\n"
        new_history_id = self._reupload_and_then_materialize(history_id, output)
        content = self.dataset_populator.get_history_dataset_content(new_history_id, hid=2, assert_ok=False)
        assert content == "This\tis\ta\tline\tof\ttext.\n"

    @pytest.mark.require_new_history
    def test_upload_vs_materialize_grooming(self, history_id: str):
        item = {
            "src": "url",
            "url": "gxfiles://testdatafiles/qname_sorted.bam",
            "ext": "bam",
        }
        output = self.dataset_populator.fetch_hda(history_id, item)
        uploaded_details = self.dataset_populator.get_history_dataset_details(
            history_id, dataset=output, assert_ok=True
        )
        assert "sources" in uploaded_details
        sources = uploaded_details["sources"]
        assert len(sources) == 1
        source_0 = sources[0]
        assert "transform" in source_0
        transform = source_0["transform"]
        assert isinstance(transform, list)
        assert len(transform) == 1
        original_details = self.dataset_populator.get_history_dataset_details(
            history_id, dataset=output, assert_ok=True
        )
        new_history_id = self._reupload_and_then_materialize(history_id, output)
        new_details = self.dataset_populator.get_history_dataset_details(new_history_id, hid=2, assert_ok=False)
        for key in original_details.keys():
            if key in ["metadata_bam_header", "metadata_bam_index"]:
                # differs because command-line different, index path different, and such...
                continue
            if key.startswith("metadata_"):
                assert original_details[key] == new_details[key], f"Mismatched on key {key}"
        assert original_details["file_ext"] == new_details["file_ext"]

    def _reupload_and_then_materialize(self, history_id, dataset):
        new_history_id, uploaded_hdas = self.dataset_populator.reupload_contents(dataset)
        assert len(uploaded_hdas) == 1
        deferred_hda = uploaded_hdas[0]
        assert deferred_hda["state"] == "deferred"

        self.dataset_populator.wait_on_history_length(new_history_id, 1)
        self.dataset_populator.materialize_dataset_instance(new_history_id, deferred_hda["id"])
        self.dataset_populator.wait_on_history_length(new_history_id, 2)
        return new_history_id
