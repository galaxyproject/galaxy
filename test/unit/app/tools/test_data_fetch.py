import errno
import json
import os
import shutil
import tempfile
from base64 import b64encode
from contextlib import contextmanager
from shutil import rmtree
from tempfile import mkdtemp
from typing import (
    Any,
)

import pytest
import responses

from galaxy.tools.data_fetch import main
from galaxy.util import galaxy_directory

# galaxy_directory rather than a walk up from __file__: the packages test
# suite copies this module elsewhere in the tree.
GALAXY_ROOT = galaxy_directory()
STOCK_DATATYPES_CONF = os.path.join(GALAXY_ROOT, "lib", "galaxy", "config", "sample", "datatypes_conf.xml.sample")

B64_FOR_1_2_3 = b64encode(b"1 2 3").decode("utf-8")
URI_FOR_1_2_3 = f"base64://{B64_FOR_1_2_3}"

DRS_OBJECT_ID = "000009a0-5b22-5be5-9217-a26b5c0b03c2"
DRS_URI = f"drs://drs.example.org/{DRS_OBJECT_ID}"
DRS_OBJECT_URL = f"https://drs.example.org/ga4gh/drs/v1/objects/{DRS_OBJECT_ID}"


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
def test_simple_path_get(hash_value: str, error_message: str | None):
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
        assert hda_result["name"] == "1.bed"


@responses.activate
def test_drs_uri_named_from_drs_metadata(mock_http_server):
    _mock_drs_object(_bed_content_url(mock_http_server), name="sample.bed")
    hda_result = _fetch_drs_element()
    assert hda_result["state"] == "ok"
    assert hda_result["name"] == "sample.bed"


@responses.activate
def test_drs_uri_named_from_drs_metadata_via_access_id(mock_http_server):
    _mock_drs_object(_bed_content_url(mock_http_server), name="sample.bed", access_id="https")
    hda_result = _fetch_drs_element()
    assert hda_result["state"] == "ok"
    assert hda_result["name"] == "sample.bed"


@responses.activate
def test_drs_uri_explicit_name_wins(mock_http_server):
    _mock_drs_object(_bed_content_url(mock_http_server), name="sample.bed")
    hda_result = _fetch_drs_element(name="user supplied name")
    assert hda_result["state"] == "ok"
    assert hda_result["name"] == "user supplied name"


@responses.activate
def test_drs_uri_without_name_falls_back_to_uri_basename(mock_http_server):
    _mock_drs_object(_bed_content_url(mock_http_server))
    hda_result = _fetch_drs_element()
    assert hda_result["state"] == "ok"
    assert hda_result["name"] == DRS_OBJECT_ID


@pytest.mark.parametrize(
    "drs_name, expected_name",
    [
        ("../../../etc/passwd", "passwd"),
        ("/etc/passwd", "passwd"),
        ("..\\..\\windows\\system32", "system32"),
        ("sample\r\n.bed", "sample.bed"),
        ("..", DRS_OBJECT_ID),
        (".", DRS_OBJECT_ID),
        ("", DRS_OBJECT_ID),
        ("   ", DRS_OBJECT_ID),
        ("etc/", DRS_OBJECT_ID),
        (12345, DRS_OBJECT_ID),
        ({"value": "sample.bed"}, DRS_OBJECT_ID),
    ],
)
@responses.activate
def test_drs_uri_name_is_sanitized(mock_http_server, drs_name, expected_name):
    _mock_drs_object(_bed_content_url(mock_http_server), name=drs_name)
    hda_result = _fetch_drs_element()
    assert hda_result["state"] == "ok"
    assert hda_result["name"] == expected_name


@responses.activate
def test_drs_uri_overlong_name_is_truncated(mock_http_server):
    _mock_drs_object(_bed_content_url(mock_http_server), name="a" * 300)
    hda_result = _fetch_drs_element()
    assert hda_result["state"] == "ok"
    assert hda_result["name"] == "a" * 255


def _bed_content_url(mock_http_server) -> str:
    return mock_http_server.get_url(
        remote_url="https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed",
        file_path="test-data/1.bed",
    )


