"""Tests for the GitLab file source.

The plugin wraps ``arcfs.fs.GitLabARCFileSystem`` from the optional ``arcfs-fsspec`` package. Most tests
below replace that class with an in-memory fake so they run without the package and without network
access; the last tests talk to a real GitLab instance and are skipped when the package, the site or the
credentials are unavailable.
"""

import asyncio
import logging

import pytest
from multidict import (
    CIMultiDict,
    CIMultiDictProxy,
)

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
from galaxy.files.sources import gitlab
from galaxy.files.sources._fsspec import MAX_ITEMS_LIMIT
from galaxy.files.sources.gitlab import (
    GitLabFilesSource,
    ROOT_MARKER,
)
from galaxy.util.unittest_utils import (
    skip_if_site_down,
    skip_unless_environ,
)
from ._gitlab_fakes import (
    _is_sub_path,
    FAKE_FILES,
    FAKE_TREE,
    FakeRecorder,
    HUGE_TREE,
    install_fake,
    LARGE_TREE,
    response_error,
)
from ._util import (
    assert_realizes_as,
    configured_file_sources,
    user_context_fixture,
)

PUBLIC_GITLAB_URL = "https://gitlab.com"
PUBLIC_DATAHUB_URL = "https://git.nfdi4plants.org"
TRANSIENT_STATUSES = (429, 500, 502, 503, 504)


def _install(monkeypatch, tree, files):
    return install_fake(monkeypatch, gitlab, GitLabFilesSource, tree, files)


@pytest.fixture
def fake_fs(monkeypatch) -> FakeRecorder:
    return _install(monkeypatch, FAKE_TREE, FAKE_FILES)


@pytest.fixture
def large_fake_fs(monkeypatch) -> FakeRecorder:
    return _install(monkeypatch, LARGE_TREE, {})


@pytest.fixture
def huge_fake_fs(monkeypatch) -> FakeRecorder:
    return _install(monkeypatch, HUGE_TREE, {})


def _source_config(**overrides) -> dict:
    config = {"type": "gitlab", "id": "test1", "base_url": "https://gitlab.example.org", "token": "glpat-secret"}
    config.update(overrides)
    return config


def _gitlab_source(conf=None) -> GitLabFilesSource:
    file_sources = configured_file_sources([conf or _source_config()])
    return file_sources.get_file_source_path("gxfiles://test1").file_source


_response_error = response_error


def test_plugin_type():
    assert GitLabFilesSource.plugin_type == "gitlab"
    assert GitLabFilesSource.required_package == "arcfs-fsspec"


def test_reported_writability_follows_the_accessor(fake_fs, monkeypatch):
    """What the source reports must be what it honours, whatever the configuration asked for.

    ``to_dict`` is what fills the client's export pickers. While it reported the configured
    attribute rather than the accessor, a source whose accessor disagreed kept offering itself
    for exports that then died in ``_ensure_writeable`` with a bare HTTP 500. This source honours
    its configuration now, so the disagreement is staged deliberately below; ``commoncrawl``
    still has that shape for real.
    """
    source = _gitlab_source(_source_config(writable=True))
    assert source.get_writable() is True
    assert source.to_dict()["writable"] is True

    monkeypatch.setattr(GitLabFilesSource, "get_writable", lambda self: False)
    assert source.writable is True, "the configured value is untouched, which is what makes this a mismatch"
    assert source.to_dict()["writable"] is False


def test_missing_package_gives_actionable_error(monkeypatch):
    monkeypatch.setattr(gitlab, "GitLabARCFileSystem", None)
    monkeypatch.setattr(GitLabFilesSource, "required_module", None)
    with pytest.raises(Exception, match="arcfs-fsspec"):
        _gitlab_source()


