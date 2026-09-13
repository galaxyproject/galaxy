"""Tests for the ARC (DataHUB/GitLab) file source.

The plugin wraps ``arcfs.fs.GitLabARCFileSystem`` from the optional ``arcfs-fsspec`` package. Most tests
below replace that class with an in-memory fake so they run without the package and without network
access; the last tests talk to a real GitLab instance and are skipped when the package, the site or the
credentials are unavailable.
"""

import asyncio
import logging
import os
from urllib.parse import quote
from uuid import uuid4

import pytest
from aiohttp import (
    ClientResponseError,
    RequestInfo,
)
from multidict import (
    CIMultiDict,
    CIMultiDictProxy,
)
from yarl import URL

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.files.models import (
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.sources import arc
from galaxy.files.sources.arc import (
    ARCFilesSource,
    GITLAB_MAX_PER_PAGE,
    ROOT_MARKER,
)
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
EXPORT_ENV_VARS = ("GALAXY_TEST_ARC_BASE_URL", "GALAXY_TEST_ARC_TOKEN", "GALAXY_TEST_ARC_WRITE_REPO")
TRANSIENT_STATUSES = (429, 500, 502, 503, 504)

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
# A catalogue larger than a single GitLab page, to exercise multi-page assembly.
LARGE_TREE = {"": [{"name": f"group/repo{i:03d}:-:", "type": "directory"} for i in range(250)]}
# Larger than MAX_ITEMS_LIMIT, so windows beyond that bound can be exercised.
HUGE_TREE = {"": [{"name": f"group/repo{i:04d}:-:", "type": "directory"} for i in range(1500)]}


class FakeRecorder:
    def __init__(self):
        self.init_kwargs: list[dict] = []
        self.ls_calls: list[str] = []
        self.list_page_calls: list[dict] = []
        self.walk_calls: list[str] = []
        self.get_file_calls: list[tuple[str, str]] = []
        self.put_file_calls: list[tuple[str, str]] = []
        self.closed = 0
        self.list_page_error: Exception | None = None


def _make_fake_fs_class(recorder: FakeRecorder, tree: dict, files: dict):
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
            entries = tree.get(key, [])
            return entries if detail else [e["name"] for e in entries]

        def list_page(self, path, detail=True, *, offset=0, limit=50, **kwargs):
            key = self._key(path)
            recorder.list_page_calls.append({"path": key, "offset": offset, "limit": limit})
            if recorder.list_page_error is not None:
                raise recorder.list_page_error
            entries = tree.get(key, [])
            if limit > 0 and offset % limit != 0:
                # arcfs can only map a window onto a GitLab page when the offset is a multiple of
                # the limit; anything else makes it fetch and keep the whole listing.
                recorder.ls_calls.append(key)
            return entries[offset : offset + limit], len(entries)

        def walk(self, path, detail=True, **kwargs):
            # fsspec's walk descends into every subdirectory, so the fake has to as well.
            pending = [self._key(path)]
            while pending:
                key = pending.pop(0)
                recorder.walk_calls.append(key)
                entries = tree.get(key, [])
                dirs = {e["name"]: e for e in entries if e["type"] == "directory"}
                found = {e["name"]: e for e in entries if e["type"] == "file"}
                yield key, dirs, found
                pending.extend(dirs)

        def get_file(self, rpath, lpath, **kwargs):
            key = self._key(rpath)
            recorder.get_file_calls.append((key, lpath))
            with open(lpath, "w") as f:
                f.write(files[key])

        def put_file(self, lpath, rpath, **kwargs):
            recorder.put_file_calls.append((lpath, self._key(rpath)))

        def close(self):
            recorder.closed += 1

    return FakeGitLabARCFileSystem


def _install_fake(monkeypatch, tree: dict, files: dict) -> FakeRecorder:
    recorder = FakeRecorder()
    fake_class = _make_fake_fs_class(recorder, tree, files)
    # Both names matter: ``_open_fs`` reads the module-level name, and ``FsspecFilesSource.__init__``
    # refuses to construct the plugin when ``required_module`` is None.
    monkeypatch.setattr(arc, "GitLabARCFileSystem", fake_class)
    monkeypatch.setattr(ARCFilesSource, "required_module", fake_class)
    return recorder


@pytest.fixture
def fake_fs(monkeypatch) -> FakeRecorder:
    return _install_fake(monkeypatch, FAKE_TREE, FAKE_FILES)


@pytest.fixture
def large_fake_fs(monkeypatch) -> FakeRecorder:
    return _install_fake(monkeypatch, LARGE_TREE, {})


@pytest.fixture
def huge_fake_fs(monkeypatch) -> FakeRecorder:
    return _install_fake(monkeypatch, HUGE_TREE, {})


def _source_config(**overrides) -> dict:
    config = {"type": "arc", "id": "test1", "base_url": "https://datahub.example.org", "token": "glpat-secret"}
    config.update(overrides)
    return config


def _arc_source(conf=None) -> ARCFilesSource:
    file_sources = configured_file_sources([conf or _source_config()])
    return file_sources.get_file_source_path("gxfiles://test1").file_source


def _response_error(status: int, message: str) -> ClientResponseError:
    """Build the error aiohttp raises for a non-2xx GitLab response."""
    url = URL("https://datahub.example.org/api/v4/projects")
    headers: CIMultiDictProxy[str] = CIMultiDictProxy(CIMultiDict())
    request_info = RequestInfo(url=url, method="GET", headers=headers, real_url=url)
    return ClientResponseError(request_info, (), status=status, message=message)


def _is_sub_path(origin: str, destination: str) -> bool:
    """Mirror the client's ``isSubPath`` (client/src/components/FilesDialog/utilities.ts).

    The file dialog decides which entries belong to a directory with this comparison, so an ARC's
    entries have to satisfy it for recursive selection to behave.
    """

    def with_trailing_slash(path: str) -> str:
        return path if path.endswith("/") else f"{path}/"

    origin, destination = with_trailing_slash(origin), with_trailing_slash(destination)
    return origin != destination and destination.startswith(origin)


def test_plugin_type():
    assert ARCFilesSource.plugin_type == "arc"
    assert ARCFilesSource.required_package == "arcfs-fsspec"


def test_missing_package_gives_actionable_error(monkeypatch):
    monkeypatch.setattr(arc, "GitLabARCFileSystem", None)
    monkeypatch.setattr(ARCFilesSource, "required_module", None)
    with pytest.raises(Exception, match="arcfs-fsspec"):
        _arc_source()


def test_open_fs_passes_config_and_skips_the_instance_cache(fake_fs):
    source = _arc_source(_source_config(listings_expiry_time=120))
    source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert len(fake_fs.init_kwargs) == 1
    kwargs = fake_fs.init_kwargs[0]
    assert kwargs["base_url"] == "https://datahub.example.org"
    assert kwargs["token"] == "glpat-secret"
    assert kwargs["asynchronous"] is False
    # Without this, one request's close() would tear down a filesystem shared with every other.
    assert kwargs["skip_instance_cache"] is True
    # The fsspec cache options are forwarded for consistency with the other fsspec sources, but
    # arcfs replaces fsspec's expiring DirCache with a plain dict and currently ignores them.
    assert kwargs["listings_expiry_time"] == 120
    assert "use_listings_cache" in kwargs


def test_anonymous_access_passes_no_token(fake_fs):
    source = _arc_source(_source_config(token=None))
    source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.init_kwargs[0]["token"] is None


def test_paginated_listing_uses_list_page_and_reports_total(fake_fs):
    source = _arc_source()
    entries, total = source.list("/", limit=1, offset=1, user_context=user_context_fixture())
    assert fake_fs.list_page_calls == [{"path": "", "offset": 1, "limit": 1}]
    assert fake_fs.ls_calls == []
    assert total == 3
    assert [e.path for e in entries] == ["group/sub/repo2:-:/"]
    assert fake_fs.closed == 1, "the filesystem should be closed after a paginated listing"


def test_window_arcfs_cannot_page_is_read_as_whole_pages(fake_fs):
    """arcfs fetches the entire listing unless the offset is a multiple of the limit."""
    source = _arc_source()
    entries, total = source.list("/", limit=2, offset=1, user_context=user_context_fixture())
    assert [e.path for e in entries] == ["group/sub/repo2:-:/", "other/repo3:-:/"]
    assert total == 3
    assert fake_fs.ls_calls == [], "no request may fall back to a full listing"
    assert all(call["offset"] % call["limit"] == 0 for call in fake_fs.list_page_calls)


def test_unpaginated_listing_is_assembled_from_pages(fake_fs):
    """``fs.ls()`` would make arcfs fetch and retain the whole catalogue and reports no total."""
    source = _arc_source()
    entries, total = source.list("/", user_context=user_context_fixture())
    assert fake_fs.ls_calls == []
    assert fake_fs.list_page_calls == [{"path": "", "offset": 0, "limit": GITLAB_MAX_PER_PAGE}]
    assert total == 3
    assert all(isinstance(e, RemoteDirectory) for e in entries)


def test_large_limit_is_assembled_from_capped_pages(large_fake_fs):
    """GitLab caps ``per_page`` at 100, so a bigger page must be built from several requests."""
    source = _arc_source()
    entries, total = source.list("/", limit=150, offset=0, user_context=user_context_fixture())
    assert all(call["limit"] <= GITLAB_MAX_PER_PAGE for call in large_fake_fs.list_page_calls)
    assert large_fake_fs.ls_calls == []
    assert total == 250
    assert len(entries) == 150
    assert len({e.path for e in entries}) == 150, "pages must not repeat entries"
    assert entries[0].name == "group/repo000"
    assert entries[-1].name == "group/repo149"


def test_offset_window_beyond_the_first_page_is_contiguous(large_fake_fs):
    source = _arc_source()
    entries, _ = source.list("/", limit=150, offset=100, user_context=user_context_fixture())
    assert [e.name for e in entries][:2] == ["group/repo100", "group/repo101"]
    assert len(entries) == 150


def test_recursive_listing_inside_a_project_uses_walk(fake_fs):
    source = _arc_source()
    entries, _ = source.list("group/repo1:-:/", recursive=True, limit=10, offset=0, user_context=user_context_fixture())
    assert fake_fs.list_page_calls == []
    assert fake_fs.walk_calls == ["group/repo1:-:", "group/repo1:-:assays"]
    assert {e.path for e in entries} == {
        "group/repo1:-:/README.md",
        "group/repo1:-:/assays",
        "group/repo1:-:/assays/measurements.csv",
    }
    assert fake_fs.closed == 1, "a recursive listing must close the filesystem too"


def test_recursive_listing_translates_errors(fake_fs, monkeypatch):
    """Recursion must go through the same error handling as every other operation."""
    source = _arc_source()

    def boom(*args, **kwargs):
        raise FileNotFoundError("4481")

    monkeypatch.setattr(source, "_list_recursive", boom)
    with pytest.raises(ObjectNotFound, match="4481"):
        source.list("group/repo1:-:/", recursive=True, user_context=user_context_fixture())
    assert fake_fs.closed == 1


def test_recursive_listing_of_the_root_is_rejected(fake_fs):
    """fsspec would resolve "/" to arcfs' marker and arcfs would call GitLab's project list endpoint."""
    source = _arc_source()
    with pytest.raises(RequestParameterInvalidException, match="single ARC"):
        source.list("/", recursive=True, limit=10, offset=0, user_context=user_context_fixture())


def test_search_filters_by_name_without_globbing(fake_fs):
    """The generic implementation globs, which needs an ``_info`` that arcfs does not implement."""
    source = _arc_source()
    entries, total = source.list("/", query="REPO2", limit=10, offset=0, user_context=user_context_fixture())
    assert [e.name for e in entries] == ["group/sub/repo2"]
    assert total == 1


def test_search_inside_a_project_matches_file_names(fake_fs):
    source = _arc_source()
    entries, total = source.list(
        "group/repo1:-:/", query="readme", limit=10, offset=0, user_context=user_context_fixture()
    )
    assert [e.name for e in entries] == ["README.md"]
    assert total == 1


def test_entries_expose_marker_separated_paths_and_uris(fake_fs):
    source = _arc_source()
    root, _ = source.list("/", limit=10, offset=0, user_context=user_context_fixture())
    assert [e.name for e in root] == ["group/repo1", "group/sub/repo2", "other/repo3"]
    repo = next(e for e in root if isinstance(e, RemoteDirectory))
    assert repo.path == "group/repo1:-:/"
    # ``uri_join`` drops the trailing slash of the project URI; the client re-adds one before
    # comparing, so what matters is the separator in the paths of the entries inside it.
    assert repo.uri == "gxfiles://test1/group/repo1:-:"

    inside, total = source.list(repo.path, limit=10, offset=0, user_context=user_context_fixture())
    assert total == 2
    readme = next(e for e in inside if isinstance(e, RemoteFile))
    assert readme.name == "README.md"
    assert readme.path == "group/repo1:-:/README.md"
    # A project's path is a prefix of the paths inside it, which is what the client's tree
    # selection relies on to recognise them as its children.
    assert readme.path.startswith(repo.path)
    assays = next(e for e in inside if isinstance(e, RemoteDirectory))
    assert assays.name == "assays"
    assert assays.path == "group/repo1:-:/assays"
    assert assays.path.startswith(repo.path)

    # The file dialog only treats entries as children of the ARC when this holds.
    assert _is_sub_path(repo.uri, readme.uri)
    assert _is_sub_path(repo.uri, assays.uri)
    assert not _is_sub_path(readme.uri, assays.uri)

    deeper, _ = source.list(assays.path, limit=10, offset=0, user_context=user_context_fixture())
    assert [(e.name, e.path) for e in deeper] == [("measurements.csv", "group/repo1:-:/assays/measurements.csv")]


def test_uri_last_segment_is_the_file_name(fake_fs):
    """Callers that derive a dataset name from the URI split it on "/" and take the last segment."""
    source = _arc_source()
    inside, _ = source.list("group/repo1:-:/", limit=10, offset=0, user_context=user_context_fixture())
    readme = next(e for e in inside if isinstance(e, RemoteFile))
    assert readme.uri.split("/")[-1] == "README.md"


@pytest.mark.parametrize(
    "galaxy_path, filesystem_path",
    [
        ("/", "/"),
        ("group/repo:-:/", "group/repo:-:"),
        ("group/repo:-:/README.md", "group/repo:-:README.md"),
        ("group/repo:-:/assays/data.csv", "group/repo:-:assays/data.csv"),
        # Paths recorded before the separator was introduced still resolve.
        ("group/repo:-:README.md", "group/repo:-:README.md"),
    ],
)
def test_filesystem_path_conversion(fake_fs, galaxy_path, filesystem_path):
    source = _arc_source()
    # config is unused by this transform; None is fine at runtime.
    assert source._to_filesystem_path(galaxy_path, None) == filesystem_path  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "filesystem_path, galaxy_path",
    [
        ("group/repo:-:", "group/repo:-:/"),
        ("group/repo:-:README.md", "group/repo:-:/README.md"),
        ("plain/path.txt", "plain/path.txt"),
    ],
)
def test_entry_path_conversion(fake_fs, filesystem_path, galaxy_path):
    source = _arc_source()
    assert source._adapt_entry_path(filesystem_path, None) == galaxy_path  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "path, expected",
    [
        ("group/repo:-:", "group/repo"),
        ("group/sub/repo:-:", "group/sub/repo"),
        ("group/repo:-:/", "group/repo"),
        ("group/repo:-:README.md", "README.md"),
        ("group/repo:-:/README.md", "README.md"),
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
        "gxfiles://test1/group/repo1:-:/assays/measurements.csv",
        "a,b\n1,2\n",
        user_context=user_context_fixture(),
    )
    assert fake_fs.get_file_calls[0][0] == "group/repo1:-:assays/measurements.csv"
    assert fake_fs.closed == 1, "the filesystem should be closed after a download"


