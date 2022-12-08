from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_tool,
)
from ._framework import ApiTestCase

MINIMAL_PROV_KEYS = ("id", "uuid")
OTHER_PROV_KEYS = ("job_id", "stdout", "stderr", "parameters", "tool_id")
ALL_PROV_KEYS = MINIMAL_PROV_KEYS + OTHER_PROV_KEYS


class TestProvenance(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @skip_without_tool("cat1")
    def test_get_prov(self):
        history_id = self.dataset_populator.new_history()
        new_dataset1_id = self.dataset_populator.new_dataset(history_id, content="for prov")["id"]
        inputs = {
            "input1": {"src": "hda", "id": new_dataset1_id},
        }
        run_response = self.dataset_populator.run_tool("cat1", inputs=inputs, history_id=history_id)
        output_hda_id = run_response["outputs"][0]["id"]
        prov_response = self._get(f"histories/{history_id}/contents/{output_hda_id}/provenance")
        self._assert_status_code_is(prov_response, 200)
        prov = prov_response.json()
        # Check the top-level provenance info
        self._assert_has_keys(prov, *ALL_PROV_KEYS)

        # Check that the provenance info is not recursive when `follow` is not specified
        prov_input1 = prov["parameters"]["input1"]
        self._assert_has_keys(prov_input1, *MINIMAL_PROV_KEYS)
        self._assert_not_has_keys(prov_input1, *OTHER_PROV_KEYS)

        # Check that the provenance info is also not recursive when `follow=False`
        prov_response = self._get(
            f"histories/{history_id}/contents/{output_hda_id}/provenance",
            {"follow": False},
        )
        self._assert_status_code_is(prov_response, 200)
        prov2 = prov_response.json()
        assert prov == prov2

        # Check that the provenance info is recursive when `follow=True`
        prov_response = self._get(
            f"histories/{history_id}/contents/{output_hda_id}/provenance",
            {"follow": True},
        )
        self._assert_status_code_is(prov_response, 200)
        prov = prov_response.json()
        self._assert_has_keys(prov, *ALL_PROV_KEYS)
        prov_input1 = prov["parameters"]["input1"]
        self._assert_has_keys(prov_input1, *ALL_PROV_KEYS)