def test_open_fs_passes_config_and_skips_the_instance_cache(fake_fs):
    source = _gitlab_source(_source_config(listings_expiry_time=120))
    source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert len(fake_fs.init_kwargs) == 1
    kwargs = fake_fs.init_kwargs[0]
    assert kwargs["base_url"] == "https://gitlab.example.org"
    assert kwargs["token"] == "glpat-secret"
    assert kwargs["asynchronous"] is False
    # Without this, one request's close() would tear down a filesystem shared with every other.
    assert kwargs["skip_instance_cache"] is True
    # The fsspec cache options are forwarded for consistency with the other fsspec sources, but
    # arcfs replaces fsspec's expiring DirCache with a plain dict and currently ignores them.
    assert kwargs["listings_expiry_time"] == 120
    assert "use_listings_cache" in kwargs


def test_anonymous_access_passes_no_token(fake_fs):
    source = _gitlab_source(_source_config(token=None))
    source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.init_kwargs[0]["token"] is None


def test_paginated_listing_uses_list_page_and_reports_total(fake_fs):
    source = _gitlab_source()
    entries, total = source.list("/", limit=1, offset=1, user_context=user_context_fixture())
    assert fake_fs.list_page_calls == [{"path": "", "offset": 1, "limit": 1}]
    assert fake_fs.ls_calls == []
    assert total == 3
    assert [e.path for e in entries] == ["group/sub/repo2:-:/"]
    assert fake_fs.closed == 1, "the filesystem should be closed after a paginated listing"


def test_unaligned_window_is_requested_as_asked(fake_fs):
    """An offset that is not a multiple of the limit is passed straight through.

    0.1.10 fetched the entire listing for such a window, so Galaxy had to ask for whole
    aligned pages and slice them. 0.1.11 serves any window, so the workaround is gone.
    """
    source = _gitlab_source()
    entries, total = source.list("/", limit=2, offset=1, user_context=user_context_fixture())
    assert [e.path for e in entries] == ["group/sub/repo2:-:/", "other/repo3:-:/"]
    assert total == 3
    assert fake_fs.ls_calls == [], "no request may fall back to a full listing"
    assert fake_fs.list_page_calls == [{"path": "", "offset": 1, "limit": 2}]


def test_unpaginated_listing_is_bounded(fake_fs):
    """``fs.ls()`` reports no total and makes arcfs keep the whole catalogue, so it is not used."""
    source = _gitlab_source()
    entries, total = source.list("/", user_context=user_context_fixture())
    assert fake_fs.ls_calls == []
    assert fake_fs.list_page_calls == [{"path": "", "offset": 0, "limit": MAX_ITEMS_LIMIT}]
    assert total == 3
    assert all(isinstance(e, RemoteDirectory) for e in entries)


def test_large_limit_is_served_in_one_request(large_fake_fs):
    """arcfs splits a window across GitLab pages itself, so Galaxy asks once."""
    source = _gitlab_source()
    entries, total = source.list("/", limit=150, offset=0, user_context=user_context_fixture())
    assert large_fake_fs.list_page_calls == [{"path": "", "offset": 0, "limit": 150}]
    assert large_fake_fs.ls_calls == []
    assert total == 250
    assert len(entries) == 150
    assert len({e.path for e in entries}) == 150, "pages must not repeat entries"
    assert entries[0].name == "group/repo000"
    assert entries[-1].name == "group/repo149"


def test_offset_window_beyond_the_first_page_is_contiguous(large_fake_fs):
    source = _gitlab_source()
    entries, _ = source.list("/", limit=150, offset=100, user_context=user_context_fixture())
    assert [e.name for e in entries][:2] == ["group/repo100", "group/repo101"]
    assert len(entries) == 150


def test_recursive_listing_inside_a_project_uses_walk(fake_fs):
    source = _gitlab_source()
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
    source = _gitlab_source()

    def boom(*args, **kwargs):
        raise FileNotFoundError("4481")

    monkeypatch.setattr(source, "_list_recursive", boom)
    with pytest.raises(ObjectNotFound, match="Not found in") as excinfo:
        source.list("group/repo1:-:/", recursive=True, user_context=user_context_fixture())
    assert fake_fs.closed == 1
    assert "4481" not in str(excinfo.value), "the internal project id must not reach the user"


