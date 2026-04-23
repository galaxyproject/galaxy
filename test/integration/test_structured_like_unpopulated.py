"""Integration test for ToolInputsNotReady on structured_like/unpopulated input.

When a tool output is ``structured_like="<non-mapped collection input>"`` and
the user maps the tool over an empty collection, implicit output collection
precreation consults that input to determine output shape. If the referenced
collection is still populating, we should raise ``ToolInputsNotReadyException``
(HTTP 400, ``TOOL_INPUTS_NOT_READY``) rather than surfacing the cryptic
"Referenced input parameter is not a collection." (Sentry issue GALAXY-MAIN-4KSCZZZ0015NC).

This test deterministically produces an unpopulated DatasetCollection by
downgrading ``populated_state`` directly in the DB after the collection has
been created via the standard fetch path — the only reliable way to simulate
the race-window state from pure API tests.
"""

from sqlalchemy import select

from galaxy.model import (
    DatasetCollection,
    HistoryDatasetCollectionAssociation,
)
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util


class TestStructuredLikeUnpopulatedRaisesNotReady(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

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

    def _mark_collection_unpopulated(self, hdca_id: str) -> None:
        hdca_db_id = self._get(f"configuration/decode/{hdca_id}").json()["decoded_id"]
        # HDCA.collection_id points at the DatasetCollection row we need.
        hdca_model = self.sa_session.scalar(
            select(HistoryDatasetCollectionAssociation).where(HistoryDatasetCollectionAssociation.id == hdca_db_id)
        )
        assert hdca_model is not None
        dc_model = hdca_model.collection
        dc_model.populated_state = DatasetCollection.populated_states.NEW
        self.sa_session.add(dc_model)
        self.sa_session.commit()

    def test_unpopulated_structured_like_target_raises_not_ready(self):
        with self.dataset_populator.test_history() as history_id:
            empty_hdca = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=[], direct_upload=True, wait=True
            ).json()["output_collections"][0]

            shape_response = self.dataset_collection_populator.create_pair_in_history(
                history_id, contents=["a", "b"], direct_upload=True, wait=True
            ).json()
            shape_hdca = shape_response["output_collections"][0]

            # Simulate upstream "still populating" — mirrors what
            # happens when the referenced collection is an implicit
            # collection whose producing jobs haven't finished yet.
            self._mark_collection_unpopulated(shape_hdca["id"])

            inputs = {
                "input1": {"batch": True, "values": [{"src": "hdca", "id": empty_hdca["id"]}]},
                "shape": {"src": "hdca", "id": shape_hdca["id"]},
            }
            response = self.dataset_populator.run_tool_raw(
                tool_id="collection_mapped_over_empty_structured_like",
                inputs=inputs,
                history_id=history_id,
            )

            # Expect HTTP 400 (ToolInputsNotReadyException) with the
            # same message meta.py raises for mapped-over unpopulated
            # HDCAs, not the cryptic "Referenced input parameter..."
            # that used to reach Sentry.
            assert response.status_code == 400, (
                f"Expected 400 for unpopulated input collection, got {response.status_code}: {response.text}"
            )
            assert "not populated" in response.text, f"Expected 'not populated' in error body, got: {response.text}"
            assert (
                "Referenced input parameter is not a collection" not in response.text
            ), "Regression: old cryptic error surfaced instead of ToolInputsNotReady"
