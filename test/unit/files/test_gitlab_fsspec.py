"""Tests for the writable GitLab filesystem.

The plugin tests in ``test_gitlab.py`` replace the filesystem class outright, so nothing there
reaches this module. What it decides is what a commit contains, which is where a mistake costs a
repository rather than an error message, so it is covered here on its own terms. The parts that
decide that are plain functions rather than methods precisely so they run without the optional
``arcfs-fsspec`` package, which CI does not install.
"""

import asyncio
import base64

import pytest

from galaxy.exceptions import MessageException
from galaxy.files.sources.gitlab import GitLabFilesSource
from galaxy.files.sources.gitlab_fsspec import (
    check_commit_size,
    commit_actions,
    GITLAB_MAX_COMMIT_REQUEST_BYTES,
    MAX_COMMIT_BYTES,
    WritableGitLabFileSystem,
)

CONTENT = base64.b64encode(b"payload").decode("ascii")


def test_a_new_file_is_created():
    actions = commit_actions("assays/x.txt", CONTENT, None)
    assert actions == [{"action": "create", "file_path": "assays/x.txt", "content": CONTENT, "encoding": "base64"}]


def test_an_existing_file_is_replaced_rather_than_updated():
    """GitLab runs the Git LFS transformer for ``create`` and for nothing else.

    An ``update`` onto a path ``.gitattributes`` marks as LFS therefore commits the raw bytes
    where git expects a pointer, and the repository cannot be read back correctly afterwards.
    Deleting and creating in one commit keeps the transformer in play, so this must never become
    a single update however much tidier that looks.
    """
    actions = commit_actions("assays/x.txt", CONTENT, {"last_commit_id": "abc123"})
    assert [a["action"] for a in actions] == ["delete", "create"]
    assert "update" not in {a["action"] for a in actions}


def test_a_replacement_carries_the_commit_it_was_read_at():
    """Without this GitLab accepts both of two concurrent exports and keeps only the later one."""
    actions = commit_actions("assays/x.txt", CONTENT, {"last_commit_id": "abc123"})
    assert actions[0]["last_commit_id"] == "abc123"


def test_a_replacement_without_a_commit_id_still_replaces():
    """Older GitLab versions omit the field; losing the guard must not lose the write."""
    actions = commit_actions("assays/x.txt", CONTENT, {})
    assert [a["action"] for a in actions] == ["delete", "create"]
    assert "last_commit_id" not in actions[0]


def test_replacing_keeps_the_execute_bit():
    """The file is created afresh, so a mode the old one carried is dropped unless restored."""
    actions = commit_actions("bin/run.sh", CONTENT, {"execute_filemode": True})
    assert actions[-1]["execute_filemode"] is True


def test_a_file_without_the_execute_bit_does_not_gain_one():
    for existing in (None, {}, {"execute_filemode": False}):
        assert "execute_filemode" not in commit_actions("assays/x.txt", CONTENT, existing)[-1]


