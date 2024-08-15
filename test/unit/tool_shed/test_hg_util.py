import pytest

from tool_shed.util import hg_util


def test_init_repository(tmpdir):
    hg_util.init_repository(str(tmpdir))
    assert (tmpdir / ".hg").exists()


def test_init_repository_fails(tmpdir):
    test_init_repository(tmpdir)
    with pytest.raises(Exception) as exc_info:
        test_init_repository(tmpdir)
    assert "Error initializing repository" in str(exc_info.value)


def test_add_file_and_commmit_changeset(tmpdir):
    test_init_repository(tmpdir)
    path_to_add = tmpdir / "test.txt"
    path_to_add.write("test")
    hg_util.add_changeset(str(tmpdir), str(path_to_add))
    hg_util.commit_changeset(str(tmpdir), str(path_to_add), "testuser", "testcommit")
    return path_to_add


def test_add_dir_and_commit_changeset(tmpdir):
    test_init_repository(tmpdir)
    path_to_add = tmpdir.mkdir("abc")
    (path_to_add / "test.txt").write("bla")
    hg_util.add_changeset(str(tmpdir), str(path_to_add))
    hg_util.commit_changeset(str(tmpdir), str(path_to_add), "testuser", "testcommit")
    return path_to_add


def test_remove_tracked_file(tmpdir):
    path_to_remove = test_add_file_and_commmit_changeset(tmpdir)
    hg_util.remove_path(str(tmpdir), path_to_remove)


def test_remove_untracked_file(tmpdir):
    test_init_repository(tmpdir)
    untracked_path = tmpdir / "untracked.txt"
    untracked_path.write("bla")
    hg_util.remove_path(str(tmpdir), str(untracked_path))


def test_remove_tracked_dir(tmpdir):
    path_to_remove = test_add_dir_and_commit_changeset(tmpdir)
    hg_util.remove_path(str(tmpdir), path_to_remove)


def test_remove_nonexistant_file_fails(tmpdir):
    test_init_repository(tmpdir)
    with pytest.raises(Exception) as exc_info:
        hg_util.remove_path(str(tmpdir), str(tmpdir / "some path"))
    assert "Error removing path" in str(exc_info.value)
