import tempfile

from galaxy.tool_util.cwl.util import (
    FileLiteralTarget,
    galactic_job_json,
    output_properties,
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
