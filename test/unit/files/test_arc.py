"""Tests for the ARC file source.

``ARCFilesSource`` extends ``GitLabFilesSource``: an ARC is a GitLab project, so browsing,
searching and importing are covered by ``test_gitlab.py`` and only inherited here. What this
module covers is what ARC adds, which is the write path, plus a check that the inheritance
actually holds.
"""

import os
from hashlib import sha256
from urllib.parse import quote
from uuid import uuid4

import pytest

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
    RequestParameterInvalidException,
)
from galaxy.files.models import FilesSourceOptions
from galaxy.files.sources import gitlab
from galaxy.files.sources.arc import ARCFilesSource
from galaxy.files.sources.gitlab import (
    GitLabFilesSource,
    ROOT_MARKER,
)
from galaxy.util import requests
from ._gitlab_fakes import (
    FAKE_FILES,
    FAKE_TREE,
    FakeRecorder,
    install_fake,
    response_error,
)
from ._util import (
    configured_file_sources,
    user_context_fixture,
    write_from,
)

EXPORT_ENV_VARS = ("GALAXY_TEST_ARC_BASE_URL", "GALAXY_TEST_ARC_TOKEN", "GALAXY_TEST_ARC_WRITE_REPO")
# One target that does name a file inside an ARC, shared by the write tests so that a refusal can
# only be about what the test under it varied, never about the path.
EXPORT_PATH = "/group/repo1:-:/galaxy_exports/result.txt"
EXPORT_URI = f"gxfiles://test1{EXPORT_PATH}"


@pytest.fixture
def fake_fs(monkeypatch) -> FakeRecorder:
    # ``_open_fs`` is inherited, so it reads the filesystem name from the gitlab module even
    # when the source under test is the ARC subclass.
    return install_fake(monkeypatch, gitlab, ARCFilesSource, FAKE_TREE, FAKE_FILES)


def _source_config(**overrides) -> dict:
    config = {"type": "arc", "id": "test1", "base_url": "https://datahub.example.org", "token": "glpat-secret"}
    config.update(overrides)
    return config


def _arc_source(conf=None) -> ARCFilesSource:
    file_sources = configured_file_sources([conf or _source_config()])
    return file_sources.get_file_source_path("gxfiles://test1").file_source


_response_error = response_error


def test_arc_extends_the_gitlab_source():
    """The ARC source is the GitLab one plus a write path, not a parallel implementation."""
    assert issubclass(ARCFilesSource, GitLabFilesSource)
    assert ARCFilesSource.plugin_type == "arc"
    assert GitLabFilesSource.plugin_type == "gitlab"


def test_each_source_opens_its_own_filesystem(monkeypatch):
    """The split lives in which filesystem each source opens, and nothing else.

    Both sources share ``_write_from``, because both take ``group/project:-:path`` and both need
    the same guard and the same error translation. What differs is the backend: a GitLab project
    takes a commit on the branch, an ARC takes a Git LFS pointer behind a merge request. If both
    sources opened the same filesystem, exports would quietly go to the wrong kind of place
    rather than fail, so the wiring is asserted by driving a write through each.
    """
    # The fakes below set required_module on each class, so they cannot show that ARC declares
    # one of its own. Without that declaration ARC inherits the GitLab filesystem and commits raw
    # content to the default branch where an ARC expects a pointer behind a merge request, and
    # nothing else in this suite would notice.
    assert "required_module" in vars(ARCFilesSource), "ARC must open its own filesystem, not inherit one"

    gitlab_fs = install_fake(monkeypatch, gitlab, GitLabFilesSource, FAKE_TREE, FAKE_FILES)
    arc_fs = install_fake(monkeypatch, gitlab, ARCFilesSource, FAKE_TREE, FAKE_FILES)

    gitlab_sources = configured_file_sources([_source_config(type="gitlab", writable=True)])
    write_from(gitlab_sources, EXPORT_URI, "result\n", user_context=user_context_fixture())
    assert len(gitlab_fs.put_file_calls) == 1
    assert arc_fs.put_file_calls == [], "a GitLab export must not reach the ARC backend"

    arc_sources = configured_file_sources([_source_config(type="arc", writable=True)])
    write_from(arc_sources, EXPORT_URI, "result\n", user_context=user_context_fixture())
    assert len(arc_fs.put_file_calls) == 1
    assert len(gitlab_fs.put_file_calls) == 1, "an ARC export must not reach the GitLab backend"


def test_a_gitlab_source_not_configured_writable_refuses(monkeypatch):
    """Writability is the admin's decision for both sources, and the guard is the accessor."""
    fake_fs = install_fake(monkeypatch, gitlab, GitLabFilesSource, FAKE_TREE, FAKE_FILES)
    file_sources = configured_file_sources([_source_config(type="gitlab")])
    source = file_sources.get_file_source_path("gxfiles://test1").file_source
    assert source.get_writable() is False
    assert source.to_dict()["writable"] is False
    with pytest.raises(Exception, match="Cannot write to a non-writable file source"):
        write_from(file_sources, EXPORT_URI, "result\n", user_context=user_context_fixture())
    assert fake_fs.put_file_calls == [], "nothing may reach the backend"


