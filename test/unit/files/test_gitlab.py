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
    ConfigDoesNotAllowException,
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


def test_missing_package_gives_actionable_error(monkeypatch):
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
    # The fsspec cache options are forwarded for consistency with the other fsspec sources. They
    # reach a real expiring DirCache and arcfs does read and write it, but nothing is cached in
    # practice: _open_fs builds a filesystem per operation and _filesystem closes it afterwards,
    # so no entry outlives the request that made it.
    assert kwargs["listings_expiry_time"] == 120
    assert "use_listings_cache" in kwargs


def test_recursive_listing_inside_a_project_descends_with_ls(fake_fs):
    """It walks with its own stack, because fsspec drops on_error below the top level."""
    source = _gitlab_source()
    entries, _ = source.list("group/repo1:-:/", recursive=True, limit=10, offset=0, user_context=user_context_fixture())
    assert fake_fs.list_page_calls == []
    assert fake_fs.walk_calls == [], "fsspec's walk cannot carry on_error into its recursion"
    assert sorted(fake_fs.ls_calls) == ["group/repo1:-:", "group/repo1:-:assays"]
    assert {e.path for e in entries} == {
        "group/repo1:-:/README.md",
        "group/repo1:-:/assays",
        "group/repo1:-:/assays/measurements.csv",
    }
    assert fake_fs.closed == 1, "a recursive listing must close the filesystem too"


def test_a_failure_below_the_top_level_is_not_swallowed(fake_fs):
    """fsspec's walk drops on_error when it recurses, so only the top level was ever guarded.

    It swallows every OSError, and aiohttp's connection errors are OSError subclasses, so a
    reset partway through a recursive listing returned the remaining folders empty with HTTP
    200 and nothing to say anything was missing. A test that fails the top level proves
    nothing, because that one level did raise.
    """
    fake_fs.ls_error_for = {"group/repo1:-:assays": ConnectionResetError("connection reset")}
    source = _gitlab_source()

    with pytest.raises(MessageException):
        source.list("group/repo1:-:/", recursive=True, limit=10, offset=0, user_context=user_context_fixture())


def test_recursive_listing_of_the_root_is_rejected(fake_fs):
    """fsspec would resolve "/" to arcfs' marker and arcfs would call GitLab's project list endpoint."""
    source = _gitlab_source()
    with pytest.raises(RequestParameterInvalidException, match="single project"):
        source.list("/", recursive=True, limit=10, offset=0, user_context=user_context_fixture())


@pytest.mark.parametrize("query,names", [("REPO2", ["group/sub/repo2"]), ("repo*", [])])
def test_search_filters_by_name_without_globbing(fake_fs, query, names):
    """The generic implementation globs, which needs an ``_info`` that arcfs does not implement.

    So a wildcard is matched literally rather than expanded.
    """
    source = _gitlab_source()
    entries, total = source.list("/", query=query, limit=10, offset=0, user_context=user_context_fixture())
    assert [e.name for e in entries] == names
    assert total == len(names)


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


@pytest.mark.parametrize(
    "error,expected,must_say,must_not_say",
    [
        # A PermissionError with no filename is GitLab refusing the credentials, not the disk.
        (PermissionError("401 Unauthorized"), AuthenticationRequired, "Permission Denied", None),
        (_response_error(401, "Unauthorized"), AuthenticationRequired, "check your credentials", None),
        # 403 means the token authenticated but may not do this, and which permission is missing
        # depends on the kind of token, so both are named. read_api because reading is all this
        # source does; asking for a write scope would contradict its own template help.
        (_response_error(403, "Forbidden"), AuthenticationRequired, "'read_api' scope", None),
        (_response_error(403, "Forbidden"), AuthenticationRequired, "fine-grained", None),
        # 405 is GitLab refusing to page an anonymous listing any further. The bare status says
        # nothing about paging, and a token lifts the limit, so the message supplies both.
        (_response_error(405, "Method Not Allowed"), MessageException, "access token", "Method Not Allowed"),
        (
            _response_error(429, "Too Many Requests"),
            MessageException,
            "rate limiting these requests. Please wait",
            None,
        ),
        # Some errors stringify to nothing, which would leave a dangling "Reason: ".
        (TimeoutError(), MessageException, "Reason: TimeoutError", None),
        # aiohttp leaves message empty when the server sends no reason phrase, and the exception
        # itself stringifies to the internal request URL, so that must not stand in for it.
        (_response_error(401, ""), AuthenticationRequired, "401", "http"),
        (_response_error(500, "Internal Server Error"), MessageException, "Problem listing", None),
        (RuntimeError("GitLab exploded"), MessageException, "Problem listing", None),
    ],
)
def test_the_error_ladder_translates_what_the_backend_raises(fake_fs, error, expected, must_say, must_not_say):
    """Every branch leads with the operation it failed at, so a refusal names what it was for."""
    fake_fs.list_page_error = error
    source = _gitlab_source()
    with pytest.raises(expected) as excinfo:
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    message = str(excinfo.value)
    assert message.startswith("Problem listing file source path /.")
    assert must_say in message
    if must_not_say:
        assert must_not_say not in message
    assert fake_fs.closed == 1, "the filesystem must be closed however the operation ended"


