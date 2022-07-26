from copy import deepcopy
from json import dumps

from galaxy.schema.fetch_data import (
    FetchDataPayload,
    FileDataElement,
    FtpImportElement,
    NestedElement,
    PastedDataElement,
    UrlDataElement,
)

HISTORY_ID = "abcdef0123456789"
example_payload = {
    "targets": [
        {
            "destination": {"type": "hdas"},
            "elements": [
                {
                    "src": "pasted",
                    "paste_content": "abcdef",
                    "name": None,
                    "dbkey": "?",
                    "ext": "auto",
                    "space_to_tab": False,
                    "to_posix_lines": True,
                },
                {"src": "url", "url": "https://github.com/bla.txt"},
                {"src": "files", "name": "uploaded file"},
            ],
        }
    ],
    "auto_decompress": True,
    "files": [],
    "history_id": HISTORY_ID,
}
items_payload = {
    "targets": [
        {
            "destination": {"type": "hdas"},
            "items": [
                {
                    "src": "url",
                    "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/html_file.txt",
                },
            ],
        }
    ],
    "history_id": HISTORY_ID,
}

nested_collection_payload = {
    "targets": [
        {
            "destination": {"type": "hdca"},
            "elements": [{"name": "samp1", "elements": [{"src": "files", "dbkey": "hg19", "info": "my cool bed"}]}],
            "collection_type": "list:list",
            "name": "Test upload",
        }
    ],
    "history_id": HISTORY_ID,
}

ftp_hdca_target = {
    "elements_from": "directory",
    "src": "ftp_import",
    "ftp_path": "subdir",
    "collection_type": "list",
}

recursive_archive_payload = {
    "history_id": "f3f73e481f432006",
    "targets": [
        {
            "destination": {"type": "library", "name": "My Cool Library"},
            "items_from": "archive",
            "src": "path",
            "path": "/Users/mvandenb/src/metadata_embed/test-data/testdir1.zip",
        }
    ],
}


nested_element_regression_payload = {
    "history_id": "80a1fcbe9fcb3c61",
    "targets": [
        {
            "destination": {"type": "hdca"},
            "elements": [
                {
                    "name": "a",
                    "elements": [
                        {
                            "name": "a",
                            "elements": [
                                {
                                    "url": "https://example.com",
                                    "src": "url",
                                    "dbkey": "?",
                                    "ext": "auto",
                                    "name": "forward",
                                },
                                {
                                    "url": "https://example.com",
                                    "src": "url",
                                    "dbkey": "?",
                                    "ext": "auto",
                                    "name": "reverse",
                                },
                            ],
                            "collection_type": "paired",
                        },
                    ],
                    "collection_type": "list:paired",
                },
            ],
            "collection_type": "list:list:paired",
            "name": "a",
        }
    ],
    "auto_decompress": True,
}


def test_fetch_data_schema():
    payload = FetchDataPayload(**example_payload)
    elements = payload.targets[0].items  # type: ignore[union-attr]  # alias doesn't type check properly
    assert len(elements) == 3
    assert isinstance(elements[0], PastedDataElement)
    assert isinstance(elements[1], UrlDataElement)
    assert isinstance(elements[2], FileDataElement)


def test_data_items():
    FetchDataPayload(**items_payload)


def test_nested_collection():
    payload = FetchDataPayload(**nested_collection_payload)
    collection_element = payload.targets[0].items[0]  # type: ignore[union-attr]  # alias doesn't type check properly
    assert isinstance(collection_element, NestedElement)
    assert isinstance(collection_element.items[0], FileDataElement)


def test_ftp_hdca_target():
    FtpImportElement(**ftp_hdca_target)


def test_recursive_archive():
    FetchDataPayload(**recursive_archive_payload)


def test_recursive_archive_form_like_data():
    payload = deepcopy(recursive_archive_payload)
    payload["targets"] = dumps(payload["targets"])
    FetchDataPayload(**payload)


def test_nested_elemet_regression():
    FetchDataPayload(**nested_element_regression_payload)
