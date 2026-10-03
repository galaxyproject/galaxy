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
from dataclasses import dataclass
from typing import Any

import requests
from sqlalchemy import select
from tusclient import client

from galaxy import model
from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.model.base import ensure_object_added_to_session
from galaxy_test.base import api_asserts
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
SIMPLE_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "simple_job_conf.xml")

TEST_INPUT_TEXT = "test input content\n"
TEST_OUTPUT_TEXT = "some initial text data"
TEST_TUS_CHUNK_SIZE = 1024


@dataclass
class RunningJob:
    job: model.Job
    job_key: str
    files_url: str
    output_path: str
    working_directory: str


class TestJobFilesIntegration(integration_util.IntegrationTestCase):
    initialized = False
    dataset_populator: DatasetPopulator
    input_hda_dict: dict[str, Any]
    input_hda: model.HistoryDatasetAssociation
    nginx_upload_job_files_store: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = SIMPLE_JOB_CONFIG_FILE
        config["object_store_store_by"] = "uuid"
        config["server_name"] = "files"
        cls.nginx_upload_job_files_store = cls._test_driver.mkdtemp()
        config["nginx_upload_job_files_store"] = cls.nginx_upload_job_files_store
        cls.initialized = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        if not TestJobFilesIntegration.initialized:
            history_id = self.dataset_populator.new_history()
            sa_session = self.sa_session
            stmt = select(model.HistoryDatasetAssociation)
            assert len(sa_session.scalars(stmt).all()) == 0
            TestJobFilesIntegration.input_hda_dict = self.dataset_populator.new_dataset(
                history_id, content=TEST_INPUT_TEXT, wait=True
            )
            assert len(sa_session.scalars(stmt).all()) == 1
            TestJobFilesIntegration.input_hda = sa_session.scalars(stmt).all()[0]
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
        job = self._running_job()
        api_asserts.assert_status_code_is_ok(self._post_job_file(job, job.output_path, TEST_OUTPUT_TEXT))
        _assert_file_contents(job.output_path, TEST_OUTPUT_TEXT)

        work_dir_file = os.path.join(job.working_directory, "work")
        api_asserts.assert_status_code_is_ok(self._post_job_file(job, work_dir_file, TEST_OUTPUT_TEXT))
        _assert_file_contents(work_dir_file, TEST_OUTPUT_TEXT)

        # set job state to finished and ensure the file is no longer
        # writable
        self._change_job_state(job.job, "ok")
        _assert_insufficient_permissions(self._post_job_file(job, work_dir_file, TEST_OUTPUT_TEXT))

    def test_write_with_tus(self):
        job = self._running_job()
        upload_url = self._api_url(f"job_files/resumable_upload?job_key={job.job_key}", use_key=False)
        my_client = client.TusClient(upload_url, headers={})
        t_file = tempfile.NamedTemporaryFile("w")
        t_file.write(TEST_OUTPUT_TEXT)
        t_file.flush()

        uploader = my_client.uploader(t_file.name, metadata={}, url_storage=None)
        uploader.chunk_size = TEST_TUS_CHUNK_SIZE
        uploader.upload()
        upload_session_url = uploader.url
        assert upload_session_url
        tus_session_id = upload_session_url.rsplit("/", 1)[1]  # type: ignore[unreachable]

        response = self._post_job_file(job, job.output_path, extra={"session_id": tus_session_id})
        api_asserts.assert_status_code_is_ok(response)
        _assert_file_contents(job.output_path, TEST_OUTPUT_TEXT)

    def test_write_with_nginx_upload_module(self):
        job = self._running_job()
        upload_path = os.path.join(self.nginx_upload_job_files_store, "nginx_upload")
        _write_file(upload_path, TEST_OUTPUT_TEXT)

        response = self._post_job_file(job, job.output_path, extra={"__file_path": upload_path})
        api_asserts.assert_status_code_is_ok(response)
        assert not os.path.exists(upload_path)
        _assert_file_contents(job.output_path, TEST_OUTPUT_TEXT)

    def test_write_with_nginx_upload_module_rejects_path_outside_store(self):
        job = self._running_job()
        outside_path = os.path.join(self._test_driver.mkdtemp(), "outside")
        _write_file(outside_path, "not an upload")
        relative_outside_path = os.path.relpath(outside_path, self.nginx_upload_job_files_store)
        traversal_path = os.path.join(self.nginx_upload_job_files_store, relative_outside_path)
        assert traversal_path.startswith(self.nginx_upload_job_files_store)
        self._assert_nginx_upload_rejected(job, traversal_path, outside_path)

    def test_write_with_nginx_upload_module_rejects_relative_path(self):
        job = self._running_job()
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as outside_dir:
            outside_path = os.path.join(outside_dir, "outside")
            _write_file(outside_path, "not an upload")
            relative_path = os.path.relpath(outside_path)
            assert not relative_path.startswith("..")
            self._assert_nginx_upload_rejected(job, relative_path, outside_path)

    def test_write_with_underscored_file_param(self):
        job = self._running_job()
        response = self._post_job_file(job, job.output_path, TEST_OUTPUT_TEXT, file_param="__file")
        api_asserts.assert_status_code_is_ok(response)
        _assert_file_contents(job.output_path, TEST_OUTPUT_TEXT)

    def test_write_with_query_params(self):
        job = self._running_job()
        response = self._post_job_file(
            job, job.output_path, TEST_OUTPUT_TEXT, extra={"file_type": "output"}, as_params=True
        )
        api_asserts.assert_status_code_is_ok(response)
        _assert_file_contents(job.output_path, TEST_OUTPUT_TEXT)

    def test_write_appends_to_tool_streams(self):
        job = self._running_job()
        for stream in ["tool_stdout", "tool_stderr"]:
            path = os.path.join(job.working_directory, "outputs", stream)
            for i in range(5):
                api_asserts.assert_status_code_is_ok(self._post_job_file(job, path, f"{stream} {i}\n"))
            _assert_file_contents(path, "".join(f"{stream} {i}\n" for i in range(5)))

    def test_write_replaces_other_files(self):
        job = self._running_job()
        path = os.path.join(job.working_directory, "work")
        for content in ["first", "second"]:
            api_asserts.assert_status_code_is_ok(self._post_job_file(job, path, content))
        _assert_file_contents(path, "second")

    def test_missing_params(self):
        job = self._running_job()
        for params in [{"path": job.output_path}, {"job_key": job.job_key}]:
            _assert_missing_attribute(requests.get(job.files_url, params=params))
            response = requests.post(job.files_url, params=params, files={"file": io.StringIO(TEST_OUTPUT_TEXT)})
            _assert_missing_attribute(response)
        _assert_file_contents(job.output_path, "")

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
        working_directory = JobWorkingDirectory(job, self._app.object_store).create()
        return job, output_hda, working_directory

    def _running_job(self) -> RunningJob:
        job, output_hda, working_directory = self.create_static_job_with_state("running")
        job_id, job_key = self._api_job_keys(job)
        output_path = self._app.object_store.get_filename(output_hda.dataset)
        assert output_path
        files_url = self._api_url(f"jobs/{job_id}/files", use_key=False)
        return RunningJob(job, job_key, files_url, output_path, working_directory)

    def _post_job_file(
        self,
        job: RunningJob,
        path: str,
        content: str | None = None,
        extra: dict[str, str] | None = None,
        file_param: str = "file",
        as_params: bool = False,
    ) -> requests.Response:
        payload = {"path": path, "job_key": job.job_key, **(extra or {})}
        files = {file_param: io.StringIO(content)} if content is not None else None
        if as_params:
            return requests.post(job.files_url, params=payload, files=files)
        return requests.post(job.files_url, data=payload, files=files)

    def _assert_nginx_upload_rejected(self, job: RunningJob, file_path: str, outside_path: str):
        response = self._post_job_file(job, job.output_path, extra={"__file_path": file_path})
        api_asserts.assert_status_code_is(response, 400)
        api_asserts.assert_error_code_is(response, 400008)
        assert os.path.exists(outside_path)
        _assert_file_contents(job.output_path, "")

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


def _assert_missing_attribute(response):
    api_asserts.assert_status_code_is(response, 400)
    api_asserts.assert_error_code_is(response, 400005)


def _write_file(path, content):
    with open(path, "w") as f:
        f.write(content)


def _assert_file_contents(path, expected):
    with open(path) as f:
        assert f.read() == expected