def test_a_rate_limit_passes_on_the_retry_delay(fake_fs):
    """GitLab says how long to wait in Retry-After, which is worth telling the user."""
    error = _response_error(429, "Too Many Requests")
    error.headers = CIMultiDictProxy(CIMultiDict({"Retry-After": "60"}))
    fake_fs.list_page_error = error
    source = _gitlab_source()
    with pytest.raises(MessageException, match="rate limiting") as excinfo:
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert "60 seconds" in str(excinfo.value)


def test_a_missing_or_empty_project_becomes_object_not_found(fake_fs):
    """arcfs reports a project without commits, or one it cannot see, as FileNotFoundError."""
    fake_fs.list_page_error = FileNotFoundError("4481")
    source = _gitlab_source()
    with pytest.raises(ObjectNotFound, match="Not found in") as excinfo:
        source.list("group/newarc:-:/", limit=5, offset=0, user_context=user_context_fixture())
    assert "4481" not in str(excinfo.value), "the internal project id must not reach the user"


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


def test_unpaginated_listing_warns_when_it_truncates(huge_fake_fs, caplog):
    source = _gitlab_source()
    with caplog.at_level(logging.WARNING):
        entries, total = source.list("/", user_context=user_context_fixture())
    # The cap is a shared constant; naming it here rather than its value keeps this test honest
    # when it changes, as it did from 1000 to 500.
    assert len(entries) == MAX_ITEMS_LIMIT
    assert total == 1500
    assert "exceeded maximum items" in caplog.text


def test_local_errors_are_not_blamed_on_the_server(fake_fs, monkeypatch):
    """A missing staging directory is not a missing project, and must not leak the server path."""
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


class _LocalFailureFs:
    """Filesystem whose download fails the way a local path problem does."""

    def __init__(self, get_file, recorder):
        self.get_file = get_file
        self._recorder = recorder

    def close(self):
        self._recorder.closed += 1


# --- live tests against real GitLab instances ---


def _skip_if_transient(e: Exception):
    """Skip on infrastructure failures only, decided from the exception chain rather than its text."""
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


def test_read_listing_does_not_narrow_to_own_projects(fake_fs):
    """Browsing and importing is the primary use, and public ARCs must stay visible."""
    source = _gitlab_source()
    source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.list_page_membership == [False]


def test_a_path_that_names_no_project_is_refused(fake_fs):
    """The marker alone is a path a user can produce by editing the address bar."""
    for path in (":-:", ":-:assays", "  :-:  /x.txt"):
        source = _gitlab_source(_source_config())
        with pytest.raises(RequestParameterInvalidException, match="does not name"):
            source.list(path, limit=5, offset=0, user_context=user_context_fixture())
        assert fake_fs.list_page_calls == [], "nothing may reach the backend"


