"""Zarr datasets created with their store in a wrapper folder must keep working after a metadata reset."""

from galaxy.model import HistoryDatasetAssociation
from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestZarrStoreRootMetadataResetIntegration(IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["metadata_strategy"] = "directory"

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_reset_metadata_keeps_a_wrapped_store_in_place(self, history_id):
        dataset_id = self._create_historical_zarr_dataset(history_id)
        # A copy shares the files of the dataset whose metadata is reset.
        copy_id = self._copy_dataset(history_id, dataset_id)

        self._put(f"histories/{history_id}/contents/{dataset_id}/validate").raise_for_status()
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

        hda = self._get_hda(dataset_id)
        assert hda.metadata.store_root == "wrapped.zarr"
        assert str(hda.metadata.zarr_format) == "2"
        preview = self._get(f"histories/{history_id}/contents/{dataset_id}/display?preview=true")
        preview.raise_for_status()
        assert "zarr_format" in preview.text
        for input_id in (dataset_id, copy_id):
            # Published wrappers read $input.extra_files_path/$input.metadata.store_root.
            assert ".zgroup" in self._run_and_read(history_id, "zarr_store_root_compat", input_id)
            # YAML tools get the store's folder as the path of a class: Directory input,
            # through the tool request API and through /api/tools alike.
            for listing in (
                self._request_and_read(history_id, "directory_or_file_user_defined", input_id),
                self._run_and_read(history_id, "directory_or_file_user_defined", input_id, input_name="input1"),
            ):
                assert ".zgroup" in listing
                assert "class=Directory" in listing

    def _run_and_read(self, history_id: str, tool_id: str, dataset_id: str, input_name: str = "input") -> list[str]:
        response = self.dataset_populator.run_tool(tool_id, {input_name: {"src": "hda", "id": dataset_id}}, history_id)
        self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
        content = self.dataset_populator.get_history_dataset_content(
            history_id, dataset_id=response["outputs"][0]["id"]
        )
        return content.splitlines()

    def _request_and_read(self, history_id: str, tool_id: str, dataset_id: str) -> list[str]:
        # The tool request API builds the runtime inputs of YAML tools from validated state.
        response = self.dataset_populator.tool_request_raw(
            tool_id, {"input1": {"src": "hda", "id": dataset_id}}, history_id
        )
        response.raise_for_status()
        assert self.dataset_populator.wait_on_tool_request(response.json()["tool_request_id"])
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return self.dataset_populator.get_history_dataset_content(history_id).splitlines()

    def _copy_dataset(self, history_id: str, dataset_id: str) -> str:
        response = self._post(
            f"histories/{history_id}/contents",
            data={"source": "hda", "content": dataset_id, "type": "dataset"},
            json=True,
        )
        response.raise_for_status()
        return response.json()["id"]

    def _create_historical_zarr_dataset(self, history_id: str) -> str:
        # A plain directory keeps the wrapper folder, which is how older Galaxy stored a zarr
        # dataset; mark it as such a dataset, with store_root naming the wrapper.
        with open(TestDataResolver().get_filename("wrapped_store.zarr.zip"), "rb") as archive:
            payload = {
                "history_id": history_id,
                "targets": [
                    {
                        "destination": {"type": "hdas"},
                        "items": [
                            {
                                "src": "pasted",
                                "paste_content": "",
                                "ext": "directory",
                                "extra_files": {"items_from": "archive", "src": "files", "fuzzy_root": False},
                            }
                        ],
                    }
                ],
                "__files": {"files_0|file_data": archive},
            }
            fetch_response = self.dataset_populator.fetch(payload)
        fetch_response.raise_for_status()
        dataset_id = fetch_response.json()["outputs"][0]["id"]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

        hda = self._get_hda(dataset_id)
        hda.extension = "zarr"
        hda._metadata = {**(hda._metadata or {}), "store_root": "wrapped.zarr"}
        self._app.model.session.commit()
        return dataset_id

    def _get_hda(self, dataset_id: str) -> HistoryDatasetAssociation:
        session = self._app.model.session
        session.expire_all()
        hda = session.get(HistoryDatasetAssociation, self._decode_id(dataset_id))
        assert hda
        return hda


class TestZarrStoreRootMetadataResetExtendedIntegration(TestZarrStoreRootMetadataResetIntegration):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["metadata_strategy"] = "extended"
