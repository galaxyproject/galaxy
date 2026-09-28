import json
from datetime import (
    datetime,
    timezone,
)
from typing import Any

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.files.models import (
    AnyRemoteEntry,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources.elabftw import (
    eLabFTWFileSourceTemplateConfiguration,
    eLabFTWFilesSource,
    MAX_ITEMS_PER_PAGE,
    remote_entry_sort_key,
)
from galaxy_test.base.mock_http_server import (
    MockHTTPRequestHandler,
    Route,
)

EXPERIMENTS_PAGE = f"/api/v2/experiments?order=id&sort=asc&limit={MAX_ITEMS_PER_PAGE}&offset=0"

NEWEST_FILE = RemoteFile(
    name="z.txt",
    uri="elabftw://elabftw/experiments/1/1",
    path="/experiments/1/1",
    size=5,
    ctime=datetime(2025, 1, 15, tzinfo=timezone.utc),
)
LARGEST_FILE = RemoteFile(
    name="b.txt",
    uri="elabftw://elabftw/experiments/1/2",
    path="/experiments/1/2",
    size=10,
    ctime=datetime(2024, 1, 15, tzinfo=timezone.utc),
)
UNDATED_FILE = RemoteFile(name="a.txt", uri="elabftw://elabftw/experiments/1/3", path="/experiments/1/3", size=1)
EXPERIMENT = RemoteDirectory(name="m", uri="elabftw://elabftw/experiments/9", path="/experiments/9")
ENTRIES: list[AnyRemoteEntry] = [LARGEST_FILE, EXPERIMENT, UNDATED_FILE, NEWEST_FILE]


def _elabftw_file_source(endpoint: str) -> eLabFTWFilesSource:
    return eLabFTWFilesSource(
        eLabFTWFileSourceTemplateConfiguration(
            id="elabftw",
            type="elabftw",
            endpoint=endpoint,
            api_key="key",
            file_sources_config=FileSourcePluginsConfig(),
        )
    )


def _serve_json(monkeypatch: pytest.MonkeyPatch, path: str, content: Any) -> None:
    monkeypatch.setitem(
        MockHTTPRequestHandler.routes,
        path,
        Route(body=json.dumps(content).encode(), headers={"Content-Type": "application/json"}),
    )


def _serve_uploads(monkeypatch: pytest.MonkeyPatch, uploads: list[dict]) -> None:
    _serve_json(monkeypatch, "/api/v2/experiments/1", {"uploads": uploads})


def test_list_attachments(mock_http_server, monkeypatch, non_utc_local_time):
    _serve_uploads(monkeypatch, [{"id": 2, "real_name": "b.txt", "filesize": 10, "created_at": "2024-01-15 10:00:00"}])
    entries, count = _elabftw_file_source(mock_http_server.base_url).list("/experiments/1")
    assert count == 1
    (entry,) = entries
    assert isinstance(entry, RemoteFile)
    assert (entry.name, entry.path, entry.size, entry.ctime) == (
        "b.txt",
        "/experiments/1/2",
        10,
        datetime(2024, 1, 15, 10, tzinfo=timezone.utc),
    )


def test_list_entities(mock_http_server, monkeypatch):
    _serve_json(monkeypatch, EXPERIMENTS_PAGE, [{"id": 2, "title": "Second"}, {"id": 1, "title": "First"}])
    entries, count = _elabftw_file_source(mock_http_server.base_url).list("/experiments")
    assert count == 2
    assert all(isinstance(entry, RemoteDirectory) for entry in entries)
    assert [(entry.name, entry.path) for entry in entries] == [
        ("First", "/experiments/1"),
        ("Second", "/experiments/2"),
    ]


@pytest.mark.parametrize(
    "sort_by, expected",
    [
        (None, [NEWEST_FILE, LARGEST_FILE, UNDATED_FILE, EXPERIMENT]),
        ("uri", [NEWEST_FILE, LARGEST_FILE, UNDATED_FILE, EXPERIMENT]),
        ("name", [UNDATED_FILE, LARGEST_FILE, EXPERIMENT, NEWEST_FILE]),
        ("class", [EXPERIMENT, NEWEST_FILE, LARGEST_FILE, UNDATED_FILE]),
        ("size", [EXPERIMENT, UNDATED_FILE, NEWEST_FILE, LARGEST_FILE]),
        ("ctime", [UNDATED_FILE, EXPERIMENT, LARGEST_FILE, NEWEST_FILE]),
    ],
)
def test_remote_entry_sort_key(sort_by, expected):
    assert sorted(ENTRIES, key=lambda entry: remote_entry_sort_key(entry, sort_by)) == expected


@pytest.mark.parametrize(
    "sort_by, expected_names",
    [
        (None, ["c.txt", "a.txt", "b.txt"]),
        ("name", ["a.txt", "b.txt", "c.txt"]),
        ("size", ["b.txt", "c.txt", "a.txt"]),
        ("ctime", ["a.txt", "b.txt", "c.txt"]),
    ],
)
def test_list_sorts_attachments(mock_http_server, monkeypatch, sort_by, expected_names):
    _serve_uploads(
        monkeypatch,
        [
            {"id": 2, "real_name": "a.txt", "filesize": 10, "created_at": "2024-01-15 10:00:00"},
            {"id": 1, "real_name": "c.txt", "filesize": 5, "created_at": "2025-01-15 10:00:00"},
            {"id": 3, "real_name": "b.txt", "filesize": 1, "created_at": "2024-06-15 10:00:00"},
        ],
    )
    entries, _ = _elabftw_file_source(mock_http_server.base_url).list("/experiments/1", sort_by=sort_by)
    assert [entry.name for entry in entries] == expected_names


def test_list_entities_sorted_by_name_pages_by_id(mock_http_server, monkeypatch):
    _serve_json(monkeypatch, EXPERIMENTS_PAGE, [{"id": 1, "title": "Zeta"}, {"id": 2, "title": "Alpha"}])
    entries, _ = _elabftw_file_source(mock_http_server.base_url).list("/experiments", sort_by="name")
    assert [entry.name for entry in entries] == ["Alpha", "Zeta"]


def test_list_rejects_unknown_sort_by(mock_http_server):
    with pytest.raises(RequestParameterInvalidException):
        _elabftw_file_source(mock_http_server.base_url).list("/", sort_by="hashes")