def test_arc_source_refuses_a_write_it_is_not_configured_for(fake_fs):
    """``writable`` still governs an ARC. What the subclass adds is the ability to honour it."""
    file_sources = configured_file_sources([_source_config(writable=False)])
    assert file_sources.get_file_source_path("gxfiles://test1").file_source.get_writable() is False
    with pytest.raises(Exception, match="Cannot write to a non-writable file source"):
        write_from(file_sources, EXPORT_URI, "result\n", user_context=user_context_fixture())
    assert fake_fs.put_file_calls == [], "nothing may reach arcfs"


def test_listing_is_inherited_unchanged(fake_fs):
    """A smoke check that the inherited read path works through the subclass."""
    entries, total = _arc_source().list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert total == 3
    assert [e.name for e in entries] == ["group/repo1", "group/sub/repo2", "other/repo3"]


def test_write_from_uploads_through_put_file(fake_fs):
    """The other half of the contrast above: configured writable, an ARC accepts the export."""
    file_sources = configured_file_sources([_source_config(writable=True)])
    assert file_sources.get_file_source_path("gxfiles://test1").file_source.get_writable() is True
    write_from(file_sources, EXPORT_URI, "result\n", user_context=user_context_fixture())
    assert fake_fs.put_file_calls[0][1] == "group/repo1:-:galaxy_exports/result.txt"
    assert fake_fs.closed == 1, "the filesystem should be closed after an upload"


def _failed_export(fake_fs: FakeRecorder, error: Exception, expected: type[Exception]) -> str:
    """Export to an ARC that arcfs refuses with ``error``, and return the message the user is shown.

    What is asserted here holds for every failure of an export, whatever the status. The error
    ladder in ``_filesystem`` is shared with listing and reading, so each arm of it has to name the
    export it was handling rather than complain about credentials or a server in the abstract, must
    not offer a listing's remedies for a write, and has to close the filesystem on the way out even
    though nothing was written.
    """
    fake_fs.put_file_error = error
    file_sources = configured_file_sources([_source_config(writable=True)])
    with pytest.raises(expected) as excinfo:
        write_from(file_sources, EXPORT_URI, "result\n", user_context=user_context_fixture())
    message = str(excinfo.value)
    assert "writing to file source path" in message
    assert EXPORT_PATH in message, "the message has to say which export failed"
    assert "listing" not in message
    assert fake_fs.closed == 1, "the filesystem should be closed after a failed upload"
    return message


def test_unauthorized_write_names_the_export_it_could_not_make(fake_fs):
    """A refused token on an export is still a refused export, and has to read as one."""
    message = _failed_export(fake_fs, _response_error(401, "Unauthorized"), AuthenticationRequired)
    assert "Permission Denied" in message
    assert "check your credentials" in message


def test_forbidden_write_names_the_export_and_both_kinds_of_token(fake_fs):
    """403 on an export is the under-scoped token case, which GitLab's own text does not survive."""
    message = _failed_export(fake_fs, _response_error(403, "Forbidden"), AuthenticationRequired)
    assert "'api' scope" in message, "an export needs the write scope, not the read-only one"
    assert "fine-grained" in message


def test_rate_limited_write_tells_the_user_to_retry(fake_fs):
    message = _failed_export(fake_fs, _response_error(429, "Too Many Requests"), MessageException)
    assert "rate limiting" in message
    assert "Please wait and try again" in message


def test_write_error_without_a_reason_phrase_does_not_leak_the_api_url(fake_fs):
    """aiohttp leaves ``message`` empty when the server sends no reason phrase.

    The exception itself stringifies to the full internal request URL, so it must not be used as a
    stand-in for the missing text. The export path renders these errors through the same ladder as
    a listing, so it has the same URL to leak.
    """
    message = _failed_export(fake_fs, _response_error(401, ""), AuthenticationRequired)
    assert "401" in message
    assert "http" not in message, "the internal API URL must not reach the user"
    assert "message=''" not in message


def test_offset_limit_on_a_write_is_not_described_as_a_listing(fake_fs):
    """``_filesystem`` is shared, so the paging wording must not leak into writes."""
    message = _failed_export(fake_fs, _response_error(405, "Method Not Allowed"), MessageException)
    assert "list any further" not in message
    assert "Search for the project by name" not in message


def _private_token_header() -> dict:
    """Build the auth header where it is used rather than holding it in a local.

    ``pytest.ini`` turns on ``--showlocals``, so a token bound to a variable in this function is
    printed in the traceback and the HTML report of any failure here. This keeps it out of *this*
    frame only: a failure inside the file source still prints the resolved configuration, whose
    ``token`` is a plain string, so the credential is not safe from a traceback in general.
    """
    return {"PRIVATE-TOKEN": os.environ["GALAXY_TEST_ARC_TOKEN"]}


