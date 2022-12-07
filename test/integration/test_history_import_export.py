import os
import tarfile
from uuid import uuid4

from galaxy.model.unittest_utils.store_fixtures import (
    deferred_hda_model_store_dict,
    history_model_store_dict,
    one_hda_model_store_dict,
)
from galaxy_test.api.test_histories import ImportExportTests
from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.api_asserts import assert_has_keys
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from galaxy_test.driver.integration_util import IntegrationTestCase


class ImportExportHistoryOutputsToWorkingDirIntegrationTestCase(ImportExportTests, IntegrationTestCase):
    task_based = False
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["outputs_to_working_directory"] = True
        config["metadata_strategy"] = "extended"

    def setUp(self):
        super().setUp()
        self._set_up_populators()


class ImportExportHistoryViaTasksIntegrationTestCase(
    ImportExportTests, IntegrationTestCase, UsesCeleryTasks, PosixFileSourceSetup
):
    task_based = True
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        PosixFileSourceSetup.handle_galaxy_config_kwds(config, cls)
        UsesCeleryTasks.handle_galaxy_config_kwds(config)
        cls.setup_ftp_config(config)

    @classmethod
    def setup_ftp_config(cls, config):
        ftp_dir = cls.temp_config_dir("ftp")
        os.makedirs(ftp_dir)
        config["ftp_upload_dir"] = ftp_dir
        config["ftp_upload_site"] = "ftp://cow.com"

    def setUp(self):
        super().setUp()
        self._set_up_populators()

    def test_import_from_model_store_async(self):
        async_history_name = "Model store imported history"
        store_dict = history_model_store_dict()
        store_dict["history"]["name"] = async_history_name
        response = self.dataset_populator.create_from_store_async(store_dict=store_dict)
        assert_has_keys(response, "id")
        self.dataset_populator.wait_for_history_with_name(
            async_history_name,
            "task based import history",
        )

    def test_import_model_store_from_file_source_async_with_format(self):
        history_name = f"for_export_format_async_{uuid4()}"
        history_id = self.dataset_populator.setup_history_for_export_testing(history_name)
        # Add bam dataset to test metadata generation on import
        self.dataset_populator.new_dataset(
            history_id, content=open(self.test_data_resolver.get_filename("1.bam"), "rb"), file_type="bam", wait=True
        )
        model_store_format = "tgz"  # Change to "rocrate.zip" when merging this forward and remove this comment, thanks!
        target_uri = f"gxfiles://posix_test/history.{model_store_format}"

        self.dataset_populator.export_history_to_uri_async(history_id, target_uri, model_store_format)
        self.dataset_populator.import_history_from_uri_async(target_uri, model_store_format)

        last_history = self._get("histories?limit=1").json()
        assert len(last_history) == 1
        imported_history = last_history[0]
        imported_history_id = imported_history["id"]
        assert imported_history_id != history_id
        assert imported_history["name"] == history_name
        self.dataset_populator.wait_for_history(imported_history_id)
        history_contents = self.dataset_populator.get_history_contents(imported_history_id)
        assert len(history_contents) == 3
        # Only deleted datasets should appear as "discarded"
        for dataset in history_contents:
            if dataset["deleted"] is True:
                assert dataset["state"] == "discarded"
            else:
                assert dataset["state"] == "ok"
                # Check metadata generation
            if dataset["extension"] == "bam":
                imported_bam_details = self.dataset_populator.get_history_dataset_details(
                    imported_history_id, dataset_id=dataset["id"]
                )
                bai_metadata = imported_bam_details["meta_files"][0]
                assert bai_metadata["file_type"] == "bam_index"

    def test_import_export_ftp(self):
        history_name = f"for_export_ftp_async_{uuid4()}"
        history_id = self.dataset_populator.setup_history_for_export_testing(history_name)

        model_store_format = "tgz"  # Change to "rocrate.zip" when merging this forward and remove this comment, thanks!
        target_uri = f"gxftp://history.{model_store_format}"

        self.dataset_populator.export_history_to_uri_async(history_id, target_uri, model_store_format)
        self.dataset_populator.import_history_from_uri_async(target_uri, model_store_format)

        last_history = self._get("histories?limit=1").json()
        assert len(last_history) == 1
        imported_history = last_history[0]
        imported_history_id = imported_history["id"]
        assert imported_history_id != history_id
        assert imported_history["name"] == history_name


