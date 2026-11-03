"""Jobs on embedded Pulsar staging through the job files API with ``job_files_strict_access``."""

import contextlib
import os
import tempfile
from collections.abc import Iterator
from unittest.mock import patch

from sqlalchemy import select

from galaxy import model
from galaxy.job_execution.setup import (
    JobFilesManifest,
    JobWorkingDirectory,
    read_job_files_manifest,
)
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
    pulsar:
      runner: pulsar_embed
      default_file_action: remote_transfer
      remote_metadata: true
    pulsar_unstructured:
      runner: pulsar_embed
      default_file_action: remote_transfer
      remote_metadata: true
      # Pulsar's client scans the command for unstructured paths only when it rewrites paths itself.
      rewrite_parameters: false
      file_actions:
        paths:
          - path: {reference_directory}
            path_types: unstructured
            action: remote_transfer
            depth: 1

tools:
- class: user_defined
  environment: pulsar_unstructured
- id: metadata_bam
  environment: pulsar
- id: cat1
  environment: pulsar
"""


def _user_tool(tool_id: str, shell_command: str, input_format: str = "txt", output_format: str = "txt"):
    return UserToolSource(
        **{
            "class": "GalaxyUserTool",
            "id": tool_id,
            "name": tool_id,
            "version": "1.0.0",
            "container": "busybox",
            "shell_command": shell_command,
            "inputs": [{"type": "data", "name": "input", "format": input_format}],
            "outputs": [{"type": "data", "name": "output", "format": output_format, "from_work_dir": "output"}],
        }
    )


class TestJobFilesStrictAccessIntegration(integration_util.IntegrationTestCase):
    framework_tool_and_types = True
    dataset_populator: DatasetPopulator
    reference_directory: str
    reference_store: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        references = cls._test_driver.mkdtemp()
        cls.reference_directory = os.path.join(references, "ref")
        cls.reference_store = os.path.join(references, "store")
        os.makedirs(cls.reference_directory)
        os.makedirs(cls.reference_store)
        with open(os.path.join(cls.reference_store, "genome.fa"), "w") as f:
            f.write(">chrM\nACGT\n")
        os.symlink(os.path.join(cls.reference_store, "genome.fa"), os.path.join(cls.reference_directory, "genome.fa"))
        with open(os.path.join(cls.reference_directory, "genome.fa.fai"), "w") as f:
            f.write("chrM\t4\t6\t4\t5\n")
        os.makedirs(os.path.join(cls.reference_store, "sub"))
        os.symlink(os.path.join(cls.reference_store, "sub"), os.path.join(cls.reference_directory, "sub"))
        with open(os.path.join(cls.reference_store, "outside.txt"), "w") as f:
            f.write("outside\n")
        with tempfile.NamedTemporaryFile(suffix="_job_conf.yml", mode="w", delete=False) as job_conf:
            job_conf.write(JOB_CONF.format(reference_directory=cls.reference_directory))
        config["job_config_file"] = job_conf.name
        config["galaxy_infrastructure_url"] = "http://localhost:$GALAXY_WEB_PORT"
        config["metadata_strategy"] = "directory"
        config["enable_celery_tasks"] = False
        config["cleanup_job"] = "never"
        config["job_files_strict_access"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.test_data_resolver = TestDataResolver()

    def test_user_defined_tool_with_remote_metadata(self):
        tool = _user_tool("copy_bam", "cp '$(inputs.input.path)' output", "bam", "bam")
        with self.dataset_populator.test_history() as history_id:
            bam = self._new_bam(history_id)
            with self._record_job_files() as (reads, writes):
                job_id, output = self._run_user_tool(tool, bam["id"], history_id)
            assert self._input_path(bam["id"]) in reads
            assert any(f"{os.sep}metadata{os.sep}" in path for path in writes)
            assert set(reads) <= self._manifest(job_id).readable_paths
            assert output["metadata_bam_index"]
            assert output["file_size"] == bam["file_size"]

    def test_unstructured_reference_files(self):
        genome = os.path.join(self.reference_directory, "genome.fa")
        tool = _user_tool("cat_reference", f"cat '$(inputs.input.path)' {genome} > output")
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id, content="input\n", wait=True)
            with self._record_job_files() as (reads, _):
                job_id, output = self._run_user_tool(tool, dataset["id"], history_id)
            # ``depth: 1`` stages the reference's siblings too; the symlinked reference is served by its link's path.
            assert {genome, f"{genome}.fai"} <= set(reads)
            assert set(reads) <= self._manifest(job_id).readable_paths
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
            assert content == "input\n>chrM\nACGT\n"

    def test_unstructured_paths_stay_in_their_mapper(self):
        # Normalized, the path is inside the mapped directory; resolved through the symlink, it is outside.
        escaping = os.path.join(self.reference_directory, "sub", "..", "outside.txt")
        outside = os.path.realpath(os.path.join(self.reference_store, "outside.txt"))
        tool = _user_tool("cat_escaping", f"cat {escaping} > output")
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id, content="input\n", wait=True)
            with self._record_job_files(allow_refused=True) as (reads, _):
                job_id, _ = self._run_user_tool(tool, dataset["id"], history_id, assert_ok=False)
            manifest = self._manifest(job_id).readable_paths
            assert not any(os.path.realpath(path) == outside for path in [*manifest, *reads])

    def test_input_metadata_file(self):
        with self.dataset_populator.test_history() as history_id:
            bam = self._new_bam(history_id)
            with self._record_job_files() as (reads, _):
                run = self.dataset_populator.run_tool(
                    "metadata_bam", {"input_bam": {"src": "hda", "id": bam["id"]}, "ref_names": "chrM"}, history_id
                )
                self.dataset_populator.wait_for_job(run["jobs"][0]["id"], assert_ok=True)
            assert self._bam_index_path(bam["id"]) in reads

    def test_deferred_input(self):
        with self.dataset_populator.test_history() as history_id:
            deferred = self.dataset_populator.create_deferred_hda(history_id, "base64://ZGVmZXJyZWQK", ext="txt")
            with self._record_job_files() as (reads, _):
                run = self.dataset_populator.run_tool(
                    "cat1", {"input1": {"src": "hda", "id": deferred["id"]}}, history_id
                )
                self.dataset_populator.wait_for_job(run["jobs"][0]["id"], assert_ok=True)
            assert any(f"{os.sep}inputs{os.sep}" in path for path in reads)
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=run["outputs"][0])
            assert content == "deferred\n"

    def _run_user_tool(
        self, tool: UserToolSource, input_id: str, history_id: str, assert_ok: bool = True
    ) -> tuple[str, dict]:
        with self.dataset_populator.user_tool_execute_permissions():
            created = self.dataset_populator.create_unprivileged_tool(tool)
            response = self.dataset_populator.run_tool_raw(
                None, {"input": {"src": "hda", "id": input_id}}, history_id, tool_uuid=created["uuid"]
            )
            response.raise_for_status()
            run = response.json()
            job_id = run["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=assert_ok)
        output = self.dataset_populator.get_history_dataset_details(
            history_id, dataset_id=run["outputs"][0]["id"], assert_ok=assert_ok
        )
        return job_id, output

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

    def _manifest(self, encoded_job_id: str) -> JobFilesManifest:
        job = self._app.model.session.get(model.Job, self._app.security.decode_id(encoded_job_id))
        assert job
        manifest = read_job_files_manifest(JobWorkingDirectory(job, self._app.object_store).resolve())
        assert manifest
        return manifest

    @contextlib.contextmanager
    def _record_job_files(self, allow_refused: bool = False) -> Iterator[tuple[list[str], list[str]]]:
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
        assert allow_refused or not refused, refused
