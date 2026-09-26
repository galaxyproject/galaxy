import json
from datetime import (
    datetime,
    timezone,
)
from typing import Any

import pytest

from galaxy.files.models import (
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources.elabftw import (
    eLabFTWFileSourceTemplateConfiguration,
    eLabFTWFilesSource,
    MAX_ITEMS_PER_PAGE,
)
from galaxy_test.base.mock_http_server import (
    MockHTTPRequestHandler,
    Route,
)

EXPERIMENTS_PAGE = f"/api/v2/experiments?order=id&sort=asc&limit={MAX_ITEMS_PER_PAGE}&offset=0"


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
