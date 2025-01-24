from typing import Tuple

import pytest

from galaxy.schema.schema import ModelStoreFormat
from galaxy.short_term_storage import ShortTermStorageAllocator
from galaxy.webapps.galaxy.services.base import model_store_storage_target


class MockShortTermStorageAllocator(ShortTermStorageAllocator):
    def __init__(self, expected_filename: str, expected_mime_type: str) -> None:
        super().__init__()
        self.expected_filename = expected_filename
        self.expected_mime_type = expected_mime_type

    def new_target(self, filename, mime_type, duration=None, security=None):
        assert filename == self.expected_filename
        assert mime_type == self.expected_mime_type


@pytest.mark.parametrize(
    "file_name, model_store_format, expected",
    [
        ("My Cool Object", "txt", ("My-Cool-Object.txt", "text/plain")),
        ("!My Cool Object!", "json", ("My-Cool-Object.json", "application/json")),
        ("Hello₩◎ґʟⅾ", "xml", ("Hello.xml", "application/xml")),
        ("test", ModelStoreFormat.ROCRATE_ZIP.value, ("test.rocrate.zip", "application/zip")),
        ("test", ModelStoreFormat.TAR.value, ("test.tar", "application/x-tar")),
        ("test", ModelStoreFormat.TGZ.value, ("test.tgz", "application/x-tar")),
        ("test", ModelStoreFormat.TAR_DOT_GZ.value, ("test.tar.gz", "application/x-tar")),
        ("test", ModelStoreFormat.BAG_DOT_ZIP.value, ("test.bag.zip", "application/zip")),
        ("test", ModelStoreFormat.BAG_DOT_TAR.value, ("test.bag.tar", "application/x-tar")),
        ("test", ModelStoreFormat.BAG_DOT_TGZ.value, ("test.bag.tgz", "application/x-tar")),
        ("test", ModelStoreFormat.BCO_JSON.value, ("test.bco.json", "application/json")),
    ],
)
def test_model_store_storage_target(file_name: str, model_store_format: str, expected: Tuple[str, str]):
    mock_sts_allocator = MockShortTermStorageAllocator(*expected)
    model_store_storage_target(
        short_term_storage_allocator=mock_sts_allocator, file_name=file_name, model_store_format=model_store_format
    )
