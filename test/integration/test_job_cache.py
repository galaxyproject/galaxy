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

    def test_job_cache_excludes_failed_metadata_hda(self):
        """Test that job cache lookup excludes HDAs in failed_metadata state.

        When an HDA is in failed_metadata state, even if a previous job ran
        successfully with that same HDA data, the cache should not be used
        because the HDA is now in an invalid state.
        """
        with self.dataset_populator.test_history() as history_id:
            # Create a dataset and run a job with it (this creates a cache entry)
            hda = self.dataset_populator.new_dataset(history_id, content="test content")
            hda_id = hda["id"]
            inputs = {"input1": {"src": "hda", "id": hda_id}}

            # Run the first job without cache - this creates the cache entry
            first_run = self.dataset_populator.run_tool(
                tool_id="cat1",
                inputs=inputs,
                history_id=history_id,
            )
            first_job_id = first_run["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(first_job_id)

            # Run the same job with caching enabled - should use cached job
            cached_run = self.dataset_populator.run_tool(
                tool_id="cat1",
                inputs=inputs,
                history_id=history_id,
                use_cached_job=True,
            )
            cached_job_id = cached_run["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(cached_job_id)

            # Verify job was cached (copied_from_job_id should be set)
            cached_job_details = self.dataset_populator.get_job_details(cached_job_id, full=True).json()
            assert cached_job_details["copied_from_job_id"] == first_job_id, "Second run should have used cached job"

            # Now set the input HDA to failed_metadata state
            database_id = self._get(f"configuration/decode/{hda_id}").json()["decoded_id"]
            hda_model = self.sa_session.scalar(
                select(HistoryDatasetAssociation).where(HistoryDatasetAssociation.id == database_id)
            )
            assert hda_model
            hda_model.state = HistoryDatasetAssociation.states.FAILED_METADATA
            self.sa_session.add(hda_model)
            self.sa_session.commit()

            # Run the same job again with caching enabled
            # This time, cache should NOT be used because input HDA is in failed_metadata state
            # The tool will also fail validation since the HDA is in an invalid state
            third_run = self.dataset_populator.run_tool_raw(
                tool_id="cat1",
                inputs=inputs,
                history_id=history_id,
                use_cached_job=True,
            ).json()

            # The response should contain an error since the HDA is in failed_metadata state
            # Most importantly, the cache should NOT have been used - if it were,
            # the job would have succeeded by copying from the cached job
            assert (
                "errors" in third_run and third_run["errors"]
            ), "Tool should fail when input HDA is in failed_metadata state"
            assert "failed_metadata" in str(third_run["errors"]), "Error should mention failed_metadata state"

    def test_job_cache_excludes_failed_metadata_hdca_element(self):
        """Test that job cache lookup excludes HDCAs with elements in failed_metadata state.

        When a leaf HDA in an HDCA is in failed_metadata state, the cache should
        not return a match for that collection.
        """
        with self.dataset_populator.test_history() as history_id:
            # Create a dataset collection with two elements
            create_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["content1\n", "content2\n"], wait=True
            ).json()
            hdca_id = create_response["output_collections"][0]["id"]

            # Get the first element's HDA ID
            hdca_details = self.dataset_populator.get_history_collection_details(history_id, content_id=hdca_id)
            first_element_hda_id = hdca_details["elements"][0]["object"]["id"]

            inputs = {"input1": {"src": "hdca", "id": hdca_id}}

            # Run the first job without cache - this creates the cache entry
            first_run = self.dataset_populator.run_tool(
                tool_id="cat_list",
                inputs=inputs,
                history_id=history_id,
            )
            first_job_id = first_run["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(first_job_id)

            # Run the same job with caching enabled - should use cached job
            cached_run = self.dataset_populator.run_tool(
                tool_id="cat_list",
                inputs=inputs,
                history_id=history_id,
                use_cached_job=True,
            )
            cached_job_id = cached_run["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(cached_job_id)

            # Verify job was cached (copied_from_job_id should be set)
            cached_job_details = self.dataset_populator.get_job_details(cached_job_id, full=True).json()
            assert cached_job_details["copied_from_job_id"] == first_job_id, "Second run should have used cached job"

            # Now set one of the collection element's HDA to failed_metadata state
            database_id = self._get(f"configuration/decode/{first_element_hda_id}").json()["decoded_id"]
            hda_model = self.sa_session.scalar(
                select(HistoryDatasetAssociation).where(HistoryDatasetAssociation.id == database_id)
            )
            assert hda_model
            hda_model.state = HistoryDatasetAssociation.states.FAILED_METADATA
            self.sa_session.add(hda_model)
            self.sa_session.commit()

            # Run the same job again with caching enabled
            # This time, cache should NOT be used because a leaf HDA is in failed_metadata state
            # The tool will also fail validation since one of the HDAs is in an invalid state
            third_run = self.dataset_populator.run_tool_raw(
                tool_id="cat_list",
                inputs=inputs,
                history_id=history_id,
                use_cached_job=True,
            ).json()

            # The response should contain an error since one of the HDAs is in failed_metadata state
            # Most importantly, the cache should NOT have been used - if it were,
            # the job would have succeeded by copying from the cached job
            assert (
                "errors" in third_run and third_run["errors"]
            ), "Tool should fail when HDCA element is in failed_metadata state"
            assert "failed_metadata" in str(third_run["errors"]), "Error should mention failed_metadata state"
