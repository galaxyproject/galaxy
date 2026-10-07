"""A dataset's uuid is chosen when Galaxy creates the dataset, not by the job that fills it.

With datasets stored by uuid, a uuid is where a dataset's file lives: a job that could
change its output's uuid could make it share another dataset's file.
"""

from uuid import uuid4

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

OTHER_CONTENT = "other content\n"


class TestRequestedUuids(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["object_store_store_by"] = "uuid"
        config["retry_metadata_internally"] = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_upload_gets_the_uuid_it_requested(self, history_id):
        uuid = str(uuid4())
        response = self._upload(history_id, "content\n", uuid)
        assert response.status_code == 200, response.text
        output = response.json()["outputs"][0]
        self.dataset_populator.wait_for_job(response.json()["jobs"][0]["id"], assert_ok=True)
        assert self._details(history_id, output)["uuid"] == uuid

    def test_upload_requesting_a_uuid_in_use_is_refused(self, history_id):
        other = self.dataset_populator.new_dataset(history_id, content=OTHER_CONTENT, wait=True)
        response = self._upload(history_id, "content\n", self._details(history_id, other)["uuid"])
        assert response.status_code == 400, response.text
        assert self._content(history_id, other) == OTHER_CONTENT

    def test_upload_requesting_an_invalid_uuid_is_refused(self, history_id):
        response = self._upload(history_id, "content\n", "not-a-uuid")
        assert response.status_code == 400, response.text

    def test_tool_cannot_change_its_outputs_uuid(self, history_id):
        run = self.dataset_populator.run_tool("tool_provided_metadata_uuid", {"uuid": str(uuid4())}, history_id)
        output = run["outputs"][0]
        self.dataset_populator.wait_for_job(run["jobs"][0]["id"], assert_ok=True)
        # The uuid Galaxy gave the output when it created it, before the job ran.
        assert self._details(history_id, output)["uuid"] == output["uuid"]

    def test_tool_cannot_take_another_datasets_uuid(self, history_id):
        other = self.dataset_populator.new_dataset(history_id, content=OTHER_CONTENT, wait=True)
        other_uuid = self._details(history_id, other)["uuid"]
        run = self.dataset_populator.run_tool("tool_provided_metadata_uuid", {"uuid": other_uuid}, history_id)
        self.dataset_populator.wait_for_job(run["jobs"][0]["id"])
        assert self._content(history_id, other) == OTHER_CONTENT
        assert self._details(history_id, run["outputs"][0])["uuid"] != other_uuid

    def _upload(self, history_id, content, uuid):
        payload = self.dataset_populator.upload_payload(history_id, content, extra_inputs={"files_0|uuid": uuid})
        return self.dataset_populator.tools_post(payload)

    def _details(self, history_id, dataset):
        return self.dataset_populator.get_history_dataset_details(history_id, dataset=dataset, assert_ok=False)

    def _content(self, history_id, dataset):
        return self.dataset_populator.get_history_dataset_content(history_id, dataset=dataset, wait=False)


class TestRequestedUuidsExtendedMetadata(TestRequestedUuids):
    """The metadata script runs with the job and writes outputs to the object store itself."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["metadata_strategy"] = "extended"
        config["tool_evaluation_strategy"] = "remote"