def test_recursive_listing_of_the_root_is_rejected(fake_fs):
    """fsspec would resolve "/" to arcfs' marker and arcfs would call GitLab's project list endpoint."""
    source = _gitlab_source()
    with pytest.raises(RequestParameterInvalidException, match="single project"):
        source.list("/", recursive=True, limit=10, offset=0, user_context=user_context_fixture())


def test_search_filters_by_name_without_globbing(fake_fs):
    """The generic implementation globs, which needs an ``_info`` that arcfs does not implement."""
    source = _gitlab_source()
    entries, total = source.list("/", query="REPO2", limit=10, offset=0, user_context=user_context_fixture())
    assert [e.name for e in entries] == ["group/sub/repo2"]
    assert total == 1


def test_search_inside_a_project_matches_file_names(fake_fs):
    source = _gitlab_source()
    entries, total = source.list(
        "group/repo1:-:/", query="readme", limit=10, offset=0, user_context=user_context_fixture()
    )
    assert [e.name for e in entries] == ["README.md"]
    assert total == 1


def test_entries_expose_marker_separated_paths_and_uris(fake_fs):
    source = _gitlab_source()
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
    source = _gitlab_source()
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
    source = _gitlab_source()
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
    source = _gitlab_source()
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
    assert GitLabFilesSource._display_name(path) == expected


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


def test_permission_error_becomes_authentication_required(fake_fs):
    """A ``PermissionError`` carrying no filename is GitLab refusing the credentials."""
    fake_fs.list_page_error = PermissionError("401 Unauthorized")
    source = _gitlab_source()
    with pytest.raises(AuthenticationRequired, match="Permission Denied") as excinfo:
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert str(excinfo.value).startswith("Problem listing file source path /.")
    assert fake_fs.closed == 1


@pytest.mark.parametrize("status", [401, 403])
def test_unauthorized_response_becomes_authentication_required(fake_fs, status):
    """GitLab reports a missing or invalid token as an aiohttp error, which is not an OSError."""
    fake_fs.list_page_error = _response_error(status, "Unauthorized")
    source = _gitlab_source()
    with pytest.raises(AuthenticationRequired, match="check your credentials") as excinfo:
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    # Every other branch of the ladder leads with the operation it failed at. A credentials failure
    # that dropped it told the user their token was refused without saying what for, which on an
    # export read as a bare permission complaint about nothing in particular.
    assert str(excinfo.value).startswith("Problem listing file source path /.")


def test_forbidden_response_names_both_kinds_of_token(fake_fs):
    """403 means the token authenticated but is not allowed to do this.

    Which permission is missing depends on the kind of token, and GitLab's own explanation does
    not survive aiohttp, so the message has to cover both rather than assert one. The classic
    scope it names is the one this source needs: reading is all it does, and asking a user to
    mint a write-capable token to browse would contradict its own template help. ``test_arc.py``
    holds the other half, where an export does need the wider scope.
    """
    fake_fs.list_page_error = _response_error(403, "Forbidden")
    source = _gitlab_source()
    with pytest.raises(AuthenticationRequired) as excinfo:
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    message = str(excinfo.value)
    assert message.startswith("Problem listing file source path /."), "the operation must survive both hints"
    assert "'read_api' scope" in message, "a read-only source must not ask for a write scope"
    assert "fine-grained" in message


def test_offset_limit_response_explains_paging_and_the_token_remedy(fake_fs):
    """GitLab answers 405 once an anonymous listing pages past its offset limit.

    The bare status says nothing about paging, and the limit applies only to
    unauthenticated requests, so the message has to supply both.
    """
    fake_fs.list_page_error = _response_error(405, "Method Not Allowed")
    source = _gitlab_source()
    with pytest.raises(MessageException, match="access token") as excinfo:
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert "page" in str(excinfo.value)
    assert "Method Not Allowed" not in str(excinfo.value)


