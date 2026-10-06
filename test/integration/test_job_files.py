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
import time
from dataclasses import (
    dataclass,
    replace,
)
from typing import Any

import requests
from sqlalchemy import select
from tusclient import client

from galaxy import model
from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.model.base import ensure_object_added_to_session
from galaxy.webapps.galaxy.api.job_files import UPLOAD_STAGING_PREFIX
from galaxy_test.base import api_asserts
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
SIMPLE_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "simple_job_conf.xml")

TEST_INPUT_TEXT = "test input content\n"
TEST_OUTPUT_TEXT = "some initial text data"
TEST_TUS_CHUNK_SIZE = 1024
UPLOAD_BOUNDARY = "jobfilesboundary"
LARGE_UPLOAD_CHUNK_SIZE = 1024 * 1024
LARGE_UPLOAD_CHUNKS = 8


@dataclass
class RunningJob:
    job: model.Job
    job_key: str
    files_url: str
    output_path: str
    output_extra_files_path: str
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

    def test_read_missing_file(self):
        # Without inputs, so a missing dataset-named file can't be blamed on a purged input.
        job = self._running_job(with_input=False)
        for name in ["missing", "dataset_missing.dat"]:
            params = {"path": os.path.join(job.working_directory, name), "job_key": job.job_key}
            api_asserts.assert_status_code_is(requests.head(job.files_url, params=params), 404)
            response = requests.get(job.files_url, params=params)
            api_asserts.assert_status_code_is(response, 404)
            api_asserts.assert_error_code_is(response, 404001)

    def test_read_directory(self):
        job = self._running_job()
        response = requests.get(job.files_url, params={"path": job.working_directory, "job_key": job.job_key})
        api_asserts.assert_status_code_is(response, 400)
        api_asserts.assert_error_code_is(response, 400008)

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

    def test_write_with_form_params(self):
        job = self._running_job()
        new_file_path_contents = set(os.listdir(self._app.config.new_file_path))
        response = self._post_job_file(job, job.output_path, TEST_OUTPUT_TEXT, form_auth=True)
        api_asserts.assert_status_code_is_ok(response)
        _assert_file_contents(job.output_path, TEST_OUTPUT_TEXT)
        work_dir_file = os.path.join(job.working_directory, "work")
        response = self._post_job_file(job, work_dir_file, TEST_OUTPUT_TEXT, form_auth=True)
        api_asserts.assert_status_code_is_ok(response)
        _assert_file_contents(work_dir_file, TEST_OUTPUT_TEXT)
        assert set(os.listdir(self._app.config.new_file_path)) == new_file_path_contents

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

        response = self._post_job_file(job, job.output_path, data={"session_id": tus_session_id})
        api_asserts.assert_status_code_is_ok(response)
        _assert_file_contents(job.output_path, TEST_OUTPUT_TEXT)

    def test_write_with_nginx_upload_module(self):
        job = self._running_job()
        upload_path = os.path.join(self.nginx_upload_job_files_store, "nginx_upload")
        _write_file(upload_path, TEST_OUTPUT_TEXT)

        response = self._post_job_file(job, job.output_path, data={"__file_path": upload_path})
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

    def test_write_with_missing_upload_source(self):
        job = self._running_job()
        missing_nginx_path = os.path.join(self.nginx_upload_job_files_store, "missing")
        for data in [{"session_id": "missing-session"}, {"__file_path": missing_nginx_path}]:
            response = self._post_job_file(job, job.output_path, data=data)
            api_asserts.assert_status_code_is(response, 400)
            api_asserts.assert_error_code_is(response, 400008)
        _assert_file_contents(job.output_path, "")

    def test_write_without_file(self):
        job = self._running_job()
        response = requests.post(job.files_url, params={"path": job.output_path, "job_key": job.job_key})
        api_asserts.assert_status_code_is(response, 400)
        _assert_file_contents(job.output_path, "")

    def test_write_with_malformed_multipart(self):
        job = self._running_job()
        headers = {"Content-Type": f"multipart/form-data; boundary={UPLOAD_BOUNDARY}"}
        params = {"path": job.output_path, "job_key": job.job_key}
        response = requests.post(job.files_url, params=params, data=b"not multipart", headers=headers)
        api_asserts.assert_status_code_is(response, 400)
        api_asserts.assert_error_code_is(response, 400008)
        _assert_file_contents(job.output_path, "")

    def test_unknown_job(self):
        job = self._running_job()
        missing_job_id = 2**31 - 1
        encoded_job_id = self._app.security.encode_id(missing_job_id)
        unknown_job = replace(
            job,
            files_url=self._api_url(f"jobs/{encoded_job_id}/files", use_key=False),
            job_key=self._app.security.encode_id(missing_job_id, kind="jobs_files"),
        )
        response = requests.get(unknown_job.files_url, params={"path": job.output_path, "job_key": unknown_job.job_key})
        api_asserts.assert_status_code_is(response, 404)
        api_asserts.assert_status_code_is(self._post_job_file(unknown_job, job.output_path, TEST_OUTPUT_TEXT), 404)

    def test_write_with_underscored_file_param(self):
        job = self._running_job()
        response = self._post_job_file(job, job.output_path, TEST_OUTPUT_TEXT, file_param="__file")
        api_asserts.assert_status_code_is_ok(response)
        _assert_file_contents(job.output_path, TEST_OUTPUT_TEXT)

    def test_write_with_query_params(self):
        job = self._running_job()
        response = self._post_job_file(job, job.output_path, TEST_OUTPUT_TEXT, params={"file_type": "output"})
        api_asserts.assert_status_code_is_ok(response)
        _assert_file_contents(job.output_path, TEST_OUTPUT_TEXT)

    def test_write_appends_to_tool_streams(self):
        job = self._running_job()
        for stream in ["tool_stdout", "tool_stderr"]:
            path = os.path.join(job.working_directory, "outputs", stream)
            for i in range(5):
                api_asserts.assert_status_code_is_ok(self._post_job_file(job, path, f"{stream} {i}\n"))
            _assert_file_contents(path, "".join(f"{stream} {i}\n" for i in range(5)))
        assert not _staging_dirs(job.working_directory)

    def test_write_replaces_other_files(self):
        job = self._running_job()
        path = os.path.join(job.working_directory, "work")
        for content in ["first", "second"]:
            api_asserts.assert_status_code_is_ok(self._post_job_file(job, path, content))
        _assert_file_contents(path, "second")

    def test_write_and_read_path_with_percent_escapes(self):
        job = self._running_job()
        path = os.path.join(job.working_directory, "a%2Fb%20c")
        api_asserts.assert_status_code_is_ok(self._post_job_file(job, path, "escaped"))
        _assert_file_contents(path, "escaped")
        response = requests.get(job.files_url, params={"path": path, "job_key": job.job_key})
        api_asserts.assert_status_code_is_ok(response)
        assert response.text == "escaped"

    def test_write_streams_working_directory_upload(self):
        job = self._running_job()
        self._assert_upload_streamed(job, os.path.join(job.working_directory, "large"), job.working_directory)

    def test_write_streams_extra_file_upload_outside_extra_files_path(self):
        job = self._running_job()
        os.makedirs(job.output_extra_files_path)
        path = os.path.join(job.output_extra_files_path, "large")
        self._assert_upload_streamed(job, path, os.path.dirname(job.output_path))

    def test_rejected_upload_leaves_no_staged_files(self):
        job = self._running_job()
        path = os.path.join(job.working_directory, "work")
        outside_path = os.path.join(self._test_driver.mkdtemp(), "outside")
        new_file_path_contents = set(os.listdir(self._app.config.new_file_path))
        invalid_key_job = replace(job, job_key="invalid")
        _assert_insufficient_permissions(self._post_job_file(invalid_key_job, path, TEST_OUTPUT_TEXT))
        _assert_insufficient_permissions(self._post_job_file(job, outside_path, TEST_OUTPUT_TEXT))
        _assert_insufficient_permissions(self._post_job_file(invalid_key_job, path, TEST_OUTPUT_TEXT, form_auth=True))
        assert not _staging_dirs(job.working_directory)
        assert not _staging_dirs(os.path.dirname(outside_path))
        assert set(os.listdir(self._app.config.new_file_path)) == new_file_path_contents
        assert not os.path.exists(path)
        assert not os.path.exists(outside_path)

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

    def create_static_job_with_state(self, state, with_input=True):
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
        if with_input:
            job.add_input_dataset("input1", hda)
        job.add_output_dataset("output1", output_hda)
        sa_session.commit()
        self._app.object_store.create(output_hda.dataset)
        working_directory = JobWorkingDirectory(job, self._app.object_store).create()
        return job, output_hda, working_directory

    def _running_job(self, with_input: bool = True) -> RunningJob:
        job, output_hda, working_directory = self.create_static_job_with_state("running", with_input=with_input)
        job_id, job_key = self._api_job_keys(job)
        output_path = self._app.object_store.get_filename(output_hda.dataset)
        assert output_path
        files_url = self._api_url(f"jobs/{job_id}/files", use_key=False)
        extra_files_path = output_hda.dataset.extra_files_path
        return RunningJob(job, job_key, files_url, output_path, extra_files_path, working_directory)

    def _post_job_file(
        self,
        job: RunningJob,
        path: str,
        content: str | None = None,
        data: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        file_param: str = "file",
        form_auth: bool = False,
    ) -> requests.Response:
        """Post like Pulsar - path and job_key as query params - unless ``form_auth``."""
        auth = {"path": path, "job_key": job.job_key}
        data = {**(data or {}), **(auth if form_auth else {})}
        params = {**(params or {}), **({} if form_auth else auth)}
        files = {file_param: io.StringIO(content)} if content is not None else None
        return requests.post(job.files_url, params=params, data=data, files=files)

    def _assert_upload_streamed(self, job: RunningJob, path: str, staging_parent: str):
        new_file_path_contents = set(os.listdir(self._app.config.new_file_path))
        chunk = b"x" * LARGE_UPLOAD_CHUNK_SIZE
        staged_sizes: list[int] = []
        extra_files_staging: list[list[str]] = []

        def body():
            yield (
                f'--{UPLOAD_BOUNDARY}\r\nContent-Disposition: form-data; name="file"; filename="large"\r\n\r\n'
            ).encode()
            for _ in range(LARGE_UPLOAD_CHUNKS):
                yield chunk
            staged_sizes.append(
                _wait_for_staged_upload(staging_parent, (LARGE_UPLOAD_CHUNKS - 1) * LARGE_UPLOAD_CHUNK_SIZE)
            )
            extra_files_staging.append(_staging_dirs(job.output_extra_files_path))
            yield f"\r\n--{UPLOAD_BOUNDARY}--\r\n".encode()

        headers = {"Content-Type": f"multipart/form-data; boundary={UPLOAD_BOUNDARY}"}
        params = {"path": path, "job_key": job.job_key}
        response = requests.post(job.files_url, params=params, data=body(), headers=headers)
        api_asserts.assert_status_code_is_ok(response)
        assert staged_sizes[0] >= (LARGE_UPLOAD_CHUNKS - 1) * LARGE_UPLOAD_CHUNK_SIZE
        assert extra_files_staging == [[]]
        assert os.path.getsize(path) == LARGE_UPLOAD_CHUNKS * LARGE_UPLOAD_CHUNK_SIZE
        assert not _staging_dirs(staging_parent)
        assert set(os.listdir(self._app.config.new_file_path)) == new_file_path_contents

    def _assert_nginx_upload_rejected(self, job: RunningJob, file_path: str, outside_path: str):
        response = self._post_job_file(job, job.output_path, data={"__file_path": file_path})
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


def _staging_dirs(directory):
    if not os.path.isdir(directory):
        return []
    return [name for name in os.listdir(directory) if name.startswith(UPLOAD_STAGING_PREFIX)]


def _wait_for_staged_upload(directory, min_size, timeout=10):
    deadline = time.time() + timeout
    size = 0
    while time.time() < deadline:
        for staging_dir in _staging_dirs(directory):
            staging_path = os.path.join(directory, staging_dir)
            for name in os.listdir(staging_path):
                size = max(size, os.path.getsize(os.path.join(staging_path, name)))
        if size >= min_size:
            break
        time.sleep(0.05)
    return size


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