def _mock_drs_object(content_url: str, name: Any = None, access_id: str | None = None) -> None:
    """Register mock responses for a DRS object resolving to ``content_url``."""
    # The DRS API endpoints are mocked below, but the payload itself is served by the
    # real local mock_http_server; the download also goes through requests now, so it
    # has to be exempted from the responses mock.
    responses.add_passthru(content_url)
    access_method: dict[str, Any] = {"type": "https"}
    if access_id is not None:
        access_method["access_id"] = access_id
        responses.add(responses.GET, f"{DRS_OBJECT_URL}/access/{access_id}", json={"url": content_url})
    else:
        access_method["access_url"] = {"url": content_url}
    drs_object: dict[str, Any] = {"id": DRS_OBJECT_ID, "access_methods": [access_method]}
    if name is not None:
        drs_object["name"] = name
    responses.add(responses.GET, DRS_OBJECT_URL, json=drs_object)


def _fetch_drs_element(name: str | None = None) -> dict[str, Any]:
    element: dict[str, Any] = {"src": "url", "url": DRS_URI}
    if name is not None:
        element["name"] = name
    with _execute_context(allow_localhost=True) as execute_context:
        request = {
            "targets": [
                {
                    "destination": {"type": "hdas"},
                    "elements": [element],
                }
            ]
        }
        execute_context.execute_request(request)
        return _unnamed_output(execute_context)["elements"][0]


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
                            {"type": "drs", "id": "stock_drs"},
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

    def execute_request(self, request, datatypes_registry: str | None = None):
        request_path = os.path.join(self.job_directory, "request.json")
        with open(request_path, "w") as f:
            json.dump(request, f)
        args = ["--request", request_path]
        if datatypes_registry:
            args.extend(["--galaxy-root", GALAXY_ROOT, "--datatypes-registry", datatypes_registry])
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


def _write_zarr_store(root: str) -> None:
    """Minimal v2 zarr layout: a .zgroup at the store root plus one array."""
    os.makedirs(os.path.join(root, "0"))
    with open(os.path.join(root, ".zgroup"), "w") as f:
        json.dump({"zarr_format": 2}, f)
    with open(os.path.join(root, "0", ".zarray"), "w") as f:
        json.dump({"zarr_format": 2, "shape": [1], "chunks": [1], "dtype": "<i4"}, f)
    with open(os.path.join(root, "0", "0"), "wb") as f:
        f.write(b"\x00\x00\x00\x00")


def _write_json(path: str, content: Any) -> None:
    with open(path, "w") as f:
        json.dump(content, f)


def _write_ome_sidecar(root: str) -> None:
    os.mkdir(os.path.join(root, "OME"))
    with open(os.path.join(root, "OME", "METADATA.ome.xml"), "w") as f:
        f.write("<OME/>")


def _fetch_single_path(
    path: str,
    ext: str | None = None,
    link_data_only: Any = None,
    purge_source: Any = None,
) -> tuple[dict[str, Any], list[str]]:
    """Fetch one path and return its result plus the extra-files tree.

    The tree is listed before the job directory is torn down, since the
    staged files do not outlive the execute context.
    """
    with _execute_context() as execute_context:
        element: dict[str, Any] = {"src": "path", "path": path}
        if ext is not None:
            element["ext"] = ext
        if link_data_only is not None:
            element["link_data_only"] = link_data_only
        if purge_source is not None:
            element["purge_source"] = purge_source
        execute_context.execute_request(
            {"targets": [{"destination": {"type": "hdas"}, "elements": [element]}]},
            datatypes_registry=STOCK_DATATYPES_CONF,
        )
        output = _unnamed_output(execute_context)
        assert output
        result = output["elements"][0]
        staged = []
        extra_files = result.get("extra_files")
        if extra_files and os.path.isdir(extra_files):
            for dirpath, _, filenames in os.walk(extra_files):
                for filename in filenames:
                    staged.append(os.path.relpath(os.path.join(dirpath, filename), extra_files))
        if result.get("filename"):
            result["_primary_file_size"] = os.path.getsize(result["filename"])
        if len(staged) == 1 and extra_files:
            # None when the staged entry cannot be read at all - a symlink
            # left dangling by the staging, for instance.
            only = os.path.join(extra_files, staged[0])
            result["_staged_content"] = None
            if os.path.isfile(only) and os.path.getsize(only) < 4096:
                with open(only) as f:
                    result["_staged_content"] = f.read()
        return result, sorted(staged)