def test_rate_limited_response_passes_on_the_retry_delay(fake_fs):
    """GitLab says how long to wait in Retry-After, which is worth telling the user."""
    error = _response_error(429, "Too Many Requests")
    error.headers = CIMultiDictProxy(CIMultiDict({"Retry-After": "60"}))
    fake_fs.list_page_error = error
    source = _gitlab_source()
    with pytest.raises(MessageException, match="rate limiting") as excinfo:
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert "60 seconds" in str(excinfo.value)


def test_rate_limited_response_without_a_retry_header_still_reads_well(fake_fs):
    fake_fs.list_page_error = _response_error(429, "Too Many Requests")
    source = _gitlab_source()
    with pytest.raises(MessageException, match="rate limiting these requests. Please wait"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())


def test_error_without_any_text_does_not_render_an_empty_reason(fake_fs):
    """Some errors stringify to nothing, which would leave a dangling "Reason: "."""
    fake_fs.list_page_error = TimeoutError()
    source = _gitlab_source()
    with pytest.raises(MessageException, match="Reason: TimeoutError"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())


def test_error_without_a_reason_phrase_does_not_leak_the_api_url(fake_fs):
    """aiohttp leaves ``message`` empty when the server sends no reason phrase.

    The exception itself stringifies to the full internal request URL, so it must
    not be used as a stand-in for the missing text.
    """
    fake_fs.list_page_error = _response_error(401, "")
    source = _gitlab_source()
    with pytest.raises(AuthenticationRequired) as excinfo:
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    message = str(excinfo.value)
    assert "401" in message
    assert "http" not in message, "the internal API URL must not reach the user"
    assert "message=''" not in message


def test_server_error_response_becomes_message_exception(fake_fs):
    fake_fs.list_page_error = _response_error(500, "Internal Server Error")
    source = _gitlab_source()
    with pytest.raises(MessageException, match="Problem listing file source path"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())


def test_missing_or_empty_project_becomes_object_not_found(fake_fs):
    """arcfs reports an ARC without commits, or one it cannot see, as a FileNotFoundError."""
    fake_fs.list_page_error = FileNotFoundError("4481")
    source = _gitlab_source()
    with pytest.raises(ObjectNotFound, match="Not found in") as excinfo:
        source.list("group/newarc:-:/", limit=5, offset=0, user_context=user_context_fixture())
    assert "4481" not in str(excinfo.value), "the internal project id must not reach the user"


def test_other_errors_become_message_exception(fake_fs):
    fake_fs.list_page_error = RuntimeError("GitLab exploded")
    source = _gitlab_source()
    with pytest.raises(MessageException, match="Problem listing file source path"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())


def test_window_beyond_the_listing_cap_still_returns_entries(huge_fake_fs):
    """Reading only the pages that cover the window keeps far pages reachable and cheap."""
    source = _gitlab_source()
    entries, total = source.list("/", limit=200, offset=1000, user_context=user_context_fixture())
    assert len(entries) == 200
    assert entries[0].name == "group/repo1000"
    assert entries[-1].name == "group/repo1199"
    assert total == 1500
    # Only the pages covering the window, not a walk from the beginning.
    assert [call["offset"] for call in huge_fake_fs.list_page_calls] == [1000]


def test_window_past_the_end_reports_the_real_total(huge_fake_fs):
    """A pager told there are more entries than exist keeps offering empty pages."""
    source = _gitlab_source()
    entries, total = source.list("/", limit=150, offset=2000, user_context=user_context_fixture())
    assert entries == []
    assert total == 1500


def test_a_satisfied_window_does_not_warn_about_the_item_cap(large_fake_fs, caplog):
    source = _gitlab_source()
    with caplog.at_level(logging.WARNING):
        entries, _ = source.list("/", limit=101, offset=0, user_context=user_context_fixture())
    assert len(entries) == 101
    assert "exceeded maximum items" not in caplog.text


def test_unpaginated_listing_warns_when_it_truncates(huge_fake_fs, caplog):
    source = _gitlab_source()
    with caplog.at_level(logging.WARNING):
        entries, total = source.list("/", user_context=user_context_fixture())
    assert len(entries) == 1000
    assert total == 1500
    assert "exceeded maximum items" in caplog.text


