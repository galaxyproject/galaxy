from typing import TYPE_CHECKING

import pytest
from mercurial import (
    hg,
    ui,
)

from galaxy.tool_shed.util.hg_util import (
    get_changectx_for_changeset,
    get_file_data_from_manifest,
)
from tool_shed.util import hg_util

if TYPE_CHECKING:
    from pathlib import Path


def test_init_repository(tmp_path):
    hg_util.init_repository(tmp_path)
    assert (tmp_path / ".hg").exists()


def test_init_repository_fails(tmp_path):
    hg_util.init_repository(tmp_path)
    with pytest.raises(Exception, match="Error initializing repository"):
        test_init_repository(tmp_path)


def _add_file_and_commmit_changeset(tmp_path: "Path"):
    path_to_add = tmp_path / "test.txt"
    path_to_add.write_text("test")
    hg_util.add_changeset(tmp_path, path_to_add)
    hg_util.commit_changeset(tmp_path, path_to_add, "testuser", "testcommit")
    return path_to_add


def test_add_file_and_commmit_changeset(tmp_path):
    hg_util.init_repository(tmp_path)
    _add_file_and_commmit_changeset(tmp_path)


def _add_dir_and_commit_changeset(tmp_path: "Path"):
    dir_to_add = tmp_path / "abc"
    dir_to_add.mkdir()
    (dir_to_add / "test.txt").write_text("bla")
    hg_util.add_changeset(tmp_path, dir_to_add)
    hg_util.commit_changeset(tmp_path, dir_to_add, "testuser", "testcommit")
    return dir_to_add


def test_add_dir_and_commit_changeset(tmp_path):
    hg_util.init_repository(tmp_path)
    _add_dir_and_commit_changeset(tmp_path)


def test_remove_tracked_file(tmp_path):
    hg_util.init_repository(tmp_path)
    path_to_remove = _add_file_and_commmit_changeset(tmp_path)
    hg_util.remove_path(tmp_path, path_to_remove)


def test_remove_untracked_file(tmp_path):
    hg_util.init_repository(tmp_path)
    untracked_path = tmp_path / "untracked.txt"
    untracked_path.write_text("bla")
    hg_util.remove_path(tmp_path, untracked_path)


def test_remove_tracked_dir(tmp_path):
    hg_util.init_repository(tmp_path)
    dir_to_remove = _add_dir_and_commit_changeset(tmp_path)
    hg_util.remove_path(tmp_path, dir_to_remove)


def test_remove_nonexistant_file_fails(tmp_path):
    hg_util.init_repository(tmp_path)
    with pytest.raises(Exception, match="Error removing path"):
        hg_util.remove_path(tmp_path, tmp_path / "some path")


def _commit_file(repo_path: "Path", relative_path: str, content: str | None) -> str:
    """Write (or with content None, remove) a file, commit it and return the new changeset revision."""
    path = repo_path / relative_path
    if content is None:
        hg_util.remove_path(repo_path, path)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        hg_util.add_changeset(repo_path, path)
    hg_util.commit_changeset(repo_path, path, "testuser", f"update {relative_path}")
    repo = hg.repository(ui.ui(), str(repo_path).encode("utf-8"))
    return str(repo[len(repo) - 1])


def test_get_file_data_from_manifest(tmp_path):
    hg_util.init_repository(tmp_path)
    first = _commit_file(tmp_path, "images/logo.png", "images v1")
    second = _commit_file(tmp_path, "docs/logo.png", "docs")
    third = _commit_file(tmp_path, "docs/logo.png", None)
    fourth = _commit_file(tmp_path, "images/logo.png", None)
    repo = hg.repository(ui.ui(), str(tmp_path).encode("utf-8"))

    # The path is matched exactly before falling back to the file name.
    assert get_file_data_from_manifest("images/logo.png", repo, second) == b"images v1"
    assert get_file_data_from_manifest("docs/logo.png", repo, second) == b"docs"
    assert get_file_data_from_manifest("logo.png", repo, first) == b"images v1"
    assert get_file_data_from_manifest("other/logo.png", repo, first) == b"images v1"
    # Deleting another file with the same name leaves images/logo.png in place.
    assert get_file_data_from_manifest("images/logo.png", repo, third) == b"images v1"
    assert get_file_data_from_manifest("images/logo.png", repo, fourth) is None
    assert get_file_data_from_manifest("images/logo.png", repo, "garbage") is None


def test_get_changectx_for_changeset_matches_only_exact_short_hash(tmp_path):
    hg_util.init_repository(tmp_path)
    first = _commit_file(tmp_path, "a.txt", "a")
    second = _commit_file(tmp_path, "b.txt", "b")
    repo = hg.repository(ui.ui(), str(tmp_path).encode("utf-8"))

    assert str(get_changectx_for_changeset(repo, first)) == first
    assert str(get_changectx_for_changeset(repo, second)) == second
    full_hash = get_changectx_for_changeset(repo, second).hex().decode()
    # Prefixes, full hashes, revision numbers, symbolic names, and the null and working directory hashes.
    not_changesets = [second[:6], full_hash, "0", "tip", ".", "null", "", "000000000000", "ffffffffffff"]
    for changeset_revision in not_changesets + ["000000000bad"]:
        assert get_changectx_for_changeset(repo, changeset_revision) is None, changeset_revision