def test_directory_path_is_staged_as_directory_dataset(tmp_path):
    """A src=path pointing at a plain directory must not be opened as a file."""
    source = tmp_path / "some_dir"
    (source / "nested").mkdir(parents=True)
    (source / "nested" / "a.txt").write_text("hello")

    result, staged = _fetch_single_path(str(source))

    assert "error_message" not in result, result.get("error_message")
    assert result["ext"] == "directory"
    assert result["name"] == "some_dir"
    assert staged == [os.path.join("some_dir", "nested", "a.txt")]
    assert result["_primary_file_size"] == 0


def test_zarr_directory_path_is_detected(tmp_path):
    """The zarr layout is recognised from the tree, since ext is 'auto'."""
    source = tmp_path / "input9.zarr"
    source.mkdir()
    _write_zarr_store(str(source))

    result, staged = _fetch_single_path(str(source))

    assert "error_message" not in result, result.get("error_message")
    assert result["ext"] == "zarr"
    assert os.path.join("input9.zarr", ".zgroup") in staged


def test_zarr_directory_detected_without_a_zarr_suffix(tmp_path):
    """Detection is by layout, not by the directory's name."""
    source = tmp_path / "plainly_named"
    source.mkdir()
    _write_zarr_store(str(source))

    assert _fetch_single_path(str(source))[0]["ext"] == "zarr"


@pytest.mark.parametrize(
    "describe_store",
    [
        pytest.param(lambda root: None, id="plain"),
        pytest.param(
            lambda root: _write_json(os.path.join(root, ".zattrs"), {"multiscales": [{"version": "0.4"}]}),
            id="ngff-multiscales",
        ),
        pytest.param(lambda root: _write_ome_sidecar(root), id="bioformats2raw-sidecar"),
    ],
)
def test_directory_detection_stops_at_the_storage_format(tmp_path, describe_store):
    """Auto-detection yields zarr, never the ome_zarr profile layered on it.

    The archive route says the same for identical bytes - the zarr.zip
    converter is registered with target_datatype="zarr" - and one store
    should not get two types depending on how it arrived. ome_zarr remains
    available by asking for it explicitly.
    """
    source = tmp_path / "image.zarr"
    source.mkdir()
    _write_zarr_store(str(source))
    describe_store(str(source))

    assert _fetch_single_path(str(source))[0]["ext"] == "zarr"


def test_ome_zarr_can_still_be_requested_explicitly(tmp_path):
    source = tmp_path / "image.zarr"
    source.mkdir()
    _write_zarr_store(str(source))
    _write_ome_sidecar(str(source))

    assert _fetch_single_path(str(source), ext="ome_zarr")[0]["ext"] == "ome_zarr"


def test_explicit_ext_overrides_directory_sniffing(tmp_path):
    source = tmp_path / "input9.zarr"
    source.mkdir()
    _write_zarr_store(str(source))

    assert _fetch_single_path(str(source), ext="directory")[0]["ext"] == "directory"


def test_directory_upload_rejects_a_non_directory_datatype(tmp_path):
    """An ordinary ext would report success while hiding all content in extra files."""
    source = tmp_path / "some_dir"
    source.mkdir()
    (source / "a.txt").write_text("hello")

    result, staged = _fetch_single_path(str(source), ext="txt")

    assert "not a directory datatype" in result["error_message"]
    assert staged == []
    assert source.is_dir(), "the source must be left alone when the request is rejected"


def test_directory_upload_rejects_linking(tmp_path):
    source = tmp_path / "some_dir"
    source.mkdir()
    (source / "a.txt").write_text("hello")

    result, _ = _fetch_single_path(str(source), link_data_only=True)

    assert "linking directory datasets is not implemented" in result["error_message"]
    assert source.is_dir()


def test_directory_upload_purges_the_source_when_asked(tmp_path):
    source = tmp_path / "some_dir"
    source.mkdir()
    (source / "a.txt").write_text("hello")

    result, staged = _fetch_single_path(str(source), purge_source=True)

    assert "error_message" not in result, result.get("error_message")
    assert staged == [os.path.join("some_dir", "a.txt")]
    assert not source.exists(), "purge_source: true must not leave the source tree behind"


