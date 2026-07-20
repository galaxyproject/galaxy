import tempfile

import pytest

from galaxy.tool_util.cwl.util import (
    FileLiteralTarget,
    galactic_job_json,
    GalaxyOutput,
    output_properties,
    output_to_cwl_json,
    UploadTarget,
)


def test_output_properties_in_memory():
    props = output_properties(content=b"hello world", basename="hello.txt")
    assert props["basename"] == "hello.txt"
    assert props["nameroot"] == "hello"
    assert props["nameext"] == ".txt"
    assert props["size"] == 11
    assert props["checksum"] == "sha1$2aae6c35c94fcfb415dbe95f408b9ce91ee846ed"


def test_output_properties_path():
    f = tempfile.NamedTemporaryFile(mode="w")
    f.write("hello world")
    f.flush()

    props = output_properties(path=f.name, basename="hello.txt")
    assert props["basename"] == "hello.txt"
    assert props["nameroot"] == "hello"
    assert props["nameext"] == ".txt"
    assert props["size"] == 11
    assert props["checksum"] == "sha1$2aae6c35c94fcfb415dbe95f408b9ce91ee846ed"


def _mock_upload_func(upload_target: UploadTarget):
    """Mock upload that captures the target for inspection."""
    dataset_id = f"dataset_{id(upload_target)}"
    return {"outputs": [{"id": dataset_id}]}


def _mock_collection_create_func(element_identifiers, collection_type, rows=None, name=None):
    return {"id": f"collection_{collection_type}"}


def test_galactic_job_json_file_literal_filetype():
    """FileLiteralTarget receives filetype when specified via class: File + contents."""
    captured_targets = []

    def upload_func(upload_target):
        captured_targets.append(upload_target)
        return _mock_upload_func(upload_target)

    job = {
        "input1": {
            "class": "File",
            "contents": "some text",
            "filetype": "txt",
        }
    }
    result_job, datasets = galactic_job_json(
        job, ".", upload_func, _mock_collection_create_func, tool_or_workflow="workflow"
    )
    assert len(captured_targets) == 1
    target = captured_targets[0]
    assert isinstance(target, FileLiteralTarget)
    assert target.contents == "some text"
    assert target.properties.get("filetype") == "txt"


def test_galactic_job_json_file_literal_no_filetype():
    """FileLiteralTarget receives filetype=None when not specified."""
    captured_targets = []

    def upload_func(upload_target):
        captured_targets.append(upload_target)
        return _mock_upload_func(upload_target)

    job = {
        "input1": {
            "class": "File",
            "contents": "some text",
        }
    }
    result_job, datasets = galactic_job_json(
        job, ".", upload_func, _mock_collection_create_func, tool_or_workflow="workflow"
    )
    assert len(captured_targets) == 1
    target = captured_targets[0]
    assert isinstance(target, FileLiteralTarget)
    assert target.properties.get("filetype") is None


def test_galactic_job_json_file_literal_tags_and_dbkey():
    """FileLiteralTarget receives tags and dbkey."""
    captured_targets = []

    def upload_func(upload_target):
        captured_targets.append(upload_target)
        return _mock_upload_func(upload_target)

    job = {
        "input1": {
            "class": "File",
            "contents": "some text",
            "filetype": "fastq",
            "tags": ["group:sample1"],
            "dbkey": "hg38",
        }
    }
    result_job, datasets = galactic_job_json(
        job, ".", upload_func, _mock_collection_create_func, tool_or_workflow="workflow"
    )
    assert len(captured_targets) == 1
    target = captured_targets[0]
    assert isinstance(target, FileLiteralTarget)
    assert target.properties["filetype"] == "fastq"
    assert target.properties["tags"] == ["group:sample1"]
    assert target.properties["dbkey"] == "hg38"


