from sqlalchemy import select

from galaxy.model import HistoryDatasetAssociation
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util


class TestJobCacheFiltering(integration_util.IntegrationTestCase):
    """Integration tests for job cache filtering based on HDA state."""

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

    def _set_hda_to_failed_metadata(self, hda_id: str) -> None:
        """Set an HDA to failed_metadata state by its encoded ID."""
        database_id = self._get(f"configuration/decode/{hda_id}").json()["decoded_id"]
        hda_model = self.sa_session.scalar(
            select(HistoryDatasetAssociation).where(HistoryDatasetAssociation.id == database_id)
        )
        assert hda_model
        hda_model.state = HistoryDatasetAssociation.states.FAILED_METADATA
        self.sa_session.add(hda_model)
        self.sa_session.commit()

    def _run_and_verify_cache_hit(self, tool_id: str, inputs: dict, history_id: str) -> str:
        """Run a tool twice and verify the second run uses the cached job.

        Returns the first job ID for reference.
        """
        first_run = self.dataset_populator.run_tool(
            tool_id=tool_id,
            inputs=inputs,
            history_id=history_id,
        )
        first_job_id = first_run["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(first_job_id)

        cached_run = self.dataset_populator.run_tool(
            tool_id=tool_id,
            inputs=inputs,
            history_id=history_id,
            use_cached_job=True,
        )
        cached_job_id = cached_run["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(cached_job_id)

        cached_job_details = self.dataset_populator.get_job_details(cached_job_id, full=True).json()
        assert cached_job_details["copied_from_job_id"] == first_job_id, "Second run should have used cached job"

        return first_job_id

    def _verify_cache_excluded_with_failed_metadata(self, tool_id: str, inputs: dict, history_id: str) -> None:
        """Verify that cache is not used when input HDA is in failed_metadata state."""
        third_run = self.dataset_populator.run_tool_raw(
            tool_id=tool_id,
            inputs=inputs,
            history_id=history_id,
            use_cached_job=True,
        ).json()

        # Either the tool fails with an error (expected for failed_metadata input),
        # or the job runs without using cache (no copied_from_job_id)
        if "errors" in third_run and third_run["errors"]:
            assert "failed_metadata" in str(third_run["errors"]), "Error should mention failed_metadata state"
        else:
            # Job ran successfully - verify cache was NOT used
            job_id = third_run["jobs"][0]["id"]
            job_details = self.dataset_populator.get_job_details(job_id, full=True).json()
            assert job_details.get("copied_from_job_id") is None, "Cache should NOT be used for failed_metadata input"

    def test_job_cache_excludes_failed_metadata_hda(self):
        """Test that job cache lookup excludes HDAs in failed_metadata state.

        When an HDA is in failed_metadata state, even if a previous job ran
        successfully with that same HDA data, the cache should not be used
        because the HDA is now in an invalid state.
        """
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="test content")
            hda_id = hda["id"]
            inputs = {"input1": {"src": "hda", "id": hda_id}}

            self._run_and_verify_cache_hit("cat1", inputs, history_id)
            self._set_hda_to_failed_metadata(hda_id)
            self._verify_cache_excluded_with_failed_metadata("cat1", inputs, history_id)

    def test_job_cache_excludes_failed_metadata_hdca_element(self):
        """Test that job cache lookup excludes HDCAs with elements in failed_metadata state.

        When a leaf HDA in an HDCA is in failed_metadata state, the cache should
        not return a match for that collection.
        """
        with self.dataset_populator.test_history() as history_id:
            create_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["content1\n", "content2\n"], wait=True
            ).json()
            hdca_id = create_response["output_collections"][0]["id"]

            hdca_details = self.dataset_populator.get_history_collection_details(history_id, content_id=hdca_id)
            first_element_hda_id = hdca_details["elements"][0]["object"]["id"]

            inputs = {"input1": {"src": "hdca", "id": hdca_id}}

            self._run_and_verify_cache_hit("cat_list", inputs, history_id)
            self._set_hda_to_failed_metadata(first_element_hda_id)
            self._verify_cache_excluded_with_failed_metadata("cat_list", inputs, history_id)