def test_directory_upload_keeps_the_source_when_not_purging(tmp_path):
    source = tmp_path / "some_dir"
    source.mkdir()
    (source / "a.txt").write_text("hello")

    result, staged = _fetch_single_path(str(source), purge_source=False)

    assert "error_message" not in result, result.get("error_message")
    assert staged == [os.path.join("some_dir", "a.txt")]
    assert (source / "a.txt").read_text() == "hello"


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores directory permissions")
def test_directory_purge_keeps_the_staged_copy_when_the_source_cannot_be_removed(tmp_path):
    """A source we cannot unlink must cost us the source, never the staged copy.

    A writable directory inside a non-writable parent is the awkward case:
    its contents can be deleted but the directory itself cannot.
    """
    parent = tmp_path / "locked"
    source = parent / "some_dir"
    source.mkdir(parents=True)
    (source / "a.txt").write_text("hello")
    parent.chmod(0o500)
    try:
        result, staged = _fetch_single_path(str(source), purge_source=True)
    finally:
        parent.chmod(0o700)

    assert "error_message" not in result, result.get("error_message")
    assert staged == [os.path.join("some_dir", "a.txt")], "the staged tree must survive intact"


def test_directory_purge_renames_rather_than_copying_within_a_filesystem(tmp_path, monkeypatch):
    """A same-filesystem purge should be a rename, not a full copy and delete."""
    source = tmp_path / "some_dir"
    source.mkdir()
    (source / "a.txt").write_text("hello")

    copied = []
    real_copytree = shutil.copytree

    def spy_copytree(src, dst, *args, **kwargs):
        copied.append(src)
        return real_copytree(src, dst, *args, **kwargs)

    monkeypatch.setattr(shutil, "copytree", spy_copytree)

    result, staged = _fetch_single_path(str(source), purge_source=True)

    assert "error_message" not in result, result.get("error_message")
    assert staged == [os.path.join("some_dir", "a.txt")]
    assert not source.exists()
    assert copied == [], f"expected a rename, but the tree was copied: {copied}"


def test_directory_purge_falls_back_to_copying_when_the_source_is_read_only(tmp_path, monkeypatch):
    """A read-only source must be copied and retained, not fail the upload.

    Models a read-only mount: the rename is refused, and the cleanup that
    follows the copy removes nothing. Both are scoped to this source so the
    rest of the fetch behaves normally.
    """
    source = tmp_path / "some_dir"
    source.mkdir()
    (source / "a.txt").write_text("hello")

    def is_our_source(candidate) -> bool:
        return os.path.abspath(str(candidate)) == os.path.abspath(str(source))

    real_rename = os.rename
    real_rmtree = shutil.rmtree

    def refuse_rename(src, dst, *args, **kwargs):
        if is_our_source(src):
            raise OSError(errno.EROFS, "Read-only file system")
        return real_rename(src, dst, *args, **kwargs)

    def refuse_rmtree(path, ignore_errors=False, **kwargs):
        if is_our_source(path):
            if ignore_errors:
                return
            raise OSError(errno.EROFS, "Read-only file system")
        return real_rmtree(path, ignore_errors=ignore_errors, **kwargs)

    monkeypatch.setattr(os, "rename", refuse_rename)
    monkeypatch.setattr(shutil, "rmtree", refuse_rmtree)

    result, staged = _fetch_single_path(str(source), purge_source=True)

    assert "error_message" not in result, result.get("error_message")
    assert staged == [os.path.join("some_dir", "a.txt")]
    assert (source / "a.txt").read_text() == "hello", "a read-only source is left in place"


def test_directory_path_with_a_trailing_slash(tmp_path):
    """A trailing slash must not produce an empty basename."""
    source = tmp_path / "some_dir"
    source.mkdir()
    (source / "a.txt").write_text("hello")

    result, staged = _fetch_single_path(f"{source}{os.sep}")

    assert "error_message" not in result, result.get("error_message")
    assert result["name"] == "some_dir"
    assert staged == [os.path.join("some_dir", "a.txt")]