class ImportExportHistoryContentsViaTasksIntegrationTestCase(IntegrationTestCase, UsesCeleryTasks):
    task_based = True
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self._set_up_populators()
        self.history_id = self.dataset_populator.new_history()

    def _set_up_populators(self):
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_export_and_imported_discarded(self):
        hda1 = self.dataset_populator.new_dataset(self.history_id, wait=True)

        second_history_id, as_list = self.dataset_populator.reupload_contents(hda1)

        assert len(as_list) == 1
        new_hda = as_list[0]
        assert new_hda["model_class"] == "HistoryDatasetAssociation"
        assert new_hda["state"] == "discarded"
        assert not new_hda["deleted"]

    def test_export_and_imported_discarded_bam(self):
        contents = self.dataset_populator.new_dataset(
            self.history_id,
            content=open(self.test_data_resolver.get_filename("1.bam"), "rb"),
            file_type="bam",
            wait=True,
        )
        second_history_id, as_list = self.dataset_populator.reupload_contents(contents)
        assert len(as_list) == 1
        new_hda = as_list[0]
        assert new_hda["model_class"] == "HistoryDatasetAssociation"
        assert new_hda["state"] == "discarded"
        assert not new_hda["deleted"]

    def test_import_as_discarded_from_dict(self):
        as_list = self.dataset_populator.create_contents_from_store(
            self.history_id,
            store_dict=one_hda_model_store_dict(
                include_source=False,
            ),
        )
        assert len(as_list) == 1
        new_hda = as_list[0]
        assert new_hda["model_class"] == "HistoryDatasetAssociation"
        assert new_hda["state"] == "discarded"
        assert not new_hda["deleted"]

        contents_response = self._get(f"histories/{self.history_id}/contents?v=dev")
        contents_response.raise_for_status()

    def test_import_as_deferred_from_discarded_with_source_dict(self):
        as_list = self.dataset_populator.create_contents_from_store(
            self.history_id,
            store_dict=one_hda_model_store_dict(
                include_source=True,
            ),
        )
        assert len(as_list) == 1
        new_hda = as_list[0]
        assert new_hda["model_class"] == "HistoryDatasetAssociation"
        assert new_hda["state"] == "deferred"
        assert not new_hda["deleted"]

        contents_response = self._get(f"histories/{self.history_id}/contents?v=dev")
        contents_response.raise_for_status()

    def test_export_and_imported_discarded_collection(self):
        create_response = self.dataset_collection_populator.create_list_in_history(
            history_id=self.history_id,
            direct_upload=True,
            wait=True,
        ).json()
        self.dataset_populator.wait_for_history(self.history_id)
        contents = create_response["outputs"][0]
        temp_tar = self.dataset_populator.download_contents_to_store(self.history_id, contents, "tgz")
        with tarfile.open(name=temp_tar) as tf:
            assert "datasets_attrs.txt" in tf.getnames()
            assert "collections_attrs.txt" in tf.getnames()

        second_history_id = self.dataset_populator.new_history()
        as_list = self.dataset_populator.create_contents_from_store(
            second_history_id,
            store_path=temp_tar,
        )
        as_list = self.dataset_populator.get_history_contents(second_history_id)
        assert len(as_list) == 4
        hdcas = [e for e in as_list if e["history_content_type"] == "dataset_collection"]
        assert len(hdcas) == 1

    def test_import_as_deferred_from_dict(self):
        as_list = self.dataset_populator.create_contents_from_store(
            self.history_id,
            store_dict=deferred_hda_model_store_dict(),
        )
        assert len(as_list) == 1
        new_hda = as_list[0]
        assert new_hda["model_class"] == "HistoryDatasetAssociation"
        assert new_hda["state"] == "deferred"
        assert not new_hda["deleted"]

        contents_response = self._get(f"histories/{self.history_id}/contents?v=dev")
        contents_response.raise_for_status()