def test_a_project_root_is_still_listable(fake_fs):
    """The guard checks only the project side: listing a project root is ordinary."""
    source = _gitlab_source(_source_config())
    source.list("group/repo1:-:", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.list_page_calls, "the listing must still be attempted"


def test_an_address_that_is_not_an_api_says_so(fake_fs):
    """Copying the address of the page you are looking at is the obvious mistake."""
    source = _gitlab_source(_source_config(base_url="https://gitlab.com/explore"))
    fake_fs.list_page_error = response_error(200, "Attempt to decode JSON with unexpected mimetype")

    with pytest.raises(RequestParameterInvalidException, match="not as a GitLab API"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())


def test_a_root_of_slashes_and_blanks_is_still_the_root(fake_fs):
    """The recursive-root refusal read only the slashes, so " / " walked the whole instance."""
    # Unicode whitespace too: arcfs strips with str.strip, which covers every character Python
    # calls whitespace, so an ASCII set here would leave the non-breaking space, the ideographic
    # space and the separator controls resolving to the root while Galaxy called them a project.
    for path in ("/ /", "/\t/", "  /  ", "//", " ", "/\xa0/", "/\u2003/", "/\u3000/", "/\x1c/"):
        source = _gitlab_source(_source_config())
        with pytest.raises(RequestParameterInvalidException, match="recursively is not supported"):
            source.list(path, recursive=True, limit=5, offset=0, user_context=user_context_fixture())
        assert fake_fs.walk_calls == [], f"{path!r} must not reach the backend"


def test_an_unresolvable_host_is_left_to_fail_as_a_connection(fake_fs):
    """A host that does not resolve is not a way into the network, so it is not refused here."""
    source = _gitlab_source(_source_config(base_url="https://gitlab.example.org"))
    source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.list_page_calls, "the listing must still be attempted"


@pytest.mark.parametrize(
    "address,says",
    [
        # Without a scheme aiohttp refuses the URL with an exception carrying only the URL, which
        # reached the form as "Reason: gitlab.com/api/v4/projects".
        ("gitlab.com", "protocol and a host"),
        ("git.nfdi4plants.org/", "protocol and a host"),
        ("ftp://gitlab.com", "protocol and a host"),
        # A scheme alone is not an address, and reached the backend as a bare URL again.
        ("https://", "protocol and a host"),
        ("", "protocol and a host"),
    ],
)
def test_an_unusable_base_url_says_what_is_wrong(fake_fs, address, says):
    source = _gitlab_source(_source_config(base_url=address))
    with pytest.raises(RequestParameterInvalidException, match=says):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.list_page_calls == [], "nothing may reach the backend"


def test_a_usable_base_url_is_accepted_and_stripped(fake_fs):
    """Whitespace pasted along with a URL survived into the hostname, where it read as correct."""
    for base_url in ("https://gitlab.com", "https://gitlab.com/", "http://gitlab.internal:8080"):
        _gitlab_source(_source_config(base_url=base_url)).list(
            "/", limit=5, offset=0, user_context=user_context_fixture()
        )
    source = _gitlab_source(_source_config(base_url="  https://gitlab.com \n"))
    source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.init_kwargs[-1]["base_url"] == "https://gitlab.com"


@pytest.mark.parametrize(
    "address",
    [
        "http://127.0.0.1:8080",
        "http://10.0.0.5",
        # validate_non_local tests the scheme with a case-sensitive startswith, so an uppercase
        # one returned unchecked; and it hands an IPv6 literal to getaddrinfo with the brackets
        # attached, which fails and looks unresolvable. yarl normalises both before connecting.
        "HTTP://127.0.0.1:8080",
        "HtTp://169.254.169.254",
        "http://[::1]:9200",
        "http://[fd00::1]:80",
        "http://[::ffff:127.0.0.1]:80",
    ],
)
def test_a_private_address_is_refused_however_it_is_written(fake_fs, address):
    """base_url is a template variable, so this would be a probe of the server's own network."""
    source = _gitlab_source(_source_config(base_url=address))
    with pytest.raises(ConfigDoesNotAllowException, match="fetch_url_allowlist"):
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert fake_fs.list_page_calls == [], f"{address} must not reach the backend"


def test_a_refused_address_names_itself_and_the_setting(fake_fs):
    """A self-hosted GitLab on a private network is ordinary; the shared check names nothing."""
    source = _gitlab_source(_source_config(base_url="http://localhost:8929"))
    with pytest.raises(ConfigDoesNotAllowException) as caught:
        source.list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert "localhost:8929" in str(caught.value)


@pytest.mark.parametrize(
    "limit,offset,asked_for",
    [
        (1, 1, {"path": "", "offset": 1, "limit": 1}),
        # An offset that is not a multiple of the limit is passed straight through.
        (2, 1, {"path": "", "offset": 1, "limit": 2}),
        # No limit means one bounded window, not fs.ls(), which reports no total and makes arcfs
        # keep the whole catalogue.
        (None, None, {"path": "", "offset": 0, "limit": MAX_ITEMS_LIMIT}),
        # limit and offset are independent query parameters, so an offset arrives on its own.
        (None, 900, {"path": "", "offset": 900, "limit": MAX_ITEMS_LIMIT}),
    ],
)
def test_the_backend_is_asked_for_the_window_the_caller_wanted(fake_fs, limit, offset, asked_for):
    source = _gitlab_source()
    source.list("/", limit=limit, offset=offset, user_context=user_context_fixture())
    assert fake_fs.list_page_calls == [asked_for]
    assert fake_fs.ls_calls == [], "no request may fall back to a full listing"
    assert fake_fs.closed == 1


def test_a_window_wider_than_a_gitlab_page_is_served_in_one_request(large_fake_fs):
    """arcfs splits a window across GitLab pages itself, so Galaxy asks once."""
    source = _gitlab_source()
    entries, total = source.list("/", limit=150, offset=100, user_context=user_context_fixture())
    assert large_fake_fs.list_page_calls == [{"path": "", "offset": 100, "limit": 150}]
    assert total == 250
    assert len(entries) == len({e.path for e in entries}) == 150, "pages must not repeat entries"
    assert [e.name for e in entries][:2] == ["group/repo100", "group/repo101"]
