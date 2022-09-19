import json
import os

from galaxy.model.store.load_objects import main
from galaxy.model.unittest_utils.store_fixtures import (
    history_model_store_dict,
    one_hda_model_store_dict,
    TEST_HISTORY_NAME,
)
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase


class ModelStoreScriptsIntegrationTestCase(IntegrationTestCase):
    # TODO: test build_objects also...

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.json_store_path = os.path.join(self._tempdir, "store.json")

    def test_import_contents_from_json(self):
        self._write_store_json(one_hda_model_store_dict())
        history_id = self.dataset_populator.new_history()
        script_args = ["-t", history_id, "-u", self.url, "-k", self.galaxy_interactor.api_key, self.json_store_path]
        main(script_args)

    def test_import_history_from_json(self):
        self._write_store_json(history_model_store_dict())
        script_args = ["-u", self.url, "-k", self.galaxy_interactor.api_key, self.json_store_path]
        history_names = [h["name"] for h in self.dataset_populator.get_histories()]
        assert TEST_HISTORY_NAME not in history_names
        main(script_args)
        history_names = [h["name"] for h in self.dataset_populator.get_histories()]
        assert TEST_HISTORY_NAME in history_names

    def _write_store_json(self, as_dict) -> None:
        with open(self.json_store_path, "w") as f:
            json.dump(as_dict, f)
