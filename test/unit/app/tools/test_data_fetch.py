import json
import os
import tempfile
from base64 import b64encode
from contextlib import contextmanager
from shutil import rmtree
from tempfile import mkdtemp

from galaxy.tools.data_fetch import main
from galaxy.util.unittest_utils import skip_if_github_down

B64_FOR_1_2_3 = b64encode(b"1 2 3").decode("utf-8")
URI_FOR_1_2_3 = f"base64://{B64_FOR_1_2_3}"


def test_simple_path_get():
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
                    "elements": [{"src": "path", "path": example_path}],
                }
            ]
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        assert output


@skip_if_github_down
def test_simple_uri_get():
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
                            "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed",
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
            "validate_hashes": True,
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
            "validate_hashes": True,
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
            "validate_hashes": True,
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
            "validate_hashes": True,
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        hda_result = output["elements"][0]
        assert (
            hda_result["error_message"]
            == "Failed to validate upload with [SHA-1] - expected [thisisbad] got [65e9d53484d28eef5447bc06fe2d754d1090975a]"
        )


@skip_if_github_down
def test_deferred_uri_get():
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
                            "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed",
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


@skip_if_github_down
def test_hdas_single_url_error():
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
                        {"src": "path", "path": example_path},
                        {
                            "src": "url",
                            "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed",
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
        assert (
            "Failed to fetch url https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed" in error
        )


@skip_if_github_down
def test_hdca_collection_element_failed():
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
                    },
                    "elements": [
                        {"src": "path", "path": example_path},
                        {
                            "src": "url",
                            "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed",
                        },
                    ],
                }
            ]
        }
        execute_context.execute_request(request)
        output = _unnamed_output(execute_context)
        assert "error_message" in output
        error = output["error_message"]
        assert (
            "Failed to fetch url https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed" in error
        )


@skip_if_github_down
def test_hdca_allow_failed_collections():
    with _execute_context() as execute_context:
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
                            "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed",
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
        assert (
            "Failed to fetch url https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed" in error
        )


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


@contextmanager
def _execute_context():
    job_directory = mkdtemp()
    try:
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
