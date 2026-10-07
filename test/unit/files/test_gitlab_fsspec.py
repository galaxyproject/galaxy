"""Tests for the writable GitLab filesystem.

The plugin tests in ``test_gitlab.py`` replace the filesystem class outright, so nothing there
reaches this module. What it decides is what a commit contains, which is where a mistake costs a
repository rather than an error message. The parts that decide that are plain functions, so they
run without the optional ``arcfs-fsspec`` package, which CI does not install.
"""

import asyncio
import base64

import pytest

from galaxy.exceptions import MessageException
from galaxy.files.sources.gitlab import GitLabFilesSource
from galaxy.files.sources.gitlab_fsspec import (
    check_commit_size,
    commit_actions,
    MAX_COMMIT_BYTES,
    refuse_a_directory,
    WritableGitLabFileSystem,
)

CONTENT = base64.b64encode(b"payload").decode("ascii")


def test_a_new_file_is_created():
    actions = commit_actions("assays/x.txt", CONTENT, None)
    assert actions == [{"action": "create", "file_path": "assays/x.txt", "content": CONTENT, "encoding": "base64"}]


def test_an_existing_file_is_replaced_rather_than_updated():
    """GitLab runs the Git LFS transformer for ``create`` and for nothing else.

    An ``update`` onto a path ``.gitattributes`` marks as LFS commits raw bytes where git expects
    a pointer, and the repository cannot be read back afterwards. This must never become a single
    update however much tidier that looks.
    """
    actions = commit_actions("assays/x.txt", CONTENT, {"last_commit_id": "abc123"})
    assert [a["action"] for a in actions] == ["delete", "create"]


@pytest.mark.parametrize(
    "existing,expected",
    [({"last_commit_id": "abc123"}, "abc123"), ({}, None)],
)
def test_a_replacement_carries_the_commit_it_was_read_at(existing, expected):
    """Without it GitLab accepts both of two concurrent exports and keeps only the later one."""
    actions = commit_actions("assays/x.txt", CONTENT, existing)
    assert [a["action"] for a in actions] == ["delete", "create"]
    assert actions[0].get("last_commit_id") == expected


@pytest.mark.parametrize(
    "existing,expected",
    [({"execute_filemode": True}, True), ({"execute_filemode": False}, None), ({}, None), (None, None)],
)
def test_the_execute_bit_survives_a_replacement(existing, expected):
    """The file is created afresh, so a mode the old one carried is dropped unless restored."""
    assert commit_actions("bin/run.sh", CONTENT, existing)[-1].get("execute_filemode") == expected


@pytest.mark.parametrize("size,refused", [(MAX_COMMIT_BYTES, False), (MAX_COMMIT_BYTES + 1, True)])
def test_a_file_too_large_to_commit_is_refused_before_it_is_sent(size, refused):
    if not refused:
        check_commit_size(size, "group/repo:-:big.bin")
        return
    with pytest.raises(MessageException) as excinfo:
        check_commit_size(size, "group/repo:-:big.bin")
    assert "ARC file source" in str(excinfo.value), "the alternative without the limit is worth naming"


def test_the_gitlab_source_opens_this_filesystem():
    """The plugin tests replace ``required_module``, so only this pins what it is by default.

    Without it, deleting the assignment in ``arc.py`` would leave ARC committing raw bytes to the
    default branch where it expects a pointer behind a merge request, with every suite green.
    """
    pytest.importorskip("arcfs")
    from arcfs.fs import GitLabARCFileSystem

    from galaxy.files.sources.arc import ARCFilesSource

    assert GitLabFilesSource.required_module is WritableGitLabFileSystem
    assert ARCFilesSource.required_module is GitLabARCFileSystem
    assert issubclass(WritableGitLabFileSystem, GitLabARCFileSystem)


class FakeClient:
    """Just the methods the guard and the metadata lookup ask for."""

    def __init__(self, answer, existing=None):
        self.answer = answer
        self.existing = existing
        self.calls: list[dict] = []

    async def retrieve_project_level_page(self, repo_id, subdir, *, ref=None, page=1, per_page=100):
        self.calls.append({"repo_id": repo_id, "subdir": subdir, "ref": ref, "per_page": per_page})
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer, len(self.answer)