def test_galactic_job_json_collection_element_filetype():
    """Collection elements with class: File + contents get filetype forwarded."""
    captured_targets = []

    def upload_func(upload_target):
        captured_targets.append(upload_target)
        return _mock_upload_func(upload_target)

    job = {
        "reads": {
            "class": "Collection",
            "collection_type": "paired",
            "elements": [
                {
                    "identifier": "forward",
                    "class": "File",
                    "contents": "forward reads",
                    "filetype": "fastqsanger",
                },
                {
                    "identifier": "reverse",
                    "class": "File",
                    "contents": "reverse reads",
                    "filetype": "fastqsanger",
                },
            ],
        }
    }
    result_job, datasets = galactic_job_json(
        job, ".", upload_func, _mock_collection_create_func, tool_or_workflow="workflow"
    )
    assert len(captured_targets) == 2
    for target in captured_targets:
        assert isinstance(target, FileLiteralTarget)
        assert target.properties.get("filetype") == "fastqsanger"


def _mock_dataset_metadata(element_id):
    return {
        "history_content_type": "dataset",
        "id": element_id,
        "file_ext": "txt",
        "name": element_id,
    }


def _collection_output(collection_type, element_identifiers):
    metadata = {
        "history_content_type": "dataset_collection",
        "collection_type": collection_type,
        "elements": [
            {"element_identifier": identifier, "object": _mock_dataset_metadata(identifier)}
            for identifier in element_identifiers
        ],
    }
    return GalaxyOutput("history_id", "dataset_collection", "collection_id", metadata)


def _output_to_cwl_json(galaxy_output):
    def get_metadata(history_content_type, history_content_id):
        return _mock_dataset_metadata(history_content_id)

    def get_dataset(dataset_details, filename=None):
        return {"content": b"hello world", "basename": dataset_details["name"]}

    def get_extra_files(dataset_details):
        return []

    return output_to_cwl_json(galaxy_output, get_metadata, get_dataset, get_extra_files)


def _nested_collection_output(collection_type, sub_collection_type, element_identifiers):
    metadata = {
        "history_content_type": "dataset_collection",
        "collection_type": collection_type,
        "elements": [
            {
                "element_identifier": identifier,
                "object": {
                    "id": identifier,
                    "collection_type": sub_collection_type,
                    "elements": [
                        {
                            "element_identifier": sub_identifier,
                            "object": _mock_dataset_metadata(f"{identifier}_{sub_identifier}"),
                        }
                        for sub_identifier in ["forward", "reverse"]
                    ],
                },
            }
            for identifier in element_identifiers
        ],
    }
    return GalaxyOutput("history_id", "dataset_collection", "collection_id", metadata)


def _assert_cwl_file(rval, basename):
    assert rval["class"] == "File"
    assert rval["basename"] == basename
    assert rval["checksum"] == "sha1$2aae6c35c94fcfb415dbe95f408b9ce91ee846ed"
    assert rval["size"] == 11


def test_output_to_cwl_json_sample_sheet():
    rval = _output_to_cwl_json(_collection_output("sample_sheet", ["sample1", "sample2"]))
    assert isinstance(rval, list)
    assert len(rval) == 2
    _assert_cwl_file(rval[0], "sample1")
    _assert_cwl_file(rval[1], "sample2")


def test_output_to_cwl_json_sample_sheet_paired():
    rval = _output_to_cwl_json(_nested_collection_output("sample_sheet", "paired", ["sample1", "sample2"]))
    assert isinstance(rval, list)
    assert len(rval) == 2
    for index, identifier in enumerate(["sample1", "sample2"]):
        assert isinstance(rval[index], list)
        assert len(rval[index]) == 2
        _assert_cwl_file(rval[index][0], f"{identifier}_forward")
        _assert_cwl_file(rval[index][1], f"{identifier}_reverse")


def test_output_to_cwl_json_paired_or_unpaired():
    rval = _output_to_cwl_json(_collection_output("paired_or_unpaired", ["unpaired"]))
    assert isinstance(rval, list)
    assert len(rval) == 1
    _assert_cwl_file(rval[0], "unpaired")


def test_output_to_cwl_json_paired_or_unpaired_paired():
    rval = _output_to_cwl_json(_collection_output("paired_or_unpaired", ["forward", "reverse"]))
    assert isinstance(rval, list)
    assert len(rval) == 2
    _assert_cwl_file(rval[0], "forward")
    _assert_cwl_file(rval[1], "reverse")


def test_output_to_cwl_json_unsupported_collection_type():
    with pytest.raises(NotImplementedError, match="not_a_real_type"):
        _output_to_cwl_json(_collection_output("not_a_real_type", ["e1"]))
