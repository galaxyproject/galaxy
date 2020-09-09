from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase


class TestProvenance(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_show_prov(self):
        history_id = self.dataset_populator.new_history()
        new_dataset1 = self.dataset_populator.new_dataset(history_id, content='for prov')
        prov_response = self._get("histories/{}/contents/{}/provenance".format(history_id, new_dataset1["id"]))
        self._assert_status_code_is(prov_response, 200)
        self._assert_has_keys(prov_response.json(), "job_id", "id", "stdout", "stderr", "parameters", "tool_id")
