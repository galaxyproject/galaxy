from typing import Optional
from unittest.mock import MagicMock

import pytest

from galaxy.files.sources.osf import (
    galaxy_pagination_to_osf,
    galaxy_sort_to_osf,
    InvalidPath,
    OSF_MAX_PAGE_SIZE,
    OSFFilesSource,
    OSFRepositoryInteractor,
    ValidationError,
)


@pytest.mark.parametrize(
    "sort_by,expected",
    [
        (None, None),
        ("", None),
        ("name", "title"),
        ("-name", "-title"),
        ("ctime", "date_created"),
        ("-ctime", "-date_created"),
        ("size", "size"),
        ("-size", "-size"),
        ("unknown", None),
        ("-unknown", None),
    ],
)
def test_galaxy_sort_to_osf(sort_by: Optional[str], expected: Optional[str]):
    assert galaxy_sort_to_osf(sort_by) == expected


@pytest.mark.parametrize(
    "limit,offset,expected_page,expected_size",
    [
        (None, None, 1, OSF_MAX_PAGE_SIZE),
        (25, 0, 1, 25),
        (25, 25, 2, 25),
        (25, 50, 3, 25),
        (200, 0, 1, OSF_MAX_PAGE_SIZE),
        (10, 15, 2, 10),
    ],
)
def test_galaxy_pagination_to_osf(limit, offset, expected_page, expected_size):
    page, size = galaxy_pagination_to_osf(limit, offset)
    assert page == expected_page
    assert size == expected_size


@pytest.mark.parametrize(
    "path,container_id,file_identifier",
    [
        ("/", "", ""),
        ("/projects", "", ""),
        ("/registrations", "", ""),
        ("/files", "", ""),
        ("/projects/proj1", "proj1", ""),
        ("/registrations/reg1", "reg1", ""),
        ("/projects/proj1/data.csv", "proj1", "data.csv"),
        ("/projects/proj1/folder/sub/a.csv", "proj1", "folder/sub/a.csv"),
        ("/proj1", "proj1", ""),
        ("/proj1/data.csv", "proj1", "data.csv"),
    ],
)
def test_parse_path(path, container_id, file_identifier):
    result = OSFFilesSource.parse_path(None, path)
    assert result.container_id == container_id
    assert result.file_identifier == file_identifier


def test_parse_path_rejects_non_absolute():
    with pytest.raises(InvalidPath):
        OSFFilesSource.parse_path(None, "projects/proj1")


def test_parse_path_container_id_only():
    result = OSFFilesSource.parse_path(None, "/projects/proj1/data.csv", container_id_only=True)
    assert result.container_id == "proj1"
    assert result.file_identifier == ""


def _make_interactor():
    plugin = MagicMock()
    plugin.get_scheme.return_value = "osf"
    plugin.get_prefix.return_value = "osf"
    return OSFRepositoryInteractor(repository_url="https://api.osf.io/v2/", plugin=plugin)


def test_list_folder_root():
    client = MagicMock()
    client.list_children.return_value = [
        {"id": "child1", "attributes": {"title": "Subproject"}},
    ]
    client.list_storage.return_value = [
        {"attributes": {"name": "data", "kind": "folder", "path": "/folder1/"}},
        {"attributes": {"name": "readme.txt", "kind": "file", "path": "/file1", "size": 1024}},
    ]
    interactor = _make_interactor()
    interactor._client = lambda ctx: client

    entries, count = interactor.list_folder(context=None, container_id="proj1")

    assert count == 3
    component, folder, file_entry = entries
    assert component.name == "Subproject"
    assert component.uri == "osf://osf/projects/child1"
    assert folder.name == "data"
    assert folder.uri == "osf://osf/projects/proj1/folder1"
    assert file_entry.name == "readme.txt"
    assert file_entry.uri == "osf://osf/projects/proj1/file1"
    assert file_entry.size == 1024


def test_list_folder_subpath():
    client = MagicMock()
    client.list_storage.return_value = [
        {"attributes": {"name": "nested.csv", "kind": "file", "path": "/folder1/sub1/file1", "size": 1024}},
    ]
    interactor = _make_interactor()
    interactor._client = lambda ctx: client

    entries, count = interactor.list_folder(
        context=None, container_id="proj1", subpath="folder1/sub1",
    )

    client.list_storage.assert_called_once_with("proj1", "/folder1/sub1/")
    assert count == 1
    assert entries[0].uri == "osf://osf/projects/proj1/folder1/sub1/file1"


def test_get_files_search_results():
    client = MagicMock()
    client.list_files.return_value = {
        "data": [
            {
                "attributes": {
                    "name": "results.csv",
                    "materialized_path": "/data/results.csv",
                    "size": 500,
                },
                "relationships": {"node": {"data": {"id": "proj1"}}},
            },
            {
                "attributes": {"name": "orphan.csv", "size": 200},
                "relationships": {},
            },
        ],
        "links": {"meta": {"total": 2}},
    }
    interactor = _make_interactor()
    interactor._client = lambda ctx: client

    files, total = interactor.get_files_search_results(context=None, query="csv")

    assert total == 2
    in_project, orphan = files
    assert in_project.uri == "osf://osf/projects/proj1/data/results.csv"
    assert orphan.uri == "osf://osf/files/orphan.csv"


def test_create_entry():
    entry_data = MagicMock()
    entry_data.name = "New Project"
    source = MagicMock()
    source.get_public_name.return_value = "Test User"
    source.repository.create_draft_file_container.return_value = {
        "id": "proj1",
        "attributes": {"title": "New Project"},
        "links": {"html": "https://osf.io/proj1/"},
    }
    source.repository.to_plugin_uri.return_value = "osf://osf/projects/proj1"

    entry = OSFFilesSource._create_entry(source, entry_data, context=None)

    assert entry.name == "New Project"
    assert entry.uri == "osf://osf/projects/proj1"
    assert entry.external_link == "https://osf.io/proj1/"


def test_create_entry_missing_id():
    entry_data = MagicMock()
    entry_data.name = "New Project"
    source = MagicMock()
    source.get_public_name.return_value = "Test User"
    source.repository.create_draft_file_container.return_value = {}

    with pytest.raises(ValidationError):
        OSFFilesSource._create_entry(source, entry_data, context=None)
