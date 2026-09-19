from typing import TYPE_CHECKING

import pytest

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
