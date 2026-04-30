import json
import os
import tempfile
from base64 import b64encode
from contextlib import contextmanager
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from shutil import rmtree
from tempfile import mkdtemp
from typing import Optional
from unittest import mock

import pytest

from galaxy.tools import data_fetch
from galaxy.tools.data_fetch import (
    _fail_if_expired,
    main,
)

B64_FOR_1_2_3 = b64encode(b"1 2 3").decode("utf-8")
URI_FOR_1_2_3 = f"base64://{B64_FOR_1_2_3}"


@pytest.mark.parametrize(
    "hash_value, error_message",
    [
        ("471ddd37fc297fba09b893b88739ece9", None),
        (
            "thisisbad",
            "Failed to validate upload with [MD5] - expected [thisisbad] got [471ddd37fc297fba09b893b88739ece9]",
        ),
    ],
)
def test_simple_path_get(hash_value: str, error_message: Optional[str]):
    with _execute_context() as execute_context:
        job_directory = execute_context.job_directory
        example_path = os.path.join(job_directory, "example_file")
        with open(example_path, "w") as f:
            f.write("sample data\nhello world")
        request = {
            "targets": [
                {
                    "destination": {
                        "type": "hdas",
                    },
                    "elements": [
                        {
                            "src": "path",
                            "path": example_path,
                            "hashes": [
                                {
                                    "hash_function": "MD5",
                                    "hash_value": hash_value,
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        assert output
        hda_result = output["elements"][0]
        if error_message is not None:
            assert hda_result["error_message"] == error_message
        else:
            assert "error_message" not in hda_result


def test_simple_uri_get(mock_http_server):
    url = mock_http_server.get_url(
        remote_url="https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed",
        file_path="test-data/1.bed",
    )
    with _execute_context(allow_localhost=True) as execute_context:
        request = {
            "targets": [
                {
                    "destination": {
                        "type": "hdas",
                    },
                    "elements": [
                        {
                            "src": "url",
                            "url": url,
                        }
                    ],
                }
            ]
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        hda_result = output["elements"][0]
        assert hda_result["state"] == "ok"
        assert hda_result["ext"] == "bed"


def test_correct_md5():
    with _execute_context() as execute_context:
        request = {
            "targets": [
                {
                    "destination": {
                        "type": "hdas",
                    },
                    "elements": [
                        {
                            "src": "url",
                            "url": URI_FOR_1_2_3,
                            "hashes": [
                                {
                                    "hash_function": "MD5",
                                    "hash_value": "5ba48b6e5a7c4d4930fda256f411e55b",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        hda_result = output["elements"][0]
        assert hda_result["state"] == "ok"
        assert hda_result["ext"] == "txt"


def test_incorrect_md5():
    with _execute_context() as execute_context:
        request = {
            "targets": [
                {
                    "destination": {
                        "type": "hdas",
                    },
                    "elements": [
                        {
                            "src": "url",
                            "url": URI_FOR_1_2_3,
                            "hashes": [
                                {
                                    "hash_function": "MD5",
                                    "hash_value": "thisisbad",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        hda_result = output["elements"][0]
        assert (
            hda_result["error_message"]
            == "Failed to validate upload with [MD5] - expected [thisisbad] got [5ba48b6e5a7c4d4930fda256f411e55b]"
        )


def test_correct_sha1():
    with _execute_context() as execute_context:
        request = {
            "targets": [
                {
                    "destination": {
                        "type": "hdas",
                    },
                    "elements": [
                        {
                            "src": "url",
                            "url": URI_FOR_1_2_3,
                            "hashes": [
                                {
                                    "hash_function": "SHA-1",
                                    "hash_value": "65e9d53484d28eef5447bc06fe2d754d1090975a",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        hda_result = output["elements"][0]
        assert hda_result["state"] == "ok"
        assert hda_result["ext"] == "txt"


def test_incorrect_sha1():
    with _execute_context() as execute_context:
        request = {
            "targets": [
                {
                    "destination": {
                        "type": "hdas",
                    },
                    "elements": [
                        {
                            "src": "url",
                            "url": URI_FOR_1_2_3,
                            "hashes": [
                                {
                                    "hash_function": "SHA-1",
                                    "hash_value": "thisisbad",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        hda_result = output["elements"][0]
        assert (
            hda_result["error_message"]
            == "Failed to validate upload with [SHA-1] - expected [thisisbad] got [65e9d53484d28eef5447bc06fe2d754d1090975a]"
        )


def test_deferred_uri_get(mock_http_server):
    url = mock_http_server.get_url(
        remote_url="https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed",
        status=404,
        body="Not Found",
    )
    with _execute_context(allow_localhost=True) as execute_context:
        request = {
            "targets": [
                {
                    "destination": {
                        "type": "hdas",
                    },
                    "elements": [
                        {
                            "src": "url",
                            "url": url,
                            "deferred": True,
                        }
                    ],
                }
            ]
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        hda_result = output["elements"][0]
        assert hda_result["state"] == "deferred"
        assert hda_result["ext"] == "bed"


def test_simple_list_path_get():
    with _execute_context() as execute_context:
        job_directory = execute_context.job_directory
        example_path = os.path.join(job_directory, "example_file")
        with open(example_path, "w") as f:
            f.write("sample data\nhello world")
        request = {
            "targets": [
                {
                    "destination": {
                        "type": "hdca",
                        "object_id": 76,
                    },
                    "elements": [{"src": "path", "path": example_path}],
                }
            ]
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        destination = output["destination"]
        assert "object_id" in destination
        assert destination["object_id"] == 76


def test_hdas_single_url_error(mock_http_server):
    url_12_bed = mock_http_server.get_url(
        remote_url="https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed",
        status=404,
        body="Not Found",
    )
    with _execute_context(allow_localhost=True) as execute_context:
        job_directory = execute_context.job_directory
        example_path = os.path.join(job_directory, "example_file")
        with open(example_path, "w") as f:
            f.write("sample data\nhello world")
        request = {
            "targets": [
                {
                    "destination": {
                        "type": "hdas",
                    },
                    "elements": [
                        {"src": "path", "path": example_path},
                        {
                            "src": "url",
                            "url": url_12_bed,
                        },
                    ],
                }
            ]
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        assert "elements" in output
        elements = output["elements"]
        assert len(elements) == 2
        assert "error_message" not in elements[0]
        assert "error_message" in elements[1]
        error = elements[1]["error_message"]
        assert f"Failed to fetch url {url_12_bed}" in error


def test_hdca_collection_element_failed(mock_http_server):
    url_12_bed = mock_http_server.get_url(
        remote_url="https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed",
        status=404,
        body="Not Found",
    )
    with _execute_context(allow_localhost=True) as execute_context:
        job_directory = execute_context.job_directory
        example_path = os.path.join(job_directory, "example_file")
        with open(example_path, "w") as f:
            f.write("sample data\nhello world")
        request = {
            "targets": [
                {
                    "destination": {
                        "type": "hdca",
                    },
                    "elements": [
                        {"src": "path", "path": example_path},
                        {
                            "src": "url",
                            "url": url_12_bed,
                        },
                    ],
                }
            ]
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        assert "error_message" in output
        error = output["error_message"]
        assert f"Failed to fetch url {url_12_bed}" in error


def test_hdca_allow_failed_collections(mock_http_server):
    url_12_bed = mock_http_server.get_url(
        remote_url="https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed",
        status=404,
        body="Not Found",
    )
    with _execute_context(allow_localhost=True) as execute_context:
        job_directory = execute_context.job_directory
        example_path = os.path.join(job_directory, "example_file")
        with open(example_path, "w") as f:
            f.write("sample data\nhello world")
        request = {
            "allow_failed_collections": True,
            "targets": [
                {
                    "destination": {
                        "type": "hdca",
                    },
                    "elements": [
                        {"src": "path", "path": example_path},
                        {
                            "src": "url",
                            "url": url_12_bed,
                        },
                    ],
                }
            ],
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        assert "error_message" not in output
        assert "elements" in output
        elements = output["elements"]
        assert len(elements) == 2
        assert "error_message" not in elements[0]
        assert "error_message" in elements[1]
        error = elements[1]["error_message"]
        assert f"Failed to fetch url {url_12_bed}" in error


def test_hdca_failed_expansion():
    with _execute_context() as execute_context:
        job_directory = execute_context.job_directory
        example_path = os.path.join(job_directory, "example_file")
        with open(example_path, "w") as f:
            f.write("sample data\nhello world")
        request = {
            "targets": [
                {
                    "destination": {
                        "type": "hdca",
                        "object_id": 76,
                    },
                    "elements_from": "bagit",
                    "src": "path",
                    "path": example_path,
                }
            ]
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        assert "elements" in output
        elements = output["elements"]
        assert len(elements) == 0
        assert "error_message" in output
        assert "Expected bagit.txt does not exist" in output["error_message"]


def test_fail_if_expired_raises_for_past_timestamp():
    with pytest.raises(Exception, match="Fetch job expired before start because staged OIDC credentials expired."):
        _fail_if_expired((datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat())


def test_fail_if_expired_allows_missing_timestamp():
    _fail_if_expired(None)


def test_fail_if_expired_allows_empty_timestamp():
    _fail_if_expired("")


def test_fail_if_expired_allows_future_timestamp():
    expiry = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    _fail_if_expired(expiry)


def test_do_fetch_short_circuits_before_processing_when_expired(monkeypatch):
    with _execute_context() as execute_context:
        request_path = os.path.join(execute_context.job_directory, "request.json")
        with open(request_path, "w") as f:
            json.dump({"targets": []}, f)
        request_to_galaxy_json = mock.Mock()
        monkeypatch.setattr(data_fetch, "_request_to_galaxy_json", request_to_galaxy_json)
        with pytest.raises(Exception, match="Fetch job expired before start because staged OIDC credentials expired."):
            data_fetch.do_fetch(
                request_path,
                working_directory=execute_context.job_directory,
                registry=mock.Mock(),
                token_expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            )
        request_to_galaxy_json.assert_not_called()


def test_do_fetch_processes_request_when_not_expired(monkeypatch):
    with _execute_context() as execute_context:
        request_path = os.path.join(execute_context.job_directory, "request.json")
        with open(request_path, "w") as f:
            json.dump({"targets": []}, f)
        expected_json: dict[str, list[dict[str, str]]] = {"__unnamed_outputs": []}
        request_to_galaxy_json = mock.Mock(return_value=expected_json)
        monkeypatch.setattr(data_fetch, "_request_to_galaxy_json", request_to_galaxy_json)
        data_fetch.do_fetch(
            request_path,
            working_directory=execute_context.job_directory,
            registry=mock.Mock(),
            token_expires_at=(datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
        )
        request_to_galaxy_json.assert_called_once()
        assert execute_context.galaxy_json == expected_json


@contextmanager
def _execute_context(allow_localhost=False):
    job_directory = mkdtemp()
    try:
        if allow_localhost:
            file_sources_path = os.path.join(job_directory, "file_sources.json")
            with open(file_sources_path, "w") as f:
                json.dump(
                    {
                        "file_sources": [
                            {"type": "http", "id": "stock_http"},
                            {"type": "base64", "id": "stock_base64"},
                        ],
                        "config": {
                            "symlink_allowlist": [],
                            "fetch_url_allowlist": ["127.0.0.0/24"],
                            "library_import_dir": None,
                            "user_library_import_dir": None,
                            "ftp_upload_dir": None,
                            "ftp_upload_purge": True,
                            "tmp_dir": None,
                            "listings_expiry_time": None,
                        },
                    },
                    f,
                )
        # temporarily set tempdir to non-existing location
        # to make sure all intermediate files are created in the working
        # directory
        tempfile.tempdir = "/abcdefgh123456"
        yield ExecuteContext(job_directory)
    finally:
        tempfile.tempdir = None
        rmtree(job_directory)


def _unnamed_output(execute_context: "ExecuteContext"):
    galaxy_json = execute_context.galaxy_json
    assert "__unnamed_outputs" in galaxy_json
    unnamed_outputs = galaxy_json.get("__unnamed_outputs")
    assert isinstance(unnamed_outputs, list)
    assert len(unnamed_outputs) > 0
    output = unnamed_outputs[0]
    return output


class ExecuteContext:
    def __init__(self, directory):
        self.job_directory = directory
        self.galaxy_json_path = os.path.join(directory, "galaxy.json")

    def execute_request(self, request):
        request_path = os.path.join(self.job_directory, "request.json")
        with open(request_path, "w") as f:
            json.dump(request, f)
        self._execute(["--request", request_path])

    def _execute(self, args):
        args.extend(["--working-directory", self.job_directory])
        assert not os.path.exists(self.galaxy_json_path)
        main(args)

    @property
    def galaxy_json(self):
        assert os.path.exists(self.galaxy_json_path)
        with open(self.galaxy_json_path) as f:
            return json.load(f)
