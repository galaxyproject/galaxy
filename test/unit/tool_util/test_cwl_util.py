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


def test_galactic_job_json_sample_sheet_collection_without_rows():
    """sample_sheet collection works without rows metadata."""
    created_collections = []

    def collection_create_func(element_identifiers, collection_type, rows=None, name=None):
        created_collections.append(
            {"element_identifiers": element_identifiers, "collection_type": collection_type, "rows": rows, "name": name}
        )
        return {"id": f"collection_{collection_type}"}

    job = {
        "input1": {
            "class": "Collection",
            "collection_type": "sample_sheet",
            "elements": [
                {"identifier": "el1", "class": "File", "contents": "element 1"},
                {"identifier": "el2", "class": "File", "contents": "element 2"},
            ],
        }
    }
    result_job, datasets = galactic_job_json(
        job, ".", _mock_upload_func, collection_create_func, tool_or_workflow="workflow"
    )
    assert len(created_collections) == 1
    coll = created_collections[0]
    assert coll["collection_type"] == "sample_sheet"
    assert coll["rows"] is None
    assert len(coll["element_identifiers"]) == 2
    assert coll["element_identifiers"][0]["name"] == "el1"
    assert coll["element_identifiers"][1]["name"] == "el2"


def test_galactic_job_json_sample_sheet_collection_with_rows():
    """sample_sheet collection passes rows metadata through."""
    created_collections = []

    def collection_create_func(element_identifiers, collection_type, rows=None, name=None):
        created_collections.append(
            {"element_identifiers": element_identifiers, "collection_type": collection_type, "rows": rows, "name": name}
        )
        return {"id": f"collection_{collection_type}"}

    job = {
        "input1": {
            "class": "Collection",
            "collection_type": "sample_sheet",
            "elements": [
                {"identifier": "el1", "class": "File", "contents": "element 1"},
                {"identifier": "el2", "class": "File", "contents": "element 2"},
            ],
            "rows": {"el1": {"condition": "treatment"}, "el2": {"condition": "control"}},
        }
    }
    result_job, datasets = galactic_job_json(
        job, ".", _mock_upload_func, collection_create_func, tool_or_workflow="workflow"
    )
    assert len(created_collections) == 1
    coll = created_collections[0]
    assert coll["collection_type"] == "sample_sheet"
    assert coll["rows"] == {"el1": {"condition": "treatment"}, "el2": {"condition": "control"}}


def test_galactic_job_json_sample_sheet_paired_collection():
    """sample_sheet:paired creates nested collection with paired sub-elements."""
    created_collections = []

    def collection_create_func(element_identifiers, collection_type, rows=None, name=None):
        created_collections.append(
            {"element_identifiers": element_identifiers, "collection_type": collection_type, "rows": rows, "name": name}
        )
        return {"id": f"collection_{collection_type}"}

    job = {
        "input1": {
            "class": "Collection",
            "collection_type": "sample_sheet:paired",
            "elements": [
                {
                    "identifier": "sample1",
                    "class": "Collection",
                    "type": "paired",
                    "elements": [
                        {"identifier": "forward", "class": "File", "contents": "fwd reads"},
                        {"identifier": "reverse", "class": "File", "contents": "rev reads"},
                    ],
                }
            ],
        }
    }
    result_job, datasets = galactic_job_json(
        job, ".", _mock_upload_func, collection_create_func, tool_or_workflow="workflow"
    )
    assert len(created_collections) == 1
    coll = created_collections[0]
    assert coll["collection_type"] == "sample_sheet:paired"
    assert coll["rows"] is None
    assert len(coll["element_identifiers"]) == 1
    el = coll["element_identifiers"][0]
    assert el["name"] == "sample1"
    assert el["src"] == "new_collection"
    assert el["collection_type"] == "paired"
    assert len(el["element_identifiers"]) == 2
