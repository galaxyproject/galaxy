from typing import Optional
from uuid import uuid4

from galaxy.schema.schema import ModelStoreFormat
from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestHistoryArchivingWithExportRecord(IntegrationTestCase, UsesCeleryTasks, PosixFileSourceSetup):
    dataset_populator: DatasetPopulator
    task_based = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        PosixFileSourceSetup.handle_galaxy_config_kwds(config, cls)
        UsesCeleryTasks.handle_galaxy_config_kwds(config)

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_archive_history_with_export_record_purges_history(self):
        history_name = f"for_archiving_{uuid4()}"
        history_id = self.dataset_populator.setup_history_for_export_testing(history_name)
        history = self._get(f"histories/{history_id}").json()
        assert history["deleted"] is False
        assert history["purged"] is False
        assert history["archived"] is False

        target_uri = f"gxfiles://posix_test/history_{history_id}"
        export_record = self._export_history_to_permanent_storage(history_id, target_uri=target_uri)
        archive_response = self.dataset_populator.archive_history(
            history_id,
            export_record_id=export_record["id"],
            purge_history=True,
        )
        self._assert_status_code_is_ok(archive_response)

        archived_history = self._get_archived_history_with_name(history_name)
        assert archived_history["deleted"] is True
        assert archived_history["purged"] is True
        assert archived_history["archived"] is True
        assert archived_history["export_record_data"] is not None
        assert archived_history["export_record_data"]["target_uri"] == target_uri

    def test_archive_history_does_not_purge_history_with_export_record_but_purge_history_false(self):
        history_name = f"for_archiving_{uuid4()}"
        history_id = self.dataset_populator.setup_history_for_export_testing(history_name)
        history = self._get(f"histories/{history_id}").json()
        assert history["deleted"] is False
        assert history["purged"] is False
        assert history["archived"] is False

        target_uri = f"gxfiles://posix_test/history_{history_id}"
        export_record = self._export_history_to_permanent_storage(history_id, target_uri=target_uri)
        archive_response = self.dataset_populator.archive_history(
            history_id,
            export_record_id=export_record["id"],
            purge_history=False,
        )
        self._assert_status_code_is_ok(archive_response)

        archived_history = self._get_archived_history_with_name(history_name)
        assert archived_history["deleted"] is False
        assert archived_history["purged"] is False
        assert archived_history["archived"] is True
        assert archived_history["export_record_data"] is not None
        assert archived_history["export_record_data"]["target_uri"] == target_uri

    def test_archive_history_does_not_purge_history_without_export_record(self):
        history_name = f"for_archiving_{uuid4()}"
        history_id = self.dataset_populator.setup_history_for_export_testing(history_name)
        history = self._get(f"histories/{history_id}").json()
        assert history["deleted"] is False
        assert history["purged"] is False
        assert history["archived"] is False

        archive_response = self.dataset_populator.archive_history(history_id, purge_history=True)
        self._assert_status_code_is(archive_response, 400)
        assert "Cannot purge history without an export record" in archive_response.json()["err_msg"]

    def test_archive_history_with_invalid_export_record_fails(self):
        history_name = f"for_archiving_failure_{uuid4()}"
        history_id = self.dataset_populator.setup_history_for_export_testing(history_name)
        history = self._get(f"histories/{history_id}").json()
        assert history["archived"] is False

        archive_response = self.dataset_populator.archive_history(history_id, export_record_id="invalid")
        self._assert_status_code_is(archive_response, 400)
        assert "Invalid id" in archive_response.json()["err_msg"]

        # Only export records belonging to the history can be used to archive the history.
        other_history_id = self.dataset_populator.new_history(name=f"other_{uuid4()}")
        target_uri = f"gxfiles://posix_test/history_{other_history_id}"
        other_export_record = self._export_history_to_permanent_storage(other_history_id, target_uri=target_uri)
        archive_response = self.dataset_populator.archive_history(
            history_id, export_record_id=other_export_record["id"]
        )
        self._assert_status_code_is(archive_response, 400)
        assert "The given archive export record does not belong to this history" in archive_response.json()["err_msg"]

        # Only permanent export records can be used to archive the history.
        export_record = self._export_history_to_short_term_storage(history_id)
        archive_response = self.dataset_populator.archive_history(history_id, export_record_id=export_record["id"])
        self._assert_status_code_is(archive_response, 400)
        assert "The given archive export record is temporal" in archive_response.json()["err_msg"]

        history = self._get(f"histories/{history_id}").json()
        assert history["archived"] is False

    def test_restore_archived_history_with_export_record_and_purged(self):
        history_name = f"for_restoring_{uuid4()}"
        history_id = self.dataset_populator.setup_history_for_export_testing(history_name)

        target_uri = f"gxfiles://posix_test/history_{history_id}"
        export_record = self._export_history_to_permanent_storage(history_id, target_uri=target_uri)
        archive_response = self.dataset_populator.archive_history(
            history_id,
            export_record_id=export_record["id"],
            purge_history=True,
        )
        self._assert_status_code_is_ok(archive_response)

        # Trying to restore an archived (and purged) history with an export record should fail by default
        archived_history = self._get_archived_history_with_name(history_name)
        restore_response = self.dataset_populator.restore_archived_history(archived_history["id"])
        self._assert_status_code_is(restore_response, 400)
        assert (
            "Cannot restore an archived (and purged) history that is associated with an archive export record"
            in restore_response.json()["err_msg"]
        )

        # Trying to restore an archived (and purged) history with an export record should succeed if the force flag is set
        restore_response = self.dataset_populator.restore_archived_history(archived_history["id"], force=True)
        restored_history = self._get(f"histories/{history_id}").json()
        assert restored_history["archived"] is False
        # But of course, restoring the history this way will not change the fact that the history is still purged
        assert restored_history["deleted"] is True
        assert restored_history["purged"] is True

    def test_restore_archived_history_with_export_record_and_not_purged(self):
        history_name = f"for_restoring_{uuid4()}"
        history_id = self.dataset_populator.setup_history_for_export_testing(history_name)

        target_uri = f"gxfiles://posix_test/history_{history_id}"
        export_record = self._export_history_to_permanent_storage(history_id, target_uri=target_uri)
        archive_response = self.dataset_populator.archive_history(
            history_id,
            export_record_id=export_record["id"],
            purge_history=False,
        )
        self._assert_status_code_is_ok(archive_response)
        archived_history = self._get_archived_history_with_name(history_name)
        assert archived_history["archived"] is True
        assert archived_history["export_record_data"] is not None
        assert archived_history["export_record_data"]["target_uri"] == target_uri

        # Trying to restore an archived (non-purged) history with an export record should succeed without the force flag
        restore_response = self.dataset_populator.restore_archived_history(archived_history["id"])
        self._assert_status_code_is_ok(restore_response)
        restored_history = self._get(f"histories/{history_id}").json()
        assert restored_history["archived"] is False
        assert restored_history["deleted"] is False
        assert restored_history["purged"] is False

    def test_reimport_history_copy_from_archive_export_record(self):
        history_name = f"for_reimporting_{uuid4()}"
        history_id = self.dataset_populator.setup_history_for_export_testing(history_name)

        model_store_format = ModelStoreFormat.ROCRATE_ZIP
        target_uri = f"gxfiles://posix_test/history_{history_id}"
        export_record = self._export_history_to_permanent_storage(
            history_id, target_uri=target_uri, model_store_format=model_store_format
        )
        archive_response = self.dataset_populator.archive_history(
            history_id,
            export_record_id=export_record["id"],
            purge_history=True,
        )
        self._assert_status_code_is_ok(archive_response)
        archived_history = self._get_archived_history_with_name(history_name)
        assert archived_history["purged"] is True
        assert archived_history["archived"] is True
        assert archived_history["export_record_data"] is not None
        assert archived_history["export_record_data"]["target_uri"] == target_uri

        # Re-importing the history from the export record data should succeed
        self.dataset_populator.import_history_from_uri_async(
            target_uri=target_uri, model_store_format=model_store_format
        )
        last_history = self._get("histories?limit=1").json()
        assert len(last_history) == 1
        imported_history = last_history[0]
        imported_history_id = imported_history["id"]
        assert imported_history_id != history_id
        assert imported_history["name"] == history_name
        assert imported_history["deleted"] is False
        assert imported_history["purged"] is False
        self.dataset_populator.wait_for_history(imported_history_id)
        history_contents = self.dataset_populator.get_history_contents(imported_history_id)
        assert len(history_contents) == 2
        for dataset in history_contents:
            if dataset["deleted"] is True:
                assert dataset["state"] == "discarded"
                assert dataset["purged"] is True
            else:
                assert dataset["state"] == "ok"
                assert dataset["purged"] is False

    def _get_archived_history_with_name(self, history_name: str):
        archived_histories = self.dataset_populator.get_archived_histories(query=f"q=name-eq&qv={history_name}")
        assert len(archived_histories) == 1
        archived_history = archived_histories[0]
        return archived_history

    def _export_history_to_permanent_storage(
        self,
        history_id: str,
        target_uri: Optional[str] = None,
        model_store_format: ModelStoreFormat = ModelStoreFormat.ROCRATE_ZIP,
    ):
        target_uri = (
            f"gxfiles://posix_test/history_{history_id}.{model_store_format}" if target_uri is None else target_uri
        )
        self.dataset_populator.export_history_to_uri_async(history_id, target_uri, model_store_format)
        export_records = self.dataset_populator.get_history_export_tasks(history_id)
        assert len(export_records) == 1
        last_record = export_records[0]
        self.dataset_populator.wait_for_export_task_on_record(last_record)
        assert last_record["ready"] is True
        return last_record

    def _export_history_to_short_term_storage(self, history_id):
        self.dataset_populator.download_history_to_store(history_id)
        export_records = self.dataset_populator.get_history_export_tasks(history_id)
        assert len(export_records) == 1
        last_record = export_records[0]
        self.dataset_populator.wait_for_export_task_on_record(last_record)
        assert last_record["ready"] is True
        return last_record