def test_local_file_errors_are_not_blamed_on_the_server(fake_fs, monkeypatch):
    """A missing staging directory is not a missing ARC, and must not leak the server path."""
    source = _gitlab_source()

    def missing_local_file(rpath, lpath, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", "/srv/galaxy/tmp/staging/tmp123")

    monkeypatch.setattr(source, "_open_fs", lambda *a, **k: _LocalFailureFs(missing_local_file, fake_fs))
    with pytest.raises(MessageException) as caught:
        source.realize_to(
            "group/repo1:-:/README.md", "/srv/galaxy/tmp/staging/tmp123", user_context=user_context_fixture()
        )
    message = str(caught.value)
    assert "project may be empty" not in message
    assert "check your credentials" not in message
    assert "/srv/galaxy/tmp/staging" not in message


def test_local_permission_errors_are_not_blamed_on_the_credentials(fake_fs, monkeypatch):
    """A staged file Galaxy may not read is not a token GitLab refused.

    Both reach the handler as a ``PermissionError`` and only the filename tells them apart. This
    matters most on the ARC write path, where ``put_file`` reads a dataset Galaxy staged for it:
    were the two arms reordered, or the filename check dropped, a server-side disk permission
    problem would send the user off to check a token that is fine, and would print the staging
    path to them on the way.
    """
    source = _gitlab_source()

    def unreadable_local_file(rpath, lpath, **kwargs):
        raise PermissionError(13, "Permission denied", "/srv/galaxy/tmp/staging/tmp123")

    monkeypatch.setattr(source, "_open_fs", lambda *a, **k: _LocalFailureFs(unreadable_local_file, fake_fs))
    with pytest.raises(MessageException) as caught:
        source.realize_to(
            "group/repo1:-:/README.md", "/srv/galaxy/tmp/staging/tmp123", user_context=user_context_fixture()
        )
    # ``AuthenticationRequired`` is a ``MessageException``, so the type raised has to be asserted
    # on rather than left to ``pytest.raises`` above.
    assert not isinstance(caught.value, AuthenticationRequired)
    message = str(caught.value)
    assert message.startswith("Problem reading file source path group/repo1:-:/README.md.")
    # The OS' own reason is the only useful thing here, so it has to survive too.
    assert "Reason: Permission denied" in message
    assert "check your credentials" not in message
    # The credentials arm renders the exception itself, which for this errno form carries the path.
    assert "/srv/galaxy/tmp/staging" not in message
    assert fake_fs.closed == 1


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
    file_sources = configured_file_sources([{"type": "gitlab", "id": "test1", "base_url": PUBLIC_DATAHUB_URL}])
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


def test_recursive_listing_honours_a_query(fake_fs):
    """A recursive search must filter, not return the whole subtree as if it matched."""
    source = _gitlab_source()
    entries, total = source.list(
        "group/repo1:-:/",
        recursive=True,
        query="README",
        limit=10,
        offset=0,
        user_context=user_context_fixture(),
    )
    assert [e.name for e in entries] == ["README.md"]
    assert total == 1


def test_search_treats_wildcards_literally(fake_fs):
    """Documents the behaviour: search is a substring match, not a glob.

    The base class preserves ``*`` and ``?`` as wildcards, but arcfs has no ``_info`` for
    globbing, so this source filters by name instead. A user typing a wildcard gets no
    matches rather than an error.
    """
    source = _gitlab_source()
    plain, _ = source.list("/", query="repo", limit=10, offset=0, user_context=user_context_fixture())
    assert len(plain) == 3

    for pattern in ("*repo*", "re?o"):
        starred, total = source.list("/", query=pattern, limit=10, offset=0, user_context=user_context_fixture())
        assert starred == [], f"{pattern} is matched literally, not as a glob"
        assert total == 0


def test_read_listing_does_not_narrow_to_own_projects(fake_fs):
    """Browsing and importing is the primary use, and public ARCs must stay visible."""
    source = _gitlab_source()
    source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.list_page_membership == [False]