def test_write_from_uploads_through_put_file(fake_fs):
    file_sources = configured_file_sources([_source_config(writable=True)])
    write_from(
        file_sources,
        "gxfiles://test1/group/repo1:-:/galaxy_exports/result.txt",
        "result\n",
        user_context=user_context_fixture(),
    )
    assert fake_fs.put_file_calls[0][1] == "group/repo1:-:galaxy_exports/result.txt"
    assert fake_fs.closed == 1, "the filesystem should be closed after an upload"


def test_permission_error_becomes_authentication_required(fake_fs):
    fake_fs.list_page_error = PermissionError("401 Unauthorized")
    source = _arc_source()
    with pytest.raises(AuthenticationRequired, match="Permission Denied"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.closed == 1


@pytest.mark.parametrize("status", [401, 403])
def test_unauthorized_response_becomes_authentication_required(fake_fs, status):
    """GitLab reports a missing or invalid token as an aiohttp error, which is not an OSError."""
    fake_fs.list_page_error = _response_error(status, "Unauthorized")
    source = _arc_source()
    with pytest.raises(AuthenticationRequired, match="check your credentials"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())


def test_server_error_response_becomes_message_exception(fake_fs):
    fake_fs.list_page_error = _response_error(500, "Internal Server Error")
    source = _arc_source()
    with pytest.raises(MessageException, match="Problem listing file source path"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())


def test_missing_or_empty_project_becomes_object_not_found(fake_fs):
    """arcfs reports an ARC without commits, or one it cannot see, as a FileNotFoundError."""
    fake_fs.list_page_error = FileNotFoundError("4481")
    source = _arc_source()
    with pytest.raises(ObjectNotFound, match="4481"):
        source.list("group/newarc:-:/", limit=5, offset=0, user_context=user_context_fixture())


def test_other_errors_become_message_exception(fake_fs):
    fake_fs.list_page_error = RuntimeError("GitLab exploded")
    source = _arc_source()
    with pytest.raises(MessageException, match="Problem listing file source path"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())


def test_window_beyond_the_listing_cap_still_returns_entries(huge_fake_fs):
    """Reading only the pages that cover the window keeps far pages reachable and cheap."""
    source = _arc_source()
    entries, total = source.list("/", limit=200, offset=1000, user_context=user_context_fixture())
    assert len(entries) == 200
    assert entries[0].name == "group/repo1000"
    assert entries[-1].name == "group/repo1199"
    assert total == 1500
    # Only the pages covering the window, not a walk from the beginning.
    assert [call["offset"] for call in huge_fake_fs.list_page_calls] == [1000, 1100]


def test_window_past_the_end_reports_the_real_total(huge_fake_fs):
    """A pager told there are more entries than exist keeps offering empty pages."""
    source = _arc_source()
    entries, total = source.list("/", limit=150, offset=2000, user_context=user_context_fixture())
    assert entries == []
    assert total == 1500


def test_a_satisfied_window_does_not_warn_about_the_item_cap(large_fake_fs, caplog):
    source = _arc_source()
    with caplog.at_level(logging.WARNING):
        entries, _ = source.list("/", limit=101, offset=0, user_context=user_context_fixture())
    assert len(entries) == 101
    assert "exceeded maximum items" not in caplog.text


def test_unpaginated_listing_warns_when_it_truncates(huge_fake_fs, caplog):
    source = _arc_source()
    with caplog.at_level(logging.WARNING):
        entries, total = source.list("/", user_context=user_context_fixture())
    assert len(entries) == 1000
    assert total == 1500
    assert "exceeded maximum items" in caplog.text


def test_local_file_errors_are_not_blamed_on_the_arc(fake_fs, monkeypatch):
    """A missing staging directory is not a missing ARC, and must not leak the server path."""
    source = _arc_source()

    def missing_local_file(rpath, lpath, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", "/srv/galaxy/tmp/staging/tmp123")

    monkeypatch.setattr(source, "_open_fs", lambda *a, **k: _LocalFailureFs(missing_local_file, fake_fs))
    with pytest.raises(MessageException) as caught:
        source.realize_to(
            "group/repo1:-:/README.md", "/srv/galaxy/tmp/staging/tmp123", user_context=user_context_fixture()
        )
    message = str(caught.value)
    assert "ARC may be empty" not in message
    assert "check your credentials" not in message
    assert "/srv/galaxy/tmp/staging" not in message


class _LocalFailureFs:
    """Filesystem whose download fails the way a local path problem does."""

    def __init__(self, get_file, recorder):
        self.get_file = get_file
        self._recorder = recorder

    def close(self):
        self._recorder.closed += 1


# --- live tests against real GitLab instances ---


def _skip_if_transient(e: Exception):
    """Skip on infrastructure failures only, decided from the exception chain rather than its text.

    Matching substrings against the message would also match project ids and paths in the URL that
    the error embeds, turning genuine failures into silent skips.
    """
    cause = e.__cause__ or e
    status = getattr(cause, "status", None)
    if status in TRANSIENT_STATUSES:
        pytest.skip(f"DataHUB returned HTTP {status}: {e}")
    if isinstance(cause, asyncio.TimeoutError) or (
        isinstance(cause, OSError) and not isinstance(cause, FileNotFoundError)
    ):
        pytest.skip(f"DataHUB unreachable: {e}")


@skip_unless_environ("GALAXY_TEST_ARC_LIVE")
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
    assert all(isinstance(r, RemoteDirectory) and r.path.endswith(f"{ROOT_MARKER}/") for r in repos)
    assert all(ROOT_MARKER not in r.name for r in repos)

    # The most recently active public ARCs are an arbitrary set: some are empty, some are visible
    # but members-only. Walk them until one yields a file, and only fail if every one errored.
    first_error: MessageException | None = None
    for repo in repos:
        try:
            entries, _ = source.list(repo.path, limit=20, offset=0, user_context=user_context)
        except MessageException as e:
            _skip_if_transient(e)
            first_error = first_error or e
            continue
        remote_file = next((e for e in entries if isinstance(e, RemoteFile)), None)
        if remote_file is None:
            continue
        assert remote_file.uri.startswith("gxfiles://test1/")
        assert remote_file.path.startswith(repo.path)
        contents = _realize_bytes(file_sources, remote_file.uri, user_context)
        assert contents, f"downloaded {remote_file.uri} but it was empty"
        return
    if first_error is not None:
        raise first_error
    pytest.skip("none of the most recently active public ARCs contained a top-level file")


def _realize_bytes(file_sources, uri: str, user_context) -> bytes:
    import tempfile

    file_source_path = file_sources.get_file_source_path(uri)
    with tempfile.NamedTemporaryFile() as temp:
        file_source_path.file_source.realize_to(file_source_path.path, temp.name, user_context=user_context)
        with open(temp.name, "rb") as f:
            return f.read()


@pytest.mark.skipif(
    not all(os.environ.get(name) for name in EXPORT_ENV_VARS),
    reason=f"all of {', '.join(EXPORT_ENV_VARS)} must be set for this test",
)
def test_export_to_writable_repository_creates_lfs_merge_request():
    """Live round trip against a GitLab instance the token can write to.

    arcfs uploads through a Git LFS pointer committed on a new ``run_results`` branch and opens a
    merge request, so the upload is verified through the GitLab API rather than by re-listing the
    default branch, where the file deliberately does not appear.
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
    write_from(file_sources, f"gxfiles://test1/{repo}{ROOT_MARKER}/{inside_path}", content, user_context=user_context)

    api = f"{base_url}/api/v4/projects/{quote(repo, safe='')}"
    headers = {"PRIVATE-TOKEN": token}
    merge_requests = requests.get(f"{api}/merge_requests?state=opened&per_page=100", headers=headers, timeout=30)
    merge_requests.raise_for_status()
    branches = [mr["source_branch"] for mr in merge_requests.json()]
    assert branches, "expected arcfs to open a merge request for the upload"

    quoted_path = quote(inside_path, safe="")
    for branch in branches:
        reference = quote(branch, safe="")
        raw = requests.get(
            f"{api}/repository/files/{quoted_path}/raw?ref={reference}&lfs=true", headers=headers, timeout=30
        )
        if raw.status_code == 200 and raw.text == content:
            pointer = requests.get(
                f"{api}/repository/files/{quoted_path}/raw?ref={reference}", headers=headers, timeout=30
            )
            assert pointer.text.startswith(
                "version https://git-lfs.github.com/spec/v1"
            ), "expected git to hold an LFS pointer"
            return
    pytest.fail(f"uploaded file {inside_path} not found with the expected content on any merge request branch")