def test_the_size_limit_is_bounded_by_the_worker_not_by_gitlab():
    """What a commit may carry is limited by this process, not by what GitLab would accept.

    The content is read, base64-encoded and then serialised into the request body, so several
    copies are resident at once in a worker shared with every other file source. Sizing the
    ceiling to GitLab's own request limit put that over a gigabyte for a single export. It is
    also kept under the 20 MB above which GitLab rate limits commits to three every thirty
    seconds, which is the point where a commit stops being a sensible way to move a file.
    """
    assert GITLAB_MAX_COMMIT_REQUEST_BYTES == 314_572_800, "GitLab's documented request limit"
    encoded = 4 * ((MAX_COMMIT_BYTES + 2) // 3)
    assert encoded <= GITLAB_MAX_COMMIT_REQUEST_BYTES, "the encoded form must still fit a request"
    assert MAX_COMMIT_BYTES <= 20 * 1024 * 1024, "above this GitLab rate limits the commit"
    # Several copies of the file are live at the peak, so the ceiling has to leave a worker room.
    assert MAX_COMMIT_BYTES * 5 < 200 * 1024 * 1024, "one export must not be able to exhaust a worker"


def test_a_file_over_the_limit_is_refused_before_it_is_sent():
    with pytest.raises(MessageException) as excinfo:
        check_commit_size(MAX_COMMIT_BYTES + 1, "group/repo:-:big.bin")
    message = str(excinfo.value)
    assert "group/repo:-:big.bin" in message
    assert "ARC file source" in message, "the alternative that has no such limit is worth naming"


def test_a_file_at_the_limit_is_allowed():
    check_commit_size(MAX_COMMIT_BYTES, "group/repo:-:big.bin")


def test_the_gitlab_source_opens_this_filesystem():
    """The plugin tests replace ``required_module``, so only this pins what it is by default.

    Without it, deleting the assignment in ``arc.py`` that looks redundant beside the inherited
    one would leave ARC opening this filesystem, committing raw bytes to the default branch
    where an ARC expects a pointer behind a merge request, and every suite would stay green.
    """
    pytest.importorskip("arcfs")
    from arcfs.fs import GitLabARCFileSystem

    from galaxy.files.sources.arc import ARCFilesSource

    assert GitLabFilesSource.required_module is WritableGitLabFileSystem
    assert ARCFilesSource.required_module is GitLabARCFileSystem
    assert issubclass(WritableGitLabFileSystem, GitLabARCFileSystem)


def _writable_fs(tree_answer, existing=None):
    """A filesystem whose backend calls are stubbed, so the write path runs without a network.

    ``tree_answer`` is what the tree endpoint does for the target: an exception to raise, or the
    ``(entries, total)`` tuple it returns.
    """
    pytest.importorskip("arcfs")
    fs = WritableGitLabFileSystem("https://example.invalid", "token", skip_instance_cache=True)
    calls: dict = {"commits": []}

    class _Client:
        token = "token"

        async def get_project_by_path(self, path, **kwargs):
            return {"id": 1, "original_path": path, "default_branch": "main"}

        async def get_default_branch(self, repo_id):
            return "main"

        async def get_file(self, repo_id, path, ref):
            if existing is None:
                raise FileNotFoundError(path)
            return existing

        async def retrieve_project_level_page(self, repo_id, subdir, *, ref=None, page=1, per_page=100):
            if isinstance(tree_answer, Exception):
                raise tree_answer
            return tree_answer

        async def create_commit(self, repo_id, branch, message, actions):
            calls["commits"].append({"branch": branch, "message": message, "actions": actions})
            return {"id": "deadbeef"}

    fs.client = _Client()
    return fs, calls


def test_a_new_path_is_allowed_when_the_tree_endpoint_answers_404():
    """GitLab 17.7 and later answer a path that is not a folder with 404."""
    fs, _ = _writable_fs(FileNotFoundError("assays/new.txt"))
    asyncio.run(fs._refuse_a_directory(1, "assays/new.txt", "main"))


def test_a_new_path_is_allowed_when_the_tree_endpoint_answers_an_empty_list():
    """Before 17.7 a self-managed GitLab answered the same case with 200 and an empty list.

    Reading only the status refused every new file on those instances: the check saw no
    exception, concluded the path was a folder, and told the user to name a file inside it,
    which is itself a new path and was refused in turn. Replacing an existing file still
    worked, because that skips this check, so nothing about the failure pointed here.
    """
    fs, _ = _writable_fs(([], 0))
    asyncio.run(fs._refuse_a_directory(1, "assays/new.txt", "main"))


def test_a_folder_is_refused():
    """Git has no empty trees, so entries are what distinguish a folder, whatever the status."""
    fs, _ = _writable_fs(([{"name": "inner.txt", "type": "blob"}], 1))
    with pytest.raises(MessageException) as excinfo:
        asyncio.run(fs._refuse_a_directory(1, "assays", "main"))
    assert "is a folder in this project" in str(excinfo.value)


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
    """``open`` reaches the inherited object, which uploads the ARC way and opens a merge request.

    That is the one thing this class exists not to do, so every mode carrying write intent is
    refused rather than only the obvious ones: "r+b" and "rb+" are read-write and would
    otherwise pass a test for the absence of "r".
    """
    pytest.importorskip("arcfs")
    fs = WritableGitLabFileSystem("https://example.invalid", "token", skip_instance_cache=True)
    with pytest.raises(NotImplementedError):
        fs._open("group/repo:-:x.txt", mode=mode)
    with pytest.raises(NotImplementedError):
        asyncio.run(fs.open_async("group/repo:-:x.txt", mode=mode))
