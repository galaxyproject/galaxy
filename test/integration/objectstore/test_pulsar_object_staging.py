"""Pulsar stages job inputs by object store identity (``object_store_staging``).

A job runs through embedded Pulsar with ``remote_transfer`` staging against a
boto3 object store backed by a disposable SeaweedFS container. The object store
cache is emptied after upload: if job preparation pulled the input back, or
staging read it from a path on Galaxy's disk, the checks below would fail.
"""

import os
import string
import time

import requests
from sqlalchemy import select

from galaxy import model
from galaxy.managers.job_object_staging import input_url
from galaxy.model.base import ensure_object_added_to_session
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from galaxy_test.driver.integration_util import docker_rm
from ._base import (
    BaseObjectStoreIntegrationTestCase,
    OBJECT_STORE_ACCESS_KEY,
    OBJECT_STORE_HOST,
    OBJECT_STORE_PORT,
    OBJECT_STORE_SECRET_KEY,
    start_seaweedfs,
)
from .test_direct_download_redirect import BOTO3_DIRECT_DOWNLOAD_CONFIG

JOB_CONF = string.Template("""
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
  default: pulsar_staged
  environments:
    local:
      runner: local
    pulsar_staged:
      runner: pulsar_embed
      default_file_action: remote_transfer
      rewrite_parameters: true
      remote_metadata: false
      object_store_staging: ${mode}

tools:
- class: local
  environment: local
""")

INPUT_CONTENT = "staged input\n"


@integration_util.skip_unless_docker()
class TestPulsarObjectStagingStream(BaseObjectStoreIntegrationTestCase):
    object_store_config = BOTO3_DIRECT_DOWNLOAD_CONFIG
    staging_mode = "stream"
    container_name: str
    object_store_cache_path: str
    dataset_populator: DatasetPopulator

    @classmethod
    def setUpClass(cls):
        cls.container_name = f"{cls.__name__}_container"
        start_seaweedfs(cls.container_name)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        docker_rm(cls.container_name)
        super().tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_store_cache_path = os.path.join(temp_directory, "object_store_cache")
        object_store_config_path = os.path.join(temp_directory, "object_store_conf.xml")
        with open(object_store_config_path, "w") as f:
            f.write(
                cls.object_store_config.safe_substitute(
                    temp_directory=temp_directory,
                    host=OBJECT_STORE_HOST,
                    port=OBJECT_STORE_PORT,
                    access_key=OBJECT_STORE_ACCESS_KEY,
                    secret_key=OBJECT_STORE_SECRET_KEY,
                )
            )
        config["object_store_config_file"] = object_store_config_path
        config["object_store_store_by"] = "uuid"
        job_config_path = os.path.join(temp_directory, "job_conf.yml")
        with open(job_config_path, "w") as f:
            f.write(JOB_CONF.substitute(mode=cls.staging_mode))
        config["job_config_file"] = job_config_path
        config["galaxy_infrastructure_url"] = "http://localhost:$GALAXY_WEB_PORT"

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_tool_input_is_staged_from_the_object_store(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content=INPUT_CONTENT, wait=True)
        self._reset_cache()

        run = self.dataset_populator.run_tool("cat1", {"input1": {"src": "hda", "id": hda["id"]}}, history_id)
        self.dataset_populator.wait_for_job(run["jobs"][0]["id"], assert_ok=True)

        output = self.dataset_populator.get_history_dataset_content(history_id, dataset=run["outputs"][0])
        assert output == INPUT_CONTENT
        # Staged by identity: the handler never pulled the input back into its cache.
        assert not os.path.exists(self._cache_path(hda))

    def test_bam_input_and_its_index_are_staged(self):
        # metadata_bam touches $input_bam.metadata.bam_index, so the index is staged as a metadata file.
        history_id = self.dataset_populator.new_history()
        with open(self.test_data_resolver.get_filename("3.bam"), "rb") as bam:
            hda = self.dataset_populator.new_dataset(history_id, content=bam, file_type="bam", wait=True)
        self._reset_cache()

        inputs = {"input_bam": {"src": "hda", "id": hda["id"]}, "ref_names": "chrM"}
        run = self.dataset_populator.run_tool("metadata_bam", inputs, history_id)
        self.dataset_populator.wait_for_job(run["jobs"][0]["id"], assert_ok=True)

        output = self.dataset_populator.get_history_dataset_content(history_id, dataset=run["outputs"][0])
        assert output.strip() == "chrM"
        assert not os.path.exists(self._cache_path(hda))

    def _hda(self, hda_dict) -> model.HistoryDatasetAssociation:
        hda = self._app.model.session.get(model.HistoryDatasetAssociation, self._app.security.decode_id(hda_dict["id"]))
        assert hda is not None and hda.dataset is not None
        return hda

    def _cache_path(self, hda_dict):
        return self._app.object_store.get_filename(self._hda(hda_dict).dataset, sync_cache=False)

    def _reset_cache(self):
        for root, _, files in os.walk(self.object_store_cache_path):
            for file_ in files:
                os.remove(os.path.join(root, file_))


@integration_util.skip_unless_docker()
class TestPulsarObjectStagingRedirect(TestPulsarObjectStagingStream):
    staging_mode = "redirect"

    def test_staging_url_redirects_to_the_object_store(self):
        history_id = self.dataset_populator.new_history()
        hda_dict = self.dataset_populator.new_dataset(history_id, content=INPUT_CONTENT, wait=True)
        self._reset_cache()
        hda = self._hda(hda_dict)
        assert hda.dataset is not None
        job = self._running_job_with_input(hda)
        expires = int(time.time()) + 3600
        url = input_url(
            self._app.security, self.url.rstrip("/"), job.id, "dataset", hda.dataset.id, expires, redirect=True
        )

        response = requests.get(url, allow_redirects=False)
        assert response.status_code == 302
        location = response.headers["Location"]
        assert OBJECT_STORE_HOST in location
        assert requests.get(location).text == INPUT_CONTENT
        assert not os.path.exists(self._cache_path(hda_dict))

    def _running_job_with_input(self, hda):
        """A job whose handler is unknown, so its state stays as set here."""
        sa_session = self._app.model.session
        job = model.Job()
        job.history = hda.history
        ensure_object_added_to_session(job, object_in_session=hda.history)
        job.user = sa_session.scalars(select(model.User)).first()
        job.handler = "unknown-handler"
        job.state = model.Job.states.RUNNING
        job.add_input_dataset("input1", hda)
        sa_session.add(job)
        sa_session.commit()
        return job