def test_internal_directory_symlinks_are_materialized_when_purging(tmp_path, monkeypatch):
    """A link staying inside the tree is followed, and forces a copy.

    A rename would relocate the link itself, leaving a relative one dangling.
    """
    source = tmp_path / "some_dir"
    (source / "data").mkdir(parents=True)
    (source / "data" / "chunk").write_text("payload")
    (source / "a").symlink_to(os.path.join("data", "chunk"))

    copied = []
    real_copytree = shutil.copytree

    def spy_copytree(src, dst, *args, **kwargs):
        copied.append(src)
        return real_copytree(src, dst, *args, **kwargs)

    monkeypatch.setattr(shutil, "copytree", spy_copytree)

    result, staged = _fetch_single_path(str(source), purge_source=True)

    assert "error_message" not in result, result.get("error_message")
    assert staged == [os.path.join("some_dir", "a"), os.path.join("some_dir", "data", "chunk")]
    assert copied, "a tree holding symlinks must be copied, not renamed"


def test_directory_symlinks_pointing_outside_the_tree_are_refused(tmp_path):
    """Following such a link would copy files the requester may not be entitled to."""
    outside = tmp_path / "secret"
    outside.write_text("not yours")
    source = tmp_path / "some_dir"
    source.mkdir()
    (source / "a").symlink_to(os.path.join("..", "secret"))

    result, staged = _fetch_single_path(str(source), purge_source=True)

    assert "points outside it" in result["error_message"]
    assert staged == [], "nothing may be staged from a rejected directory"
    assert source.is_dir(), "the source must be left alone"
    assert outside.read_text() == "not yours"


def test_a_directory_holding_a_text_file_named_meta_is_not_zarr(tmp_path):
    """The zarr layout check alone matches an ordinary directory."""
    source = tmp_path / "notes"
    source.mkdir()
    (source / "meta").write_text("just some notes, not JSON\n")

    result, _ = _fetch_single_path(str(source))

    assert "error_message" not in result, result.get("error_message")
    assert result["ext"] == "directory"


def test_a_symlinked_directory_root_is_materialized_when_purging(tmp_path):
    """Renaming a symlinked root would relocate the link, not the tree."""
    real = tmp_path / "real_store"
    real.mkdir()
    (real / "a.txt").write_text("payload")
    source = tmp_path / "some_dir"
    source.symlink_to(os.path.join(".", "real_store"))

    result, staged = _fetch_single_path(str(source), purge_source=True)

    assert "error_message" not in result, result.get("error_message")
    assert staged == [os.path.join("some_dir", "a.txt")]
    assert result["_staged_content"] == "payload", "the tree must be followed, not the link moved"


def test_a_directory_holding_a_json_meta_file_is_not_zarr(tmp_path):
    """Valid JSON is not enough; Zarr metadata has to identify itself."""
    source = tmp_path / "notes"
    source.mkdir()
    (source / "meta").write_text('{"description": "notes"}')

    result, _ = _fetch_single_path(str(source))

    assert "error_message" not in result, result.get("error_message")
    assert result["ext"] == "directory"


@pytest.mark.parametrize("meta_content", ["[1]", '"notes"', "null", "12"])
def test_non_object_json_meta_is_a_failed_sniff_not_an_error(tmp_path, meta_content):
    """Valid JSON that is not an object must fall back, not fail the upload.

    Sniffing happens after the source may already have been moved, so a
    raising sniffer would lose the data.
    """
    source = tmp_path / "notes"
    source.mkdir()
    (source / "meta").write_text(meta_content)

    result, staged = _fetch_single_path(str(source))

    assert "error_message" not in result, result.get("error_message")
    assert result["ext"] == "directory"
    assert staged == [os.path.join("notes", "meta")]


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores file permissions")
def test_staging_never_dereferences_an_escaping_link(tmp_path):
    """Containment is settled on the staged tree, so the target is never read.

    The target is made unreadable: dereferencing it during the copy would
    fail with PermissionError, so our own refusal proves it was not followed.
    """
    outside = tmp_path / "secret"
    outside.write_text("not yours")
    outside.chmod(0o000)
    source = tmp_path / "some_dir"
    source.mkdir()
    (source / "a").symlink_to(os.path.join("..", "secret"))

    try:
        result, staged = _fetch_single_path(str(source), purge_source=False)
    finally:
        outside.chmod(0o600)

    assert "points outside it" in result["error_message"], result.get("error_message")
    assert staged == []
