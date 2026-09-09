"""Tests for the ARC (DataHUB/GitLab) file source.

The plugin wraps ``arcfs.fs.GitLabARCFileSystem`` from the optional ``arcfs-fsspec`` package. Most tests
below replace that class with an in-memory fake so they run without the package and without network
access; the last tests talk to the public DataPLANT DataHUB and are skipped when the package or the
site is unavailable.
"""

import os
from urllib.parse import quote
from uuid import uuid4

import pytest

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from galaxy.files.models import (
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.sources import arc
from galaxy.files.sources.arc import ARCFilesSource
from galaxy.util import requests
from galaxy.util.unittest_utils import (
    skip_if_site_down,
    skip_unless_environ,
)
from ._util import (
    assert_realizes_as,
    configured_file_sources,
    user_context_fixture,
    write_from,
)

PUBLIC_DATAHUB_URL = "https://git.nfdi4plants.org"
ROOT_MARKER = ":-:"
TRANSIENT_ERROR_MARKERS = ("rate limit", "429", "503", "connection", "timed out", "timeout", "temporarily")

# The listing shape produced by arcfs: projects are top-level directories whose names end with the
# ``:-:`` marker, and entries inside a project are prefixed with ``<project>:-:``.
FAKE_TREE = {
    "": [
        {"name": "group/repo1:-:", "type": "directory"},
        {"name": "group/sub/repo2:-:", "type": "directory"},
        {"name": "other/repo3:-:", "type": "directory"},
    ],
    "group/repo1:-:": [
        {"name": "group/repo1:-:README.md", "type": "file"},
        {"name": "group/repo1:-:assays", "type": "directory"},
    ],
    "group/repo1:-:assays": [
        {"name": "group/repo1:-:assays/measurements.csv", "type": "file"},
    ],
}
FAKE_FILES = {
    "group/repo1:-:README.md": "hello from repo1\n",
    "group/repo1:-:assays/measurements.csv": "a,b\n1,2\n",
}


class FakeRecorder:
    def __init__(self):
        self.init_kwargs: list[dict] = []
        self.ls_calls: list[str] = []
        self.list_page_calls: list[dict] = []
        self.walk_calls: list[str] = []
        self.get_file_calls: list[tuple[str, str]] = []
        self.closed = 0
        self.list_page_error: Exception | None = None


def _make_fake_fs_class(recorder: FakeRecorder):
    class FakeGitLabARCFileSystem:
        """Minimal stand-in for ``arcfs.fs.GitLabARCFileSystem``."""

        def __init__(self, **kwargs):
            recorder.init_kwargs.append(dict(kwargs))

        @staticmethod
        def _key(path: str) -> str:
            return (path or "").strip().strip("/")

        def ls(self, path, detail=True, **kwargs):
            key = self._key(path)
            recorder.ls_calls.append(key)
            entries = FAKE_TREE.get(key, [])
            return entries if detail else [e["name"] for e in entries]

        def list_page(self, path, detail=True, *, offset=0, limit=50, **kwargs):
            recorder.list_page_calls.append({"path": self._key(path), "offset": offset, "limit": limit})
            if recorder.list_page_error is not None:
                raise recorder.list_page_error
            entries = FAKE_TREE.get(self._key(path), [])
            return entries[offset : offset + limit], len(entries)

        def walk(self, path, detail=True, **kwargs):
            key = self._key(path)
            recorder.walk_calls.append(key)
            entries = FAKE_TREE.get(key, [])
            dirs = {e["name"]: e for e in entries if e["type"] == "directory"}
            files = {e["name"]: e for e in entries if e["type"] == "file"}
            yield key, dirs, files

        def get_file(self, rpath, lpath, **kwargs):
            key = self._key(rpath)
            recorder.get_file_calls.append((key, lpath))
            with open(lpath, "w") as f:
                f.write(FAKE_FILES[key])

        def close(self):
            recorder.closed += 1

    return FakeGitLabARCFileSystem


@pytest.fixture
def fake_fs(monkeypatch) -> FakeRecorder:
    recorder = FakeRecorder()
    fake_class = _make_fake_fs_class(recorder)
    # Both names matter: ``_open_fs`` reads the module-level name, and ``FsspecFilesSource.__init__``
    # refuses to construct the plugin when ``required_module`` is None.
    monkeypatch.setattr(arc, "GitLabARCFileSystem", fake_class)
    monkeypatch.setattr(ARCFilesSource, "required_module", fake_class)
    return recorder


def _source_config(**overrides) -> dict:
    config = {"type": "arc", "id": "test1", "base_url": "https://datahub.example.org", "token": "glpat-secret"}
    config.update(overrides)
    return config


def _arc_source(conf=None) -> ARCFilesSource:
    file_sources = configured_file_sources([conf or _source_config()])
    return file_sources.get_file_source_path("gxfiles://test1").file_source


def test_plugin_type():
    assert ARCFilesSource.plugin_type == "arc"
    assert ARCFilesSource.required_package == "arcfs-fsspec"


def test_missing_package_gives_actionable_error(monkeypatch):
    monkeypatch.setattr(arc, "GitLabARCFileSystem", None)
    monkeypatch.setattr(ARCFilesSource, "required_module", None)
    with pytest.raises(Exception, match="arcfs-fsspec"):
        _arc_source()


def test_open_fs_passes_config_and_cache_options(fake_fs):
    source = _arc_source(_source_config(listings_expiry_time=120))
    source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert len(fake_fs.init_kwargs) == 1
    kwargs = fake_fs.init_kwargs[0]
    assert kwargs["base_url"] == "https://datahub.example.org"
    assert kwargs["token"] == "glpat-secret"
    assert kwargs["asynchronous"] is False
    assert kwargs["listings_expiry_time"] == 120
    assert "use_listings_cache" in kwargs


def test_anonymous_access_passes_no_token(fake_fs):
    source = _arc_source(_source_config(token=None))
    source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.init_kwargs[0]["token"] is None


def test_paginated_listing_uses_list_page_and_reports_total(fake_fs):
    source = _arc_source()
    entries, total = source.list("/", limit=2, offset=1, user_context=user_context_fixture())
    assert fake_fs.list_page_calls == [{"path": "", "offset": 1, "limit": 2}]
    assert fake_fs.ls_calls == []
    assert total == 3
    assert [e.path for e in entries] == ["group/sub/repo2:-:", "other/repo3:-:"]
    assert fake_fs.closed == 1, "the filesystem should be closed after a paginated listing"


def test_unpaginated_listing_falls_back_to_generic_fsspec_listing(fake_fs):
    source = _arc_source()
    entries, total = source.list("/", user_context=user_context_fixture())
    assert fake_fs.list_page_calls == []
    assert fake_fs.ls_calls == [""]
    assert total == 3
    assert all(isinstance(e, RemoteDirectory) for e in entries)


def test_recursive_listing_falls_back_to_generic_fsspec_listing(fake_fs):
    source = _arc_source()
    entries, _ = source.list("group/repo1:-:", recursive=True, limit=10, offset=0, user_context=user_context_fixture())
    assert fake_fs.list_page_calls == []
    assert fake_fs.walk_calls == ["group/repo1:-:"]
    assert {e.path for e in entries} == {"group/repo1:-:README.md", "group/repo1:-:assays"}


def test_entries_keep_arcfs_paths_and_build_uris(fake_fs):
    source = _arc_source()
    root, _ = source.list("/", limit=10, offset=0, user_context=user_context_fixture())
    assert [e.name for e in root] == ["group/repo1", "group/sub/repo2", "other/repo3"]
    repo = next(e for e in root if isinstance(e, RemoteDirectory))
    assert repo.path == "group/repo1:-:"
    assert repo.uri == "gxfiles://test1/group/repo1:-:"

    inside, total = source.list(repo.path, limit=10, offset=0, user_context=user_context_fixture())
    assert total == 2
    readme = next(e for e in inside if isinstance(e, RemoteFile))
    assert readme.name == "README.md"
    assert readme.path == "group/repo1:-:README.md"
    assert readme.uri == "gxfiles://test1/group/repo1:-:README.md"
    assays = next(e for e in inside if isinstance(e, RemoteDirectory))
    assert assays.name == "assays"
    assert assays.path == "group/repo1:-:assays"

    deeper, _ = source.list(assays.path, limit=10, offset=0, user_context=user_context_fixture())
    assert [(e.name, e.path) for e in deeper] == [("measurements.csv", "group/repo1:-:assays/measurements.csv")]


@pytest.mark.parametrize(
    "path, expected",
    [
        ("group/repo:-:", "group/repo"),
        ("group/sub/repo:-:", "group/sub/repo"),
        ("group/repo:-:/", "group/repo"),
        ("group/repo:-:README.md", "README.md"),
        ("group/repo:-:assays/data.csv", "data.csv"),
        ("group/repo:-:assays/", "assays"),
        ("plain/path/file.txt", "file.txt"),
    ],
)
def test_display_name_hides_marker(path, expected):
    assert ARCFilesSource._display_name(path) == expected


def test_realize_downloads_through_get_file(fake_fs):
    file_sources = configured_file_sources([_source_config()])
    assert_realizes_as(
        file_sources,
        "gxfiles://test1/group/repo1:-:assays/measurements.csv",
        "a,b\n1,2\n",
        user_context=user_context_fixture(),
    )
    assert fake_fs.get_file_calls[0][0] == "group/repo1:-:assays/measurements.csv"


def test_permission_error_becomes_authentication_required(fake_fs):
    fake_fs.list_page_error = PermissionError("401 Unauthorized")
    source = _arc_source()
    with pytest.raises(AuthenticationRequired, match="Permission Denied"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.closed == 1


def test_other_errors_become_message_exception(fake_fs):
    fake_fs.list_page_error = RuntimeError("GitLab exploded")
    source = _arc_source()
    with pytest.raises(MessageException, match="Problem listing file source path"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())


# --- live tests against the public DataPLANT DataHUB (anonymous, read-only) ---


def _skip_if_transient(e: Exception):
    message = str(e).lower()
    if any(marker in message for marker in TRANSIENT_ERROR_MARKERS):
        pytest.skip(f"DataHUB unavailable or rate-limited: {e}")


@skip_if_site_down(PUBLIC_DATAHUB_URL)
def test_public_datahub_listing_and_download():
    pytest.importorskip("arcfs")
    file_sources = configured_file_sources([{"type": "arc", "id": "test1", "base_url": PUBLIC_DATAHUB_URL}])
    source = file_sources.get_file_source_path("gxfiles://test1").file_source
    user_context = user_context_fixture()
    try:
        repos, total = source.list("/", limit=5, offset=0, user_context=user_context)
    except MessageException as e:
        _skip_if_transient(e)
        raise
    assert repos, "expected at least one public ARC on the DataHUB"
    assert total >= len(repos)
    assert all(isinstance(r, RemoteDirectory) and r.path.endswith(ROOT_MARKER) for r in repos)
    assert all(ROOT_MARKER not in r.name for r in repos)

    # Public ARCs may be empty; find one with a file and fetch it.
    for repo in repos:
        try:
            entries, _ = source.list(repo.path, limit=20, offset=0, user_context=user_context)
        except MessageException as e:
            _skip_if_transient(e)
            raise
        remote_file = next((e for e in entries if isinstance(e, RemoteFile)), None)
        if remote_file is None:
            continue
        assert remote_file.uri.startswith("gxfiles://test1/")
        assert remote_file.path.startswith(repo.path)
        contents = _realize_bytes(file_sources, remote_file.uri, user_context)
        assert contents, f"downloaded {remote_file.uri} but it was empty"
        return
    pytest.skip("none of the first public ARCs contained a top-level file")


def _realize_bytes(file_sources, uri: str, user_context) -> bytes:
    import tempfile

    file_source_path = file_sources.get_file_source_path(uri)
    with tempfile.NamedTemporaryFile() as temp:
        file_source_path.file_source.realize_to(file_source_path.path, temp.name, user_context=user_context)
        with open(temp.name, "rb") as f:
            return f.read()


@skip_unless_environ("GALAXY_TEST_ARC_TOKEN")
def test_export_to_writable_repository_creates_lfs_merge_request():
    """Live round trip against a GitLab instance the token can write to.

    Requires ``GALAXY_TEST_ARC_BASE_URL``, ``GALAXY_TEST_ARC_TOKEN`` (``api`` scope) and
    ``GALAXY_TEST_ARC_WRITE_REPO`` (``group/project``). arcfs uploads through a Git LFS pointer
    committed on a new ``run_results`` branch and opens a merge request, so the upload is verified
    through the GitLab API rather than by re-listing the default branch.
    """
    pytest.importorskip("arcfs")
    base_url = os.environ["GALAXY_TEST_ARC_BASE_URL"].rstrip("/")
    token = os.environ["GALAXY_TEST_ARC_TOKEN"]
    repo = os.environ["GALAXY_TEST_ARC_WRITE_REPO"].strip("/")
    file_sources = configured_file_sources(
        [{"type": "arc", "id": "test1", "base_url": base_url, "token": token, "writable": True}]
    )
    user_context = user_context_fixture()

    marker = uuid4().hex
    content = f"galaxy arc export test {marker}\n"
    inside_path = f"galaxy_exports/{marker}.txt"
    write_from(file_sources, f"gxfiles://test1/{repo}{ROOT_MARKER}{inside_path}", content, user_context=user_context)

    api = f"{base_url}/api/v4/projects/{quote(repo, safe='')}"
    headers = {"PRIVATE-TOKEN": token}
    merge_requests = requests.get(f"{api}/merge_requests?state=opened&per_page=100", headers=headers, timeout=30)
    merge_requests.raise_for_status()
    branches = [mr["source_branch"] for mr in merge_requests.json()]
    assert branches, "expected arcfs to open a merge request for the upload"

    for branch in branches:
        raw = requests.get(
            f"{api}/repository/files/{quote(inside_path, safe='')}/raw?ref={quote(branch, safe='')}&lfs=true",
            headers=headers,
            timeout=30,
        )
        if raw.status_code == 200 and raw.text == content:
            pointer = requests.get(
                f"{api}/repository/files/{quote(inside_path, safe='')}/raw?ref={quote(branch, safe='')}",
                headers=headers,
                timeout=30,
            )
            assert pointer.text.startswith("version https://git-lfs.github.com/spec/v1"), "expected an LFS pointer in git"
            return
    pytest.fail(f"uploaded file {inside_path} not found with the expected content on any merge request branch")
