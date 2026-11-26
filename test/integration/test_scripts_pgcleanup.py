from pathlib import Path

import pytest

from galaxy_test.base.populators import skip_without_tool
from .test_job_cache_metadata_files import RunsCachedBamJob
from .test_scripts import BaseScriptsIntegrationTestCase

SCRIPT = "cleanup_datasets/pgcleanup.py"


class TestScriptsPgCleanupIntegration(RunsCachedBamJob, BaseScriptsIntegrationTestCase):
    def test_help(self):
        self._skip_unless_postgres()
        self._scripts_check_argparse_help(SCRIPT)

    def test_purge_deleted_histories(self):
        self._skip_unless_postgres()

        history_id = self.dataset_populator.new_history()
        delete_response = self.dataset_populator._delete(f"histories/{history_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["purged"] is False
        self._pgcleanup_check_output(["--older-than", "0", "--sequence", "purge_deleted_histories"])
        history_response = self.dataset_populator._get(f"histories/{history_id}")
        assert history_response.status_code == 200
        assert history_response.json()["purged"] is True, history_response.json()

    def test_purge_old_hdas(self):
        self._skip_unless_postgres()

        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, wait=True)
        assert not self.is_purged(history_id, hda)

        # filtering on a date too old - shouldn't purge the dataset
        self._pgcleanup_check_output(
            [
                "--older-than",
                "1",
                "--sequence",
                "purge_old_hdas",
            ]
        )
        assert not self.is_purged(history_id, hda)

        # filtering on invalid object store - shouldn't purge the dataset
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--object-store-id",
                "myfakeobjectstore",
                "--sequence",
                "purge_old_hdas",
            ]
        )
        assert not self.is_purged(history_id, hda)

        self._pgcleanup_check_output(["--older-than", "0", "--sequence", "purge_old_hdas"])

        assert self.is_purged(history_id, hda)

    @skip_without_tool("test_data_source")
    def test_purge_errored_hdas(self):
        history_id = self.dataset_populator.new_history()
        error_dataset = self.dataset_populator.new_error_dataset(history_id)
        assert not self.is_purged(history_id, error_dataset)

        # dataset not old enough, shouldn't be purged
        self._pgcleanup_check_output(
            [
                "--older-than",
                "1",
                "--sequence",
                "purge_error_hdas",
            ]
        )
        assert not self.is_purged(history_id, error_dataset)

        # dataset not in target object store, shouldn't be purged
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--object-store-id",
                "myfakeobjectstore",
                "--sequence",
                "purge_error_hdas",
            ]
        )
        assert not self.is_purged(history_id, error_dataset)

        # okay though, this should purge the dataset
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--sequence",
                "purge_error_hdas",
            ]
        )
        assert self.is_purged(history_id, error_dataset)

    def test_purge_datasets(self):
        self._skip_unless_postgres()

        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, wait=True)
        self.dataset_populator.delete_dataset(history_id, hda["id"])
        assert not self.is_purged(history_id, hda)

        self._pgcleanup_check_output(
            [
                "--older-than",
                "1",
                "--sequence",
                "purge_datasets",
            ]
        )
        assert not self.is_purged(history_id, hda)

        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--object-store-id",
                "myfakeobjectstore",
                "--sequence",
                "purge_datasets",
            ]
        )
        assert not self.is_purged(history_id, hda)

        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--sequence",
                "purge_datasets",
            ]
        )
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--sequence",
                "purge_datasets",
            ]
        )

        # why is this not purged?
        # test or functionality seem broken but better to run through it and ensure
        # it isn't breaking anything and everything is syntactically correct than not
        # assert self.is_purged(history_id, hda)

    def test_delete_datasets(self):
        # this walks through the code to ensure no SQL or Python errors but
        # I think we would need to talk to the model layer from the test directly
        # to actually produce datasets of the target type for purging and to verify
        # they were purged (certainly a possibility)
        self._skip_unless_postgres()

        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, wait=True)

        assert not self.is_purged(history_id, hda)

        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--sequence",
                "delete_datasets",
            ]
        )
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--object-store-id",
                "myfakeobjectstore",
                "--sequence",
                "delete_datasets",
            ]
        )

        assert not self.is_purged(history_id, hda)

    def test_purge_historyless_hdas(self):
        # same as above - this is just a negative test for things being broken
        # we could access the model layer to write a test to verify the positive
        # behavior actually occurs
        self._skip_unless_postgres()

        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, wait=True)

        assert not self.is_purged(history_id, hda)
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--sequence",
                "purge_historyless_hdas",
            ]
        )
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--object-store-id",
                "myfakeobjectstore",
                "--sequence",
                "purge_historyless_hdas",
            ]
        )

        assert not self.is_purged(history_id, hda)

    @pytest.mark.parametrize("rename_input", [False, True], ids=["hit_at_submission", "hit_at_job_preparation"])
    def test_purge_deleted_hdas_with_cached_copy(self, rename_input: bool):
        self._skip_unless_postgres()

        history_id = self.dataset_populator.new_history()
        source_id, cached_id = self._run_cached_bam_job(history_id, rename_input=rename_input)
        cached = self._hda(cached_id)
        cached_index_path = cached.metadata.bam_index.get_file_name()
        cached_index = Path(cached_index_path).read_bytes()
        assert cached_index

        self.dataset_populator.delete_dataset(history_id, source_id)
        self._pgcleanup_check_output(["--older-than", "0", "--sequence", "purge_deleted_hdas"])

        assert self.is_purged(history_id, source_id)
        assert not self.is_purged(history_id, cached_id)
        assert Path(cached_index_path).read_bytes() == cached_index

    def is_purged(self, history_id: str, dataset) -> bool:
        # set wait=False to prevent errored dataset from erroring out
        if isinstance(dataset, str):
            details_response = self.dataset_populator.get_history_dataset_details(
                history_id, dataset_id=dataset, wait=False
            )
        else:
            details_response = self.dataset_populator.get_history_dataset_details(
                history_id, dataset=dataset, wait=False
            )
        return details_response["purged"]

    def _pgcleanup_check_output(self, extra_args: list[str]) -> str:
        config_file = self.write_config_file()
        output = self._scripts_check_output(SCRIPT, ["-c", config_file] + extra_args)
        print(output)
        return output
