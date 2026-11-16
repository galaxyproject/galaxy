"""Metadata files of outputs copied from another output: job cache hits and expression tool passthroughs."""

from pathlib import Path

from galaxy import model
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

TOOL_ID = "cat_data_and_sleep"


class RunsCachedBamJob(integration_util.IntegrationTestCase):
    """Base for integration tests that run a BAM job and then hit the job cache with it."""

    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _run_cached_bam_job(self, history_id: str, rename_input: bool = False) -> tuple[str, str]:
        """Run a BAM job, then run it again from the job cache.

        Returns the encoded ids of the source output and the cached output.
        """
        bam = self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver)
        inputs = {"input1": {"src": "hda", "id": bam["id"]}}
        source_run = self.dataset_populator.run_tool(TOOL_ID, inputs, history_id)
        source_job_id = source_run["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(source_job_id, assert_ok=True)
        if rename_input:
            # The search at submission requires matching input names, the search at job preparation doesn't.
            self.dataset_populator.rename_dataset(bam["id"])
        cached_run = self.dataset_populator.run_tool(TOOL_ID, inputs, history_id, use_cached_job=True)
        cached_job_id = cached_run["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(cached_job_id, assert_ok=True)
        cached_job = self.dataset_populator.get_job_details(cached_job_id, full=True).json()
        assert cached_job["copied_from_job_id"] == source_job_id
        return source_run["outputs"][0]["id"], cached_run["outputs"][0]["id"]

    def _hda(self, encoded_id: str) -> model.HistoryDatasetAssociation:
        session = self._app.model.session
        session.expire_all()
        hda = session.get(model.HistoryDatasetAssociation, self._app.security.decode_id(encoded_id))
        assert hda is not None
        return hda


class TestJobCacheMetadataFiles(RunsCachedBamJob):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["allow_path_paste"] = True

    def test_cache_hit_at_submission(self):
        history_id = self.dataset_populator.new_history()
        self._check_owns_copied_metadata_file(*self._run_cached_bam_job(history_id))

    def test_cache_hit_at_job_preparation(self):
        history_id = self.dataset_populator.new_history()
        self._check_owns_copied_metadata_file(*self._run_cached_bam_job(history_id, rename_input=True))

    def test_expression_tool_output_copied_from_input(self):
        history_id = self.dataset_populator.new_history()
        bam = self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver)
        self._check_owns_copied_metadata_file(bam["id"], self._pick_larger_file(history_id, bam["id"]))

    def test_expression_tool_output_copied_from_linked_input(self):
        history_id = self.dataset_populator.new_history()
        path = self.test_data_resolver.get_filename("1.bam")
        item = {"src": "path", "path": path, "ext": "bam", "link_data_only": True}
        payload = {"history_id": history_id, "targets": [{"destination": {"type": "hdas"}, "items": [item]}]}
        bam = self.dataset_populator.fetch(payload).json()["outputs"][0]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        assert self._hda(bam["id"]).dataset.external_filename == path
        self._check_owns_copied_metadata_file(bam["id"], self._pick_larger_file(history_id, bam["id"]))

    def _pick_larger_file(self, history_id: str, input_id: str) -> str:
        """Run an expression tool that outputs its input, and return the output's encoded id."""
        inputs = {"input1": {"src": "hda", "id": input_id}}
        run = self.dataset_populator.run_tool("expression_pick_larger_file", inputs, history_id)
        self.dataset_populator.wait_for_job(run["jobs"][0]["id"], assert_ok=True)
        return run["outputs"][0]["id"]

    def _check_owns_copied_metadata_file(self, source_id: str, copy_id: str) -> None:
        # Hold the HDAs: metadata keeps only a weak reference to its parent.
        source = self._hda(source_id)
        copy = self._hda(copy_id)
        source_index = source.metadata.bam_index
        copy_index = copy.metadata.bam_index
        assert isinstance(source_index, model.MetadataFile)
        assert isinstance(copy_index, model.MetadataFile)
        assert source_index.history_dataset is source
        assert copy_index.history_dataset is copy
        assert copy_index.id != source_index.id
        assert copy_index.get_file_name() != source_index.get_file_name()
        assert Path(copy_index.get_file_name()).read_bytes() == Path(source_index.get_file_name()).read_bytes()
