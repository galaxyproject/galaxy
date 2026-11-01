"""Jobs whose job files are restricted, run on embedded Pulsar staging through the job files API."""

import contextlib
import os
import tempfile
from collections.abc import Iterator
from unittest.mock import patch

from sqlalchemy import select

from galaxy import model
from galaxy.job_execution.setup import restrict_job_files
from galaxy.managers.job_files import JobFilesManager
from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.tool_util_models import UserToolSource
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

JOB_CONF = """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
  pulsar_embed:
    load: galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner
    pulsar_app_config:
      tool_dependency_dir: none
      conda_auto_init: false
      conda_auto_install: false

execution:
  default: local
  environments:
    local:
      runner: local
    user_defined:
      runner: pulsar_embed
      default_file_action: remote_transfer
      remote_metadata: true
    strict:
      runner: pulsar_embed
      default_file_action: remote_transfer
      remote_metadata: true
      job_files_policy: strict
    strict_extended:
      runner: pulsar_embed
      default_file_action: remote_transfer
      remote_metadata: true
      job_files_policy: strict
      metadata_strategy: extended

tools:
- class: user_defined
  environment: user_defined
- id: metadata_bam
  environment: strict
- id: cat_data_and_sleep
  environment: strict_extended
"""

BAM_TOOL = UserToolSource(
    **{
        "class": "GalaxyUserTool",
        "id": "copy_bam",
        "name": "copy_bam",
        "version": "1.0.0",
        "container": "busybox",
        "shell_command": "cp '$(inputs.input.path)' output.bam",
        "inputs": [{"type": "data", "name": "input", "format": "bam"}],
        "outputs": [{"type": "data", "name": "output", "format": "bam", "from_work_dir": "output.bam"}],
    }
)


class TestRestrictedJobFilesIntegration(integration_util.IntegrationTestCase):
    framework_tool_and_types = True
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        with tempfile.NamedTemporaryFile(suffix="_job_conf.yml", mode="w", delete=False) as job_conf:
            job_conf.write(JOB_CONF)
        config["job_config_file"] = job_conf.name
        config["galaxy_infrastructure_url"] = "http://localhost:$GALAXY_WEB_PORT"
        config["metadata_strategy"] = "directory"
        config["enable_celery_tasks"] = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.test_data_resolver = TestDataResolver()

    def test_user_defined_tool_with_remote_metadata(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            tool = self.dataset_populator.create_unprivileged_tool(BAM_TOOL)
            bam = self._new_bam(history_id)
            with self._record_job_files() as (reads, writes):
                response = self.dataset_populator.run_tool_raw(
                    None, {"input": {"src": "hda", "id": bam["id"]}}, history_id, tool_uuid=tool["uuid"]
                )
                response.raise_for_status()
                run = response.json()
                self.dataset_populator.wait_for_job(run["jobs"][0]["id"], assert_ok=True)

            assert self._restricted(run["jobs"][0]["id"])
            assert self._input_path(bam["id"]) in reads
            assert any(f"{os.sep}metadata{os.sep}" in path for path in writes)
            output = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=run["outputs"][0]["id"])
            assert output["metadata_bam_index"]
            assert output["file_size"] == bam["file_size"]

    def test_strict_destination_stages_bam_index(self):
        with self.dataset_populator.test_history() as history_id:
            bam = self._new_bam(history_id)
            with self._record_job_files() as (reads, _):
                run = self.dataset_populator.run_tool(
                    "metadata_bam", {"input_bam": {"src": "hda", "id": bam["id"]}, "ref_names": "chrM"}, history_id
                )
                self.dataset_populator.wait_for_job(run["jobs"][0]["id"], assert_ok=True)
            assert self._restricted(run["jobs"][0]["id"])
            assert self._bam_index_path(bam["id"]) in reads

    def test_strict_destination_refuses_remote_extended_metadata(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id, content="abc\n", wait=True)
            run = self.dataset_populator.run_tool(
                "cat_data_and_sleep", {"input1": {"src": "hda", "id": dataset["id"]}, "sleep_time": 0}, history_id
            )
            job_id = run["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=False)
            assert self.dataset_populator.get_job_details(job_id).json()["state"] == "error"
            output = self.dataset_populator.get_history_dataset_details(
                history_id, dataset=run["outputs"][0], assert_ok=False
            )
            assert "Remote extended metadata is not supported" in output["misc_info"]

    def _new_bam(self, history_id: str) -> dict:
        with open(self.test_data_resolver.get_filename("3.bam"), "rb") as content:
            return self.dataset_populator.new_dataset(history_id, content=content, file_type="bam", wait=True)

    def _hda(self, encoded_hda_id: str) -> model.HistoryDatasetAssociation:
        hda = self._app.model.session.get(model.HistoryDatasetAssociation, self._app.security.decode_id(encoded_hda_id))
        assert hda
        return hda

    def _input_path(self, encoded_hda_id: str) -> str:
        return self._hda(encoded_hda_id).get_file_name()

    def _bam_index_path(self, encoded_hda_id: str) -> str:
        stmt = select(model.MetadataFile).filter_by(
            hda_id=self._app.security.decode_id(encoded_hda_id), name="bam_index"
        )
        return self._app.model.session.scalars(stmt).one().get_file_name()

    def _restricted(self, encoded_job_id: str) -> bool:
        job = self._app.model.session.get(model.Job, self._app.security.decode_id(encoded_job_id))
        assert job
        return restrict_job_files(job)

    @contextlib.contextmanager
    def _record_job_files(self) -> Iterator[tuple[list[str], list[str]]]:
        """Record the paths runners read and write, failing on any the job files API refuses."""
        reads: list[str] = []
        writes: list[str] = []
        refused: list[str] = []
        readable_path = JobFilesManager.readable_path
        authorize_write = JobFilesManager.authorize_write

        def record(method, paths):
            def recording(manager, encoded_job_id, path, job_key):
                try:
                    result = method(manager, encoded_job_id, path, job_key)
                except Exception as e:
                    refused.append(f"{path}: {e}")
                    raise
                paths.append(path)
                return result

            return recording

        with (
            patch.object(JobFilesManager, "readable_path", record(readable_path, reads)),
            patch.object(JobFilesManager, "authorize_write", record(authorize_write, writes)),
        ):
            yield reads, writes
        assert not refused, refused