@pytest.mark.parametrize(
    "answer,refused",
    [
        ([{"path": "assays/a.txt", "type": "blob"}], True),
        # 17.7 and later answer 404 for a path that is not a folder; before it, 200 with [].
        # Reading only the status refused every new file on those older instances.
        (FileNotFoundError("assays/x.txt"), False),
        ([], False),
    ],
)
def test_a_folder_is_refused_and_a_new_path_is_not(answer, refused):
    """A create against a folder replaces it and everything under it, and GitLab reports success.

    Git has no empty trees, so the entries decide it whichever way the status went. Confirmed
    against a real GitLab 17.4.0, which answers 200 with [] where 17.7 answers 404.
    """
    client = FakeClient(answer)
    if not refused:
        asyncio.run(refuse_a_directory(client, 1, "assays/x.txt", "main"))
        return
    with pytest.raises(MessageException, match="is a folder"):
        asyncio.run(refuse_a_directory(client, 1, "assays", "main"))


def test_the_guard_asks_about_the_branch_it_was_given():
    """It has to be the branch the commit lands on, not the project default."""
    client = FakeClient([])
    asyncio.run(refuse_a_directory(client, 7, "assays/x.txt", "some-branch"))
    assert client.calls == [{"repo_id": 7, "subdir": "assays/x.txt", "ref": "some-branch", "per_page": 1}]


def _writable_fs(tree_answer, existing=None):
    """A filesystem whose backend calls are stubbed, so the write path runs without a network."""
    pytest.importorskip("arcfs")
    fs = WritableGitLabFileSystem("https://example.invalid", "token", skip_instance_cache=True)
    calls: dict = {"commits": []}

    class _Head:
        """What GitLab answers a HEAD on the files endpoint with: headers, no body."""

        def __init__(self):
            self.status = 404 if existing is None else 200
            self.headers: dict = (
                {}
                if existing is None
                else {
                    "X-Gitlab-Last-Commit-Id": existing.get("last_commit_id", ""),
                    # GitLab sends this as text, and the string "false" is true.
                    "X-Gitlab-Execute-Filemode": "true" if existing.get("execute_filemode") else "false",
                }
            )

        def raise_for_status(self):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    class _Session:
        def head(self, url, **kwargs):
            return _Head()

    class _Client(FakeClient):
        token = "token"

        async def get_project_by_path(self, path, **kwargs):
            return {"id": 1, "original_path": path, "default_branch": "main"}

        async def get_default_branch(self, repo_id):
            return "main"

        def _repository_file_url(self, repo_id, path):
            return f"https://example.invalid/api/v4/projects/{repo_id}/repository/files/{path}"

        async def _ensure(self):
            return _Session()

        async def create_commit(self, repo_id, branch, message, actions):
            calls["commits"].append({"branch": branch, "message": message, "actions": actions})
            return {"id": "deadbeef"}

    fs.client = _Client(tree_answer)
    return fs, calls


def test_writing_a_new_file_commits_a_create(tmp_path):
    fs, calls = _writable_fs(FileNotFoundError("x"))
    local = tmp_path / "payload.txt"
    local.write_bytes(b"hello")
    asyncio.run(fs._put_file(str(local), "group/repo:-:assays/new.txt"))
    assert [a["action"] for a in calls["commits"][0]["actions"]] == ["create"]
    assert calls["commits"][0]["branch"] == "main"


def test_writing_over_a_folder_commits_nothing(tmp_path):
    fs, calls = _writable_fs(([{"name": "inner.txt", "type": "blob"}], 1))
    local = tmp_path / "payload.txt"
    local.write_bytes(b"hello")
    with pytest.raises(MessageException):
        asyncio.run(fs._put_file(str(local), "group/repo:-:assays"))
    assert calls["commits"] == [], "nothing may be committed over a folder"


@pytest.mark.parametrize("mode", ["wb", "ab", "xb", "rb+", "r+b", "w+b"])
def test_a_write_through_open_is_refused(mode):
    """``open`` reaches the inherited object, which uploads the ARC way and opens a merge request."""
    pytest.importorskip("arcfs")
    fs = WritableGitLabFileSystem("https://example.invalid", "token", skip_instance_cache=True)
    with pytest.raises(NotImplementedError):
        fs._open("group/repo:-:x.txt", mode=mode)
    with pytest.raises(NotImplementedError):
        asyncio.run(fs.open_async("group/repo:-:x.txt", mode=mode))


@pytest.mark.parametrize(
    "existing,expected", [(None, None), ({"execute_filemode": False}, False), ({"execute_filemode": True}, True)]
)
def test_the_execute_bit_is_read_as_a_flag_not_as_a_string(existing, expected):
    """HEAD returns this header as text, and the string "false" is true."""
    pytest.importorskip("arcfs")
    fs, _ = _writable_fs(FileNotFoundError("x"), existing=existing)
    answer = asyncio.run(fs._existing_file(1, "assays/x.txt", "main"))
    assert (answer["execute_filemode"] if answer else None) == expected
