"""Integration tests for the persistence directories of embedded Pulsar apps."""

import os
import uuid

from galaxy import model
from galaxy.jobs.runners.pulsar import (
    active_job_index_entries,
    EMBEDDED_PULSAR_PERSISTENCE_DIRECTORY,
    migrate_embedded_pulsar_persistence,
    PersistenceEntryMigration,
)
from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on,
)
from galaxy_test.driver import integration_util

PULSAR_APP_CONFIG = {
    "tool_dependency_dir": "none",
    "conda_auto_init": False,
    "conda_auto_install": False,
}


class TestEmbeddedPulsarPersistenceDirectory(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    persistence_root: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.persistence_root = cls._test_driver.mkdtemp()
        config.pop("job_config_file", None)
        config["job_config"] = {
            "runners": {
                "local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"},
                "pulsar_default": {
                    "load": "galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner",
                    "pulsar_app_config": dict(PULSAR_APP_CONFIG),
                },
                "pulsar_placeholder": {
                    "load": "galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner",
                    "pulsar_app_config": {
                        **PULSAR_APP_CONFIG,
                        "persistence_directory": os.path.join(cls.persistence_root, "persisted", "{server_name}"),
                    },
                },
            },
            "execution": {
                "default": "pulsar_default",
                "environments": {
                    "local": {"runner": "local"},
                    "pulsar_default": {"runner": "pulsar_default"},
                    "pulsar_placeholder": {"runner": "pulsar_placeholder"},
                },
            },
            "tools": [
                {"id": "upload1", "environment": "local"},
                {"id": "cat_data_and_sleep", "environment": "pulsar_placeholder"},
            ],
        }

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_default_persistence_directory_is_per_server(self, history_id: str) -> None:
        shared_directory = os.path.join(self._app.config.data_dir, EMBEDDED_PULSAR_PERSISTENCE_DIRECTORY)
        job_id = self._run_sleep_job(history_id, sleep_time=5)
        entry = self._wait_for_active_job_entry(os.path.join(shared_directory, self._app.config.server_name), job_id)

        self.dataset_populator.wait_for_job(job_id, assert_ok=True)
        assert not os.path.exists(entry)
        assert active_job_index_entries(shared_directory) == []

    def test_server_name_placeholder_in_persistence_directory(self, history_id: str) -> None:
        dataset = self.dataset_populator.new_dataset(history_id, content="1\n", wait=True)
        job_id = self.dataset_populator.run_tool(
            "cat_data_and_sleep",
            {"input1": {"src": "hda", "id": dataset["id"]}, "sleep_time": 5},
            history_id,
        )["jobs"][0]["id"]
        persisted = os.path.join(self.persistence_root, "persisted")
        self._wait_for_active_job_entry(os.path.join(persisted, self._app.config.server_name), job_id)

        self.dataset_populator.wait_for_job(job_id, assert_ok=True)
        assert os.listdir(persisted) == [self._app.config.server_name]

    def test_migrate_shared_persistence_directory(self, history_id: str) -> None:
        server_name = self._app.config.server_name
        finished_job_id = self._run_sleep_job(history_id, sleep_time=0)
        self.dataset_populator.wait_for_job(finished_job_id, assert_ok=True)
        running_job_id = self._run_sleep_job(history_id, sleep_time=10)
        self._wait_for_active_job_entry(
            os.path.join(self._app.config.data_dir, EMBEDDED_PULSAR_PERSISTENCE_DIRECTORY, server_name), running_job_id
        )

        source = os.path.join(self.persistence_root, "shared")
        running = self._touch(source, "_default_-active-jobs", self._decode(running_job_id))
        finished = self._touch(source, "_default_-postprocessing-jobs", self._decode(finished_job_id))
        unknown = self._touch(source, "_default_-active-jobs", "999999999")
        uuid_id = self._touch(source, "_default_-active-jobs", uuid.uuid4().hex)
        no_handler = self._touch(source, "_default_-active-jobs", self._create_job(model.Job.states.QUEUED, None))
        uuid_job_external_id = self._create_job(model.Job.states.RUNNING, server_name, uuid.uuid4().hex)
        uuid_job = self._touch(source, "_default_-active-jobs", uuid_job_external_id)
        moved_to = os.path.join(source, server_name, "_default_-active-jobs", self._decode(running_job_id))
        uuid_job_moved_to = os.path.join(source, server_name, "_default_-active-jobs", uuid_job_external_id)
        expected = sorted(
            [
                PersistenceEntryMigration(running, moved_to),
                PersistenceEntryMigration(uuid_job, uuid_job_moved_to),
                PersistenceEntryMigration(finished, None, "job is ok"),
                PersistenceEntryMigration(unknown, None, "no Galaxy job with this id"),
                PersistenceEntryMigration(uuid_id, None, "no Galaxy job with this id"),
                PersistenceEntryMigration(no_handler, None, "job has no handler"),
            ],
            key=lambda migration: migration.entry,
        )
        target = os.path.join(source, "{server_name}")
        session = self._app.model.session

        assert migrate_embedded_pulsar_persistence(session, source, target, dry_run=True) == expected
        assert not os.path.exists(moved_to)
        assert migrate_embedded_pulsar_persistence(session, source, target) == expected
        assert os.path.exists(moved_to)
        assert os.path.exists(uuid_job_moved_to)
        assert not os.path.exists(running)
        assert active_job_index_entries(source) == sorted([finished, unknown, uuid_id, no_handler])

        self.dataset_populator.wait_for_job(running_job_id, assert_ok=True)

    def _run_sleep_job(self, history_id: str, sleep_time: int) -> str:
        return self.dataset_populator.run_tool("galaxy_json_sleep", {"sleep_time": sleep_time}, history_id)["jobs"][0][
            "id"
        ]

    def _create_job(self, state: str, handler: str | None, external_id: str | None = None) -> str:
        job = model.Job()
        job.tool_id = "galaxy_json_sleep"
        job.state = state
        job.handler = handler
        job.job_runner_external_id = external_id
        session = self._app.model.session
        session.add(job)
        session.commit()
        return external_id or str(job.id)

    def _decode(self, job_id: str) -> str:
        return str(self._app.security.decode_id(job_id))

    def _wait_for_active_job_entry(self, persistence_directory: str, job_id: str) -> str:
        entry = os.path.join(persistence_directory, "_default_-active-jobs", self._decode(job_id))
        wait_on(lambda: True if os.path.exists(entry) else None, f"Pulsar active job entry {entry}", timeout=60)
        return entry

    @staticmethod
    def _touch(directory: str, index_name: str, job_id: str) -> str:
        path = os.path.join(directory, index_name, job_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()
        return path
