from pathlib import Path

import pytest

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from galaxy.files.models import (
    EntryData,
    FileSourcePluginsConfig,
)
from galaxy.files.sources.onedrive import OneDriveFilesSource


class MockResponse:
    def __init__(self, status_code=200, json_data=None, text="", content_chunks=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self._content_chunks = content_chunks or []

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._json_data

    def iter_content(self, chunk_size=1024 * 1024):
        yield from self._content_chunks


def _plugin():
    template = OneDriveFilesSource.build_template_config(
        id="test1",
        type="onedrive",
        label="OneDrive",
        doc="Test OneDrive file source",
        writable=True,
        access_token="test_access_token",
        file_sources_config=FileSourcePluginsConfig(),
    )
    return OneDriveFilesSource(template)


def _plugin_full():
    template = OneDriveFilesSource.build_template_config(
        id="test1",
        type="onedrive",
        label="OneDrive",
        doc="Test OneDrive file source",
        writable=True,
        access_token="test_access_token",
        drive_mode="full",
        file_sources_config=FileSourcePluginsConfig(),
    )
    return OneDriveFilesSource(template)


def test_list_root(monkeypatch):
    plugin = _plugin()
    observed = {}

    def mock_request(method, url, headers=None, timeout=None, **kwargs):
        observed["method"] = method
        observed["url"] = url
        observed["headers"] = headers
        return MockResponse(
            json_data={
                "value": [
                    {"name": "subdir", "folder": {}, "size": 0},
                    {"name": "a.txt", "size": 12, "lastModifiedDateTime": "2026-04-05T12:00:00Z"},
                ]
            }
        )

    monkeypatch.setattr("galaxy.files.sources.onedrive.requests.request", mock_request)

    entries, count = plugin.list("/")

    assert count == 2
    assert observed["method"] == "GET"
    assert observed["url"] == "https://graph.microsoft.com/v1.0/me/drive/special/approot/children"
    assert observed["headers"]["Authorization"] == "Bearer test_access_token"
    assert entries[0].path == "/subdir"
    assert entries[0].uri == "gxfiles://test1/subdir"
    assert entries[1].path == "/a.txt"
    assert entries[1].uri == "gxfiles://test1/a.txt"


def test_list_root_full_drive_mode(monkeypatch):
    plugin = _plugin_full()
    observed = {}

    def mock_request(method, url, headers=None, timeout=None, **kwargs):
        observed["url"] = url
        return MockResponse(json_data={"value": []})

    monkeypatch.setattr("galaxy.files.sources.onedrive.requests.request", mock_request)

    entries, count = plugin.list("/")

    assert count == 0
    assert entries == []
    assert observed["url"] == "https://graph.microsoft.com/v1.0/me/drive/root/children"


def test_list_nested_folder(monkeypatch):
    plugin = _plugin()
    observed = {}

    def mock_request(method, url, headers=None, timeout=None, **kwargs):
        observed["url"] = url
        return MockResponse(json_data={"value": [{"name": "b.txt", "size": 4}]})

    monkeypatch.setattr("galaxy.files.sources.onedrive.requests.request", mock_request)

    entries, count = plugin.list("/level1/level 2")

    assert count == 1
    assert observed["url"] == "https://graph.microsoft.com/v1.0/me/drive/special/approot:/level1/level%202:/children"
    assert entries[0].path == "/level1/level 2/b.txt"


def test_list_nested_folder_full_drive_mode(monkeypatch):
    plugin = _plugin_full()
    observed = {}

    def mock_request(method, url, headers=None, timeout=None, **kwargs):
        observed["url"] = url
        return MockResponse(json_data={"value": [{"name": "b.txt", "size": 4}]})

    monkeypatch.setattr("galaxy.files.sources.onedrive.requests.request", mock_request)

    entries, count = plugin.list("/level1/level 2")

    assert count == 1
    assert observed["url"] == "https://graph.microsoft.com/v1.0/me/drive/root:/level1/level%202:/children"
    assert entries[0].path == "/level1/level 2/b.txt"


def test_realize_to_downloads_content(monkeypatch, tmp_path: Path):
    plugin = _plugin()
    target = tmp_path / "downloaded.txt"

    def mock_request(method, url, headers=None, timeout=None, stream=None, **kwargs):
        assert method == "GET"
        assert stream is True
        assert url == "https://graph.microsoft.com/v1.0/me/drive/special/approot:/dir/file.txt:/content"
        return MockResponse(content_chunks=[b"hello ", b"world"])

    monkeypatch.setattr("galaxy.files.sources.onedrive.requests.request", mock_request)

    plugin.realize_to("/dir/file.txt", str(target))

    assert target.read_text("utf-8") == "hello world"


def test_write_from_uploads_content(monkeypatch, tmp_path: Path):
    plugin = _plugin()
    source = tmp_path / "upload.txt"
    source.write_text("payload", "utf-8")
    observed = {}

    def mock_put(url, headers=None, data=None, timeout=None):
        observed["url"] = url
        observed["headers"] = headers
        observed["data"] = data.read()
        return MockResponse(json_data={"id": "item1"})

    monkeypatch.setattr("galaxy.files.sources.onedrive.requests.put", mock_put)

    actual_uri = plugin.write_from("/nested/upload.txt", str(source))

    assert actual_uri == "gxfiles://test1/nested/upload.txt"
    assert observed["url"] == "https://graph.microsoft.com/v1.0/me/drive/special/approot:/nested/upload.txt:/content"
    assert observed["headers"]["Authorization"] == "Bearer test_access_token"
    assert observed["data"] == b"payload"


def test_create_entry_creates_directory(monkeypatch):
    plugin = _plugin()
    observed = {}

    def mock_post(url, json=None, headers=None, timeout=None):
        observed["url"] = url
        observed["json"] = json
        observed["headers"] = headers
        return MockResponse(json_data={"name": "newdir", "webUrl": "https://example.org/newdir"})

    monkeypatch.setattr("galaxy.files.sources.onedrive.requests.post", mock_post)

    entry = plugin.create_entry(EntryData(name="newdir", target="gxfiles://test1/parent"))

    assert observed["url"] == "https://graph.microsoft.com/v1.0/me/drive/special/approot:/parent:/children"
    assert observed["json"]["name"] == "newdir"
    assert entry.uri == "gxfiles://test1/parent/newdir"
    assert entry.external_link == "https://example.org/newdir"


def test_list_authentication_error(monkeypatch):
    plugin = _plugin()

    def mock_request(method, url, headers=None, timeout=None, **kwargs):
        return MockResponse(status_code=401, json_data={"error": {"message": "Unauthorized"}})

    monkeypatch.setattr("galaxy.files.sources.onedrive.requests.request", mock_request)

    with pytest.raises(AuthenticationRequired):
        plugin.list("/")


def test_write_reports_api_error(monkeypatch, tmp_path: Path):
    plugin = _plugin()
    source = tmp_path / "upload.txt"
    source.write_text("payload", "utf-8")

    def mock_put(url, headers=None, data=None, timeout=None):
        return MockResponse(status_code=400, json_data={"error": {"message": "Bad request"}})

    monkeypatch.setattr("galaxy.files.sources.onedrive.requests.put", mock_put)

    with pytest.raises(MessageException, match="Bad request"):
        plugin.write_from("/upload.txt", str(source))
