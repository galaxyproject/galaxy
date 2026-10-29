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
import uuid
from unittest.mock import patch

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
    nginx_upload_job_files_store: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.nginx_upload_job_files_store = cls._test_driver.mkdtemp()
        config["nginx_upload_job_files_store"] = cls.nginx_upload_job_files_store
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

        response = self._post_job_files(job_id, data, files())
        api_asserts.assert_status_code_is_ok(response)
        assert open(path).read() == "some initial text data"

        work_dir_file = os.path.join(working_directory, "work")
        data = {"path": work_dir_file, "job_key": job_key}
        response = self._post_job_files(job_id, data, files())
        api_asserts.assert_status_code_is_ok(response)
        assert open(work_dir_file).read() == "some initial text data"

        # set job state to finished and ensure the file is no longer
        # readable
        self._change_job_state(job, "ok")

        response = self._post_job_files(job_id, data, files())
        _assert_insufficient_permissions(response)

    def test_write_with_tus(self):
        # shared setup with above test
        job, output_hda, _ = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        path = self._app.object_store.get_filename(output_hda.dataset)
        assert path

        upload_url = self._api_url(f"job_files/resumable_upload?job_key={job_key}", use_key=False)
        headers: dict[str, str] = {}
        my_client = client.TusClient(upload_url, headers=headers)

        storage = None
        metadata: dict[str, str] = {}
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
        response = self._post_job_files(job_id, data)
        api_asserts.assert_status_code_is_ok(response)
        assert open(path).read() == "some initial text data"

    def test_write_protection(self):
        job, _, _ = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        t_file = tempfile.NamedTemporaryFile()
        data = {"path": t_file.name, "job_key": job_key}
        file = io.StringIO("some initial text data")
        files = {"file": file}
        response = self._post_job_files(job_id, data, files, use_key=True)
        _assert_insufficient_permissions(response)

    def test_write_relative_path_rejected(self):
        job, _, _ = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        relative_path = os.path.join(f"job_files_relative_{uuid.uuid4().hex}", "work")
        data = {"path": relative_path, "job_key": job_key}
        files = {"file": io.StringIO("some initial text data")}
        response = self._post_job_files(job_id, data, files)
        api_asserts.assert_status_code_is(response, 400)
        api_asserts.assert_error_message_contains(response, "absolute path")
        assert not os.path.exists(relative_path)

        response = self._post_job_files(job_id, {**data, "path": "123"}, files)
        api_asserts.assert_status_code_is(response, 400)
        api_asserts.assert_error_message_contains(response, "absolute path")

    def test_write_invalid_upload_sources_rejected(self):
        job, _, working_directory = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        data = {"path": os.path.join(working_directory, "work"), "job_key": job_key}

        response = self._post_job_files(job_id, data)
        api_asserts.assert_status_code_is(response, 400)
        api_asserts.assert_error_message_contains(response, "No file uploaded")

        response = self._post_job_files(job_id, {**data, "file": "not an upload"})
        api_asserts.assert_status_code_is(response, 400)
        api_asserts.assert_error_message_contains(response, "No file uploaded")

        for session_id in ["not/a-session", "null"]:
            response = self._post_job_files(job_id, {**data, "session_id": session_id})
            api_asserts.assert_status_code_is(response, 400)
            api_asserts.assert_error_message_contains(response, "Invalid session id")

        response = self._post_job_files(job_id, {**data, "__file_path": "null"})
        api_asserts.assert_status_code_is(response, 400)
        api_asserts.assert_error_message_contains(response, "not in the configured upload directory")

        response = self._post_job_files(job_id, {**data, "session_id": "unknown-session"})
        api_asserts.assert_status_code_is(response, 400)
        api_asserts.assert_error_message_contains(response, "No upload found")

        missing_nginx_path = os.path.join(self.nginx_upload_job_files_store, "missing")
        response = self._post_job_files(job_id, {**data, "__file_path": missing_nginx_path})
        api_asserts.assert_status_code_is(response, 400)
        api_asserts.assert_error_message_contains(response, "File provided by nginx does not exist")

        upload_path = os.path.join(self.nginx_upload_job_files_store, "unconfigured")
        _write_file(upload_path, "not an upload")
        with patch.object(self._app.config, "nginx_upload_job_files_store", None):
            response = self._post_job_files(job_id, {**data, "__file_path": upload_path})
        api_asserts.assert_status_code_is(response, 403)
        api_asserts.assert_error_message_contains(response, "nginx_upload_module")
        assert not os.path.exists(data["path"])

    def test_write_with_nginx_upload_module(self):
        job, output_hda, _ = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        path = self._app.object_store.get_filename(output_hda.dataset)
        upload_path = os.path.join(self.nginx_upload_job_files_store, "nginx_upload")
        _write_file(upload_path, "some initial text data")
        response = self._post_job_files(job_id, {"path": path, "job_key": job_key, "__file_path": upload_path})
        api_asserts.assert_status_code_is_ok(response)
        assert not os.path.exists(upload_path)
        assert open(path).read() == "some initial text data"

    def test_write_with_nginx_upload_module_rejects_path_outside_store(self):
        outside_path = os.path.join(self._test_driver.mkdtemp(), "outside")
        _write_file(outside_path, "not an upload")
        traversal_path = os.path.join(
            self.nginx_upload_job_files_store, os.path.relpath(outside_path, self.nginx_upload_job_files_store)
        )
        assert traversal_path.startswith(self.nginx_upload_job_files_store)
        self._assert_nginx_upload_rejected(traversal_path, outside_path)

    def test_write_with_nginx_upload_module_rejects_relative_path(self):
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as outside_dir:
            outside_path = os.path.join(outside_dir, "outside")
            _write_file(outside_path, "not an upload")
            relative_path = os.path.relpath(outside_path)
            assert not relative_path.startswith("..")
            self._assert_nginx_upload_rejected(relative_path, outside_path)

    def _assert_nginx_upload_rejected(self, file_path, outside_path):
        job, output_hda, _ = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        path = self._app.object_store.get_filename(output_hda.dataset)
        response = self._post_job_files(job_id, {"path": path, "job_key": job_key, "__file_path": file_path})
        api_asserts.assert_status_code_is(response, 400)
        api_asserts.assert_error_message_contains(response, "not in the configured upload directory")
        assert os.path.exists(outside_path)
        assert open(path).read() == ""

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

    def _post_job_files(self, job_id, data, files=None, use_key=False):
        post_url = self._api_url(f"jobs/{job_id}/files", use_key=use_key)
        return requests.post(post_url, data=data, files=files)

    def _change_job_state(self, job, state):
        job.state = state
        sa_session = self.sa_session
        sa_session.add(job)
        sa_session.commit()


def _assert_insufficient_permissions(response):
    api_asserts.assert_status_code_is(response, 403)
    api_asserts.assert_error_code_is(response, 403002)


def _write_file(path, contents):
    with open(path, "w") as f:
        f.write(contents)
