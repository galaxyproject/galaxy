import os
import shutil
import tempfile
from typing import List

import pytest

from galaxy.files import ConfiguredFileSources
from galaxy.files.sources import FilesSource
from ._util import (
    assert_realizes_contains,
    configured_file_sources,
    user_context_fixture,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "temporary_file_sources_conf.yml")

ROOT_URI = "temp://test1"
ROOT_PATH = "/tmp/test1"


@pytest.fixture(scope="session")
def file_sources() -> ConfiguredFileSources:
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    return file_sources


@pytest.fixture(scope="session")
def temp_file_source(file_sources: ConfiguredFileSources) -> FilesSource:
    file_source_pair = file_sources.get_file_source_path(ROOT_URI)
    file_source = file_source_pair.file_source
    _populate_test_scenario(file_source)
    return file_source


def test_file_source(file_sources: FilesSource):
    assert_realizes_contains(file_sources, f"{ROOT_URI}/a", "a")
    assert_realizes_contains(file_sources, f"{ROOT_URI}/b", "b")
    assert_realizes_contains(file_sources, f"{ROOT_URI}/c", "c")
    assert_realizes_contains(file_sources, f"{ROOT_URI}/dir1/d", "d")
    assert_realizes_contains(file_sources, f"{ROOT_URI}/dir1/e", "e")
    assert_realizes_contains(file_sources, f"{ROOT_URI}/dir1/sub1/f", "f")


def test_list(temp_file_source: FilesSource):
    assert_list_names(temp_file_source, "/", recursive=False, expected_names=["a", "b", "c", "dir1"])
    assert_list_names(temp_file_source, "/dir1", recursive=False, expected_names=["d", "e", "sub1"])


def test_list_recursive(temp_file_source: FilesSource):
    expected_names = ["a", "b", "c", "dir1", "d", "e", "sub1", "f"]
    assert_list_names(temp_file_source, "/", recursive=True, expected_names=expected_names)


def test_pagination(temp_file_source: FilesSource):
    # Pagination is only supported for non-recursive listings.
    recursive = False
    root_lvl_entries = temp_file_source.list("/", recursive=recursive)
    assert len(root_lvl_entries) == 4

    # Get first entry
    result = temp_file_source.list("/", recursive=recursive, limit=1, offset=0)
    assert len(result) == 1
    assert result[0] == root_lvl_entries[0]

    # Get second entry
    result = temp_file_source.list("/", recursive=recursive, limit=1, offset=1)
    assert len(result) == 1
    assert result[0] == root_lvl_entries[1]

    # Get second and third entry
    result = temp_file_source.list("/", recursive=recursive, limit=2, offset=1)
    assert len(result) == 2
    assert result[0] == root_lvl_entries[1]
    assert result[1] == root_lvl_entries[2]

    # Get last three entries
    result = temp_file_source.list("/", recursive=recursive, limit=3, offset=1)
    assert len(result) == 3
    assert result[0] == root_lvl_entries[1]
    assert result[1] == root_lvl_entries[2]
    assert result[2] == root_lvl_entries[3]


def _populate_test_scenario(file_source: FilesSource):
    """Create a directory structure in the file source."""
    if os.path.exists(ROOT_PATH):
        shutil.rmtree(ROOT_PATH)
        os.mkdir(ROOT_PATH)

    user_context = user_context_fixture()

    _upload_to(file_source, "/a", content="a", user_context=user_context)
    _upload_to(file_source, "/b", content="b", user_context=user_context)
    _upload_to(file_source, "/c", content="c", user_context=user_context)
    _upload_to(file_source, "/dir1/d", content="d", user_context=user_context)
    _upload_to(file_source, "/dir1/e", content="e", user_context=user_context)
    _upload_to(file_source, "/dir1/sub1/f", content="f", user_context=user_context)


def _upload_to(file_source: FilesSource, target_uri: str, content: str, user_context=None):
    with tempfile.NamedTemporaryFile(mode="w") as f:
        f.write(content)
        f.flush()
        file_source.write_from(target_uri, f.name, user_context=user_context)


def assert_list_names(file_source: FilesSource, uri: str, recursive: bool, expected_names: List[str]):
    result = file_source.list(uri, recursive=recursive)
    assert sorted([entry["name"] for entry in result]) == sorted(expected_names)
    return result
