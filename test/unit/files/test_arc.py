"""Tests for the ARC file source.

``ARCFilesSource`` extends ``GitLabFilesSource``: an ARC is a GitLab project, so browsing,
searching and importing are covered by ``test_gitlab.py`` and only inherited here. What this
module covers is what ARC adds, which is the write path, plus a check that the inheritance
actually holds.
"""

import os

import pytest

from galaxy.exceptions import (
    MessageException,
    RequestParameterInvalidException,
)
from galaxy.files.models import FilesSourceOptions
from galaxy.files.sources import gitlab
from galaxy.files.sources.arc import (
    ARCFilesSource,
    ROOT_MARKER,
)
from galaxy.files.sources.gitlab import GitLabFilesSource
from galaxy.util.unittest_utils import skip_unless_environ
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
TRANSIENT_STATUSES = (429, 500, 502, 503, 504)


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


def _skip_if_transient(e: Exception):
    if getattr(e, "status", None) in TRANSIENT_STATUSES:
        pytest.skip(f"DataHUB returned {e.status}")


def test_arc_extends_the_gitlab_source():
    """The ARC source is the GitLab one plus a write path, not a parallel implementation."""
    assert issubclass(ARCFilesSource, GitLabFilesSource)
    assert ARCFilesSource.plugin_type == "arc"
    assert GitLabFilesSource.plugin_type == "gitlab"


def test_gitlab_source_is_read_only_and_arc_is_not(fake_fs):
    """Writing is what ARC adds. A plain GitLab instance takes data another way."""
    assert "_write_from" not in GitLabFilesSource.__dict__
    assert "_write_from" in ARCFilesSource.__dict__
    assert _arc_source(_source_config(writable=True)).get_writable() is True


def test_listing_is_inherited_unchanged(fake_fs):
    """A smoke check that the inherited read path works through the subclass."""
    entries, total = _arc_source().list("/", limit=5, offset=0, user_context=user_context_fixture())
    assert total == 3
    assert [e.name for e in entries] == ["group/repo1", "group/sub/repo2", "other/repo3"]


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


def test_offset_limit_on_a_write_is_not_described_as_a_listing(fake_fs):
    """``_filesystem`` is shared, so the paging wording must not leak into writes."""
    fake_fs.put_file_error = _response_error(405, "Method Not Allowed")
    file_sources = configured_file_sources([_source_config(writable=True)])
    with pytest.raises(MessageException) as excinfo:
        write_from(
            file_sources,
            "gxfiles://test1/group/repo1:-:/galaxy_exports/result.txt",
            "result\n",
            user_context=user_context_fixture(),
        )
    message = str(excinfo.value)
    assert "writing to file source path" in message
    assert "list any further" not in message
    assert "Search for the ARC by name" not in message


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
        [{"type": "gitlab", "id": "test1", "base_url": base_url, "token": token, "writable": True}]
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


@pytest.mark.parametrize("target", ["/history.tgz", "/exports/history.tgz", "/"])
def test_write_outside_an_arc_is_rejected(fake_fs, target):
    """Without the marker arcfs builds the whole project index before failing obscurely."""
    file_sources = configured_file_sources([_source_config(writable=True)])
    with pytest.raises(RequestParameterInvalidException, match="inside an ARC"):
        write_from(file_sources, f"gxfiles://test1{target}", "data\n", user_context=user_context_fixture())
    assert fake_fs.put_file_calls == [], "nothing may reach arcfs"