def _run_results_branch() -> str:
    """Name the branch arcfs commits to, rather than going looking for it.

    arcfs derives the branch from a hash of the access token and reuses the merge request that the
    first export with that token opened, so everything written with these credentials lands on one
    branch. Recovering that branch by scanning open merge requests stops working twice over: once a
    hundred newer ones exist the branch is off the first page, and once a maintainer merges or
    closes the request it is not open any more. Either way a successful export would be reported as
    a failure. Computing the name has neither problem, and the token is hashed where it is read for
    the reason ``_private_token_header`` gives.
    """
    return f"run_results-{sha256(os.environ['GALAXY_TEST_ARC_TOKEN'].encode()).hexdigest()}"


def _gitlab_api_get(url: str) -> requests.Response:
    """GET from the GitLab API, failing as an HTTP error rather than as a missing export.

    Without the status check a 403 from an under-scoped token, or the body of a 404, reaches the
    assertions below as unexpected content, and a credentials problem is reported as an export that
    never arrived.
    """
    response = requests.get(url, headers=_private_token_header(), timeout=30)
    response.raise_for_status()
    return response


@pytest.mark.skipif(
    not all(os.environ.get(name) for name in EXPORT_ENV_VARS),
    reason=f"all of {', '.join(EXPORT_ENV_VARS)} must be set for this test",
)
def test_export_to_writable_repository_creates_lfs_merge_request():
    """Live round trip against a GitLab instance the token can write to.

    arcfs uploads through a Git LFS pointer committed on a ``run_results`` branch and opens a merge
    request, so the upload is verified on that branch rather than by re-listing the default branch,
    where the file deliberately does not appear until someone merges the request.
    """
    pytest.importorskip("arcfs")
    base_url = os.environ["GALAXY_TEST_ARC_BASE_URL"].rstrip("/")
    repo = os.environ["GALAXY_TEST_ARC_WRITE_REPO"].strip("/")
    file_sources = configured_file_sources(
        [
            {
                "type": "arc",
                "id": "test1",
                "base_url": base_url,
                "token": os.environ["GALAXY_TEST_ARC_TOKEN"],
                "writable": True,
            }
        ]
    )
    user_context = user_context_fixture()

    marker = uuid4().hex
    content = f"galaxy arc export test {marker}\n"
    inside_path = f"galaxy_exports/{marker}.txt"
    write_from(file_sources, f"gxfiles://test1/{repo}{ROOT_MARKER}/{inside_path}", content, user_context=user_context)

    api = f"{base_url}/api/v4/projects/{quote(repo, safe='')}"
    reference = quote(_run_results_branch(), safe="")
    # Deliberately unfiltered by state: the merge request is reused by every export made with this
    # token, so by now it may well have been merged or closed, and the export still succeeded.
    merge_requests = _gitlab_api_get(f"{api}/merge_requests?source_branch={reference}")
    assert merge_requests.json(), "expected arcfs to open a merge request from the run_results branch"

    quoted_path = quote(inside_path, safe="")
    stored = _gitlab_api_get(f"{api}/repository/files/{quoted_path}/raw?ref={reference}&lfs=true")
    assert stored.text == content, f"{inside_path} did not come back with the content it was exported with"
    pointer = _gitlab_api_get(f"{api}/repository/files/{quoted_path}/raw?ref={reference}")
    assert pointer.text.startswith("version https://git-lfs.github.com/spec/v1"), "expected git to hold an LFS pointer"
    # Without the entry git checks the pointer out as the file's contents rather than resolving it.
    attributes = _gitlab_api_get(f"{api}/repository/files/.gitattributes/raw?ref={reference}")
    assert (
        f"{inside_path} filter=lfs diff=lfs merge=lfs" in attributes.text
    ), f"expected {inside_path} to be registered for LFS in .gitattributes"


def test_writable_listing_asks_only_for_reachable_arcs(fake_fs):
    """Every visible ARC can be read, but only some can be pushed to."""
    source = _arc_source()
    source.list(
        "/",
        limit=5,
        offset=0,
        opts=FilesSourceOptions(write_intent=True),
        user_context=user_context_fixture(),
    )
    assert fake_fs.list_page_membership == [True]


@pytest.mark.parametrize(
    "target",
    ["/history.tgz", "/exports/history.tgz", "/", "/group/repo1:-:", "/group/repo1:-:/", "/:-:/history.tgz"],
)
def test_write_outside_an_arc_is_rejected(fake_fs, target):
    """A target that does not name a file inside an ARC has to be refused before arcfs sees it.

    Each of the three ways of failing is obscure at the backend: without the marker arcfs probes
    prefixes and builds the whole project index before complaining about a missing ARC, an ARC
    itself comes back as an IsADirectoryError repeating the path, and an empty project part is not
    caught at all and reaches GitLab's project list endpoint instead.
    """
    file_sources = configured_file_sources([_source_config(writable=True)])
    with pytest.raises(RequestParameterInvalidException, match="inside an ARC"):
        write_from(file_sources, f"gxfiles://test1{target}", "data\n", user_context=user_context_fixture())
    assert fake_fs.put_file_calls == [], "nothing may reach arcfs"
