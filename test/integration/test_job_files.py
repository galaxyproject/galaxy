"""Warning - this is hard to test.

This is a terrible API to test - the state of what is allowed is
highly dependent on the state of the job - which Galaxy typically
tries to get running and finish ASAP. Additionally, what is allowed
is very dependent on Galaxy internals about how the job working
directory is structured.

An ideal test would be to run Pulsar and Galaxy on different disk
and different servers and have them talk to each other - but this
still wouldn't test security stuff.

As a result this test is highly coupled with internals in a way most
integration tests avoid - but @jmchilton's fear of not touching this
API has gone too far.
"""

import io
import os
import tempfile
from typing import Dict

import requests
from sqlalchemy import select
from tusclient import client

from galaxy import model
from galaxy.model.base import ensure_object_added_to_session
from galaxy_test.base import api_asserts
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
SIMPLE_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "simple_job_conf.xml")

TEST_INPUT_TEXT = "test input content\n"
TEST_FILE_IO = io.StringIO("some initial text data")
TEST_TUS_CHUNK_SIZE = 1024


class TestJobFilesIntegration(integration_util.IntegrationTestCase):
    initialized = False
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = SIMPLE_JOB_CONFIG_FILE
        config["object_store_store_by"] = "uuid"
        config["server_name"] = "files"
        cls.initialized = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        if not TestJobFilesIntegration.initialized:
            history_id = self.dataset_populator.new_history()
            sa_session = self.sa_session
            stmt = select(model.HistoryDatasetAssociation)
            assert len(sa_session.scalars(stmt).all()) == 0
            self.input_hda_dict = self.dataset_populator.new_dataset(history_id, content=TEST_INPUT_TEXT, wait=True)
            assert len(sa_session.scalars(stmt).all()) == 1
            self.input_hda = sa_session.scalars(stmt).all()[0]
            TestJobFilesIntegration.initialized = True

    def test_read_by_state(self):
        job, _, _ = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        data = {"path": self.input_hda.get_file_name(), "job_key": job_key}
        get_url = self._api_url(f"jobs/{job_id}/files", use_key=True)
        head_response = requests.head(get_url, params=data)
        api_asserts.assert_status_code_is_ok(head_response)
        assert head_response.text == ""
        assert head_response.headers["content-length"] == str(len(TEST_INPUT_TEXT))
        response = requests.get(get_url, params=data)
        api_asserts.assert_status_code_is_ok(response)
        assert response.text == TEST_INPUT_TEXT

        # set job state to finished and ensure the file is no longer
        # readable
        self._change_job_state(job, "ok")

        get_url = self._api_url(f"jobs/{job_id}/files", use_key=True)
        response = requests.get(get_url, params=data)
        _assert_insufficient_permissions(response)

    def test_read_fails_if_input_file_purged(self):
        job, _, _ = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        input_file_path = self.input_hda.get_file_name()
        data = {"path": input_file_path, "job_key": job_key}
        get_url = self._api_url(f"jobs/{job_id}/files", use_key=True)
        head_response = requests.head(get_url, params=data)
        api_asserts.assert_status_code_is_ok(head_response)
        delete_response = self.dataset_populator.delete_dataset(
            self.input_hda_dict["history_id"], content_id=self.input_hda_dict["id"], purge=True, wait_for_purge=True
        )
        assert delete_response.status_code == 200
        head_response = requests.get(get_url, params=data)
        assert head_response.status_code == 400
        assert head_response.json()["err_msg"] == "Input dataset(s) for job have been purged."

    def test_write_by_state(self):
        job, output_hda, working_directory = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        path = self._app.object_store.get_filename(output_hda.dataset)
        assert path
        data = {"path": path, "job_key": job_key}

        def files():
            return {"file": io.StringIO("some initial text data")}

        post_url = self._api_url(f"jobs/{job_id}/files", use_key=False)
        response = requests.post(post_url, data=data, files=files())
        api_asserts.assert_status_code_is_ok(response)
        assert open(path).read() == "some initial text data"

        work_dir_file = os.path.join(working_directory, "work")
        data = {"path": work_dir_file, "job_key": job_key}
        response = requests.post(post_url, data=data, files=files())
        api_asserts.assert_status_code_is_ok(response)
        assert open(work_dir_file).read() == "some initial text data"

        # set job state to finished and ensure the file is no longer
        # readable
        self._change_job_state(job, "ok")

        response = requests.post(post_url, data=data, files=files())
        _assert_insufficient_permissions(response)

    def test_write_with_tus(self):
        # shared setup with above test
        job, output_hda, _ = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        path = self._app.object_store.get_filename(output_hda.dataset)
        assert path

        upload_url = self._api_url(f"job_files/resumable_upload?job_key={job_key}", use_key=False)
        headers: Dict[str, str] = {}
        my_client = client.TusClient(upload_url, headers=headers)

        storage = None
        metadata: Dict[str, str] = {}
        t_file = tempfile.NamedTemporaryFile("w")
        t_file.write("some initial text data")
        t_file.flush()

        input_path = t_file.name

        uploader = my_client.uploader(input_path, metadata=metadata, url_storage=storage)
        uploader.chunk_size = TEST_TUS_CHUNK_SIZE
        uploader.upload()
        upload_session_url = uploader.url
        assert upload_session_url
        tus_session_id = upload_session_url.rsplit("/", 1)[1]  # type: ignore[unreachable]

        data = {"path": path, "job_key": job_key, "session_id": tus_session_id}
        post_url = self._api_url(f"jobs/{job_id}/files", use_key=False)
        response = requests.post(post_url, data=data)
        api_asserts.assert_status_code_is_ok(response)
        assert open(path).read() == "some initial text data"

    def test_write_protection(self):
        job, _, _ = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        t_file = tempfile.NamedTemporaryFile()
        data = {"path": t_file.name, "job_key": job_key}
        file = io.StringIO("some initial text data")
        files = {"file": file}
        post_url = self._api_url(f"jobs/{job_id}/files", use_key=True)
        response = requests.post(post_url, data=data, files=files)
        _assert_insufficient_permissions(response)

    @property
    def sa_session(self):
        return self._app.model.session

    def create_static_job_with_state(self, state):
        """Create a job with unknown handler so its state won't change."""
        sa_session = self.sa_session
        hda = sa_session.scalars(select(model.HistoryDatasetAssociation)).all()[0]
        assert hda
        history = sa_session.scalars(select(model.History)).all()[0]
        assert history
        user = sa_session.scalars(select(model.User)).all()[0]
        assert user
        output_hda = model.HistoryDatasetAssociation(history=history, create_dataset=True, flush=False)
        output_hda.hid = 2
        sa_session.add(output_hda)
        sa_session.commit()
        job = model.Job()
        job.history = history
        ensure_object_added_to_session(job, object_in_session=history)
        job.user = user
        job.handler = "unknown-handler"
        job.state = state
        sa_session.add(job)
        job.add_input_dataset("input1", hda)
        job.add_output_dataset("output1", output_hda)
        sa_session.commit()
        self._app.object_store.create(output_hda.dataset)
        self._app.object_store.create(job, base_dir="job_work", dir_only=True, obj_dir=True)
        working_directory = self._app.object_store.get_filename(job, base_dir="job_work", dir_only=True, obj_dir=True)
        return job, output_hda, working_directory

    def _api_job_keys(self, job):
        job_id = self._app.security.encode_id(job.id)
        job_key = self._app.security.encode_id(job.id, kind="jobs_files")
        assert job_key
        return job_id, job_key

    def _change_job_state(self, job, state):
        job.state = state
        sa_session = self.sa_session
        sa_session.add(job)
        sa_session.commit()


def _assert_insufficient_permissions(response):
    api_asserts.assert_status_code_is(response, 403)
    api_asserts.assert_error_code_is(response, 403002)
