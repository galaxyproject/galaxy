from typing import Optional
from uuid import uuid4

from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestHistoryArchivingWithExportRecord(IntegrationTestCase, UsesCeleryTasks, PosixFileSourceSetup):
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
        export_record = self._export_history_to_permanent_source(history_id, target_uri=target_uri)
        archive_response = self.dataset_populator.archive_history(
            history_id,
            export_record_id=export_record["id"],
            purge_history=True,
        )
        self._assert_status_code_is_ok(archive_response)

        archived_histories = self.dataset_populator.get_archived_histories(query=f"q=name-eq&qv={history_name}")
        assert len(archived_histories) == 1
        archived_history = archived_histories[0]
        assert archived_history["deleted"] is True
        assert archived_history["purged"] is True
        assert archived_history["archived"] is True
        assert archived_history["export_record_data"] is not None
        assert archived_history["export_record_data"]["target_uri"] == target_uri

    def _export_history_to_permanent_source(self, history_id: str, target_uri: Optional[str] = None):
        model_store_format = "rocrate.zip"
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
