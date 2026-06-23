from sqlalchemy import select

from galaxy.model import HistoryDatasetAssociation
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util


class TestFailJobWhenToolUnavailable(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator
    require_admin_user = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    @property
    def sa_session(self):
        return self._app.model.session

    def test_partial_job_success_error_handling(self):
        with self.dataset_populator.test_history() as history_id:
            create_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["xxx\n", "yyy\n"], wait=True
            ).json()
            hdca_id = create_response["output_collections"][0]["id"]
            first_hda_id = self.dataset_populator.get_history_collection_details(history_id, content_id=hdca_id)[
                "elements"
            ][0]["object"]["id"]
            database_id = self._get(f"configuration/decode/{first_hda_id}").json()["decoded_id"]
            hda = self.sa_session.scalar(
                select(HistoryDatasetAssociation).where(HistoryDatasetAssociation.id == database_id)
            )
            assert hda
            hda.state = HistoryDatasetAssociation.states.FAILED_METADATA
            self.sa_session.add(hda)
            self.sa_session.commit()
            response = self.dataset_populator.run_tool_raw(
                tool_id="__FILTER_NULL__",
                inputs={"input": {"src": "hdca", "id": hdca_id}},
                history_id=history_id,
            ).json()
            assert response["errors"] == [
                {
                    "err_code": 0,
                    "err_msg": "Tool requires inputs to be in valid state, but "
                    "dataset with hid 2 is in state 'failed_metadata'",
                    "id": "eb142648ac45b77086610f67617bec2ad3808fd4409d175f",
                    "input_name": "input1",
                    "src": "hda",
                }
            ]
