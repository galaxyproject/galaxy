import json
import os
import tempfile
from base64 import b64encode
from contextlib import contextmanager
from shutil import rmtree
from tempfile import mkdtemp
from typing import Optional
from uuid import uuid4

import pytest

from galaxy.tools.data_fetch import main
from galaxy.util import galaxy_directory
from galaxy.util.unittest_utils import skip_if_github_down

B64_FOR_1_2_3 = b64encode(b"1 2 3").decode("utf-8")
URI_FOR_1_2_3 = f"base64://{B64_FOR_1_2_3}"

GALAXY_ROOT = galaxy_directory()
# Register lped to exercise composite filenames that substitute base_name.
LPED_DATATYPES_CONF = """<?xml version="1.0"?>
<datatypes>
  <registration>
    <datatype extension="lped" type="galaxy.datatypes.genetics:Lped"/>
  </registration>
</datatypes>
"""


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


def test_extra_files_nested_layout_stays_in_extra_files_directory():
    with _execute_context() as execute_context:
        extra_files = {
            "elements": [
                {"src": "pasted", "paste_content": "top\n", "name": "top.txt"},
                {
                    "name": "subdir",
                    "elements": [
                        {"src": "pasted", "paste_content": "nested\n", "name": "nested.txt"},
                        {"src": "pasted", "paste_content": "deep\n", "name": "deeper/deep.txt"},
                    ],
                },
            ]
        }
        execute_context.execute_request(_composite_request(extra_files))
        output = _unnamed_output(execute_context)
        element = output["elements"][0]
        assert "error_message" not in element
        extra_files_path = element["extra_files"]
        job_directory = os.path.realpath(execute_context.job_directory)
        assert os.path.realpath(extra_files_path).startswith(job_directory + os.sep)
        assert os.path.exists(os.path.join(extra_files_path, "top.txt"))
        assert os.path.exists(os.path.join(extra_files_path, "subdir", "nested.txt"))
        assert os.path.exists(os.path.join(extra_files_path, "subdir", "deeper", "deep.txt"))


def test_extra_files_leaf_name_cannot_escape_extra_files_directory():
    with _execute_context() as execute_context:
        escaped_path = execute_context.path_outside_job_directory()
        bad_name = os.path.join("..", "..", os.path.basename(escaped_path))
        extra_files = {"elements": [{"src": "pasted", "paste_content": "escaped\n", "name": bad_name}]}
        _assert_extra_files_rejected(execute_context, extra_files, bad_name, escaped_path)


def test_extra_files_directory_name_cannot_escape_extra_files_directory():
    with _execute_context() as execute_context:
        escaped_path = execute_context.path_outside_job_directory()
        bad_name = os.path.join("..", "..")
        extra_files = {
            "elements": [
                {
                    "name": bad_name,
                    "elements": [
                        {"src": "pasted", "paste_content": "escaped\n", "name": os.path.basename(escaped_path)}
                    ],
                }
            ]
        }
        _assert_extra_files_rejected(execute_context, extra_files, bad_name, escaped_path)


def test_extra_files_absolute_name_cannot_escape_extra_files_directory():
    with _execute_context() as execute_context:
        escaped_path = execute_context.path_outside_job_directory()
        extra_files = {"elements": [{"src": "pasted", "paste_content": "escaped\n", "name": escaped_path}]}
        _assert_extra_files_rejected(execute_context, extra_files, escaped_path, escaped_path)


def _composite_request(extra_files):
    return {
        "targets": [
            {
                "destination": {
                    "type": "hdas",
                },
                "elements": [
                    {
                        "src": "pasted",
                        "paste_content": "primary\n",
                        "ext": "txt",
                        "extra_files": extra_files,
                    }
                ],
            }
        ]
    }


def _assert_extra_files_rejected(execute_context, extra_files, bad_name, escaped_path):
    execute_context.execute_request(_composite_request(extra_files))
    assert not os.path.exists(escaped_path), f"extra file escaped the job directory to {escaped_path}"
    output = _unnamed_output(execute_context)
    element = output["elements"][0]
    assert "error_message" in element
    assert bad_name in element["error_message"]
    assert "extra file name" in element["error_message"]


def test_composite_base_name_cannot_escape_extra_files_directory():
    # For a composite datatype whose file template substitutes ``base_name`` (e.g.
    # lped's ``%s.ped``), the user-supplied element name becomes part of the
    # on-disk composite key. A traversing name must not write outside the dataset.
    with _execute_context() as execute_context:
        conf_path = os.path.join(execute_context.job_directory, "test_datatypes_conf.xml")
        with open(conf_path, "w") as f:
            f.write(LPED_DATATYPES_CONF)
        escape_dir = os.path.join(os.path.dirname(execute_context.job_directory), f"escape-{uuid4().hex}")
        os.makedirs(escape_dir)
        try:
            base_name = ("../" * 40) + os.path.join(escape_dir.lstrip("/"), "pwned")
            request = {
                "targets": [
                    {
                        "destination": {"type": "hdas"},
                        "elements": [
                            {
                                "ext": "lped",
                                "name": base_name,
                                "composite": {"elements": [{"src": "pasted", "paste_content": "ped content\n"}]},
                            }
                        ],
                    }
                ]
            }
            execute_context.execute_request(request, datatypes_registry=conf_path, galaxy_root=GALAXY_ROOT)
            # base_name is sanitized before it becomes the composite key on this
            # branch, so the traversing name is contained rather than rejected; the
            # sink guard is covered directly by test_sniff. The invariant is no escape.
            assert os.listdir(escape_dir) == [], f"composite file escaped into {escape_dir}"
            _unnamed_output(execute_context)
        finally:
            rmtree(escape_dir, ignore_errors=True)


@contextmanager
def _execute_context():
    job_directory = mkdtemp()
    execute_context = ExecuteContext(job_directory)
    try:
        # temporarily set tempdir to non-existing location
        # to make sure all intermediate files are created in the working
        # directory
        tempfile.tempdir = "/abcdefgh123456"
        yield execute_context
    finally:
        tempfile.tempdir = None
        rmtree(job_directory)
        for path in execute_context.paths_outside_job_directory:
            if os.path.exists(path):
                os.remove(path)


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
        self.paths_outside_job_directory: list[str] = []

    def path_outside_job_directory(self):
        # A sibling of the job directory: where ``<primary>_extra/../../<name>`` would land.
        path = os.path.join(os.path.dirname(self.job_directory), f"escaped-{uuid4().hex}.txt")
        self.paths_outside_job_directory.append(path)
        return path

    def execute_request(self, request, datatypes_registry=None, galaxy_root=None):
        request_path = os.path.join(self.job_directory, "request.json")
        with open(request_path, "w") as f:
            json.dump(request, f)
        args = ["--request", request_path]
        if datatypes_registry is not None:
            args.extend(["--datatypes-registry", datatypes_registry])
        if galaxy_root is not None:
            args.extend(["--galaxy-root", galaxy_root])
        self._execute(args)

    def _execute(self, args):
        args.extend(["--working-directory", self.job_directory])
        assert not os.path.exists(self.galaxy_json_path)
        main(args)

    @property
    def galaxy_json(self):
        assert os.path.exists(self.galaxy_json_path)
        with open(self.galaxy_json_path) as f:
            return json.load(f)
