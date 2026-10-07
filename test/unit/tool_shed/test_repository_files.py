import os
import subprocess
from pathlib import Path

import pytest
from mercurial import (
    hg,
    revlog,
    ui,
)
from mercurial.revlogutils.constants import KIND_FILELOG

from tool_shed.util import hg_util
from tool_shed.util.hg_util import changectx_for_revision
from tool_shed.util.repository_files import (
    find_manifest_file,
    list_manifest,
    listing_validator,
    MAX_CONTENT_BYTES,
    read_file,
)
from tool_shed_client.schema import RepositoryFileContents

BINARY_CONTENTS = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
NON_UTF8_CONTENTS = b"caf\xe9 au lait\n"


@pytest.fixture
def hg_repo(tmp_path: Path):
    hg_util.init_repository(tmp_path)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "README").write_text("from a\n")
    (tmp_path / "b" / "README").write_text("from b\n")
    (tmp_path / "image.png").write_bytes(BINARY_CONTENTS)
    (tmp_path / "latin1.txt").write_bytes(NON_UTF8_CONTENTS)
    (tmp_path / "big.txt").write_text("x" * 100)
    script = tmp_path / "run.sh"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(0o755)
    os.symlink("a/README", tmp_path / "link")
    hg_util.add_changeset(tmp_path, tmp_path)
    hg_util.commit_changeset(tmp_path, tmp_path, "testuser", "first")
    return hg.repository(ui.ui(), bytes(tmp_path))


def _tip(hg_repo):
    return hg_repo[len(hg_repo) - 1]


def _read(ctx, path: str, max_bytes: int = MAX_CONTENT_BYTES) -> RepositoryFileContents:
    manifest_file = find_manifest_file(ctx, path)
    assert manifest_file is not None
    return read_file(manifest_file, max_bytes)


def test_changectx_for_revision_requires_exact_short_hash(hg_repo):
    ctx = _tip(hg_repo)
    short_hash = str(ctx)
    assert len(short_hash) == 12
    assert changectx_for_revision(hg_repo, short_hash) == ctx
    assert changectx_for_revision(hg_repo, ctx.hex().decode()) is None
    assert changectx_for_revision(hg_repo, short_hash[:8]) is None
    assert changectx_for_revision(hg_repo, "tip") is None
    assert changectx_for_revision(hg_repo, "default") is None
    assert changectx_for_revision(hg_repo, "0") is None
    assert changectx_for_revision(hg_repo, "deadbeefdead") is None
    assert changectx_for_revision(hg_repo, "000000000000") is None
    assert changectx_for_revision(hg_repo, "") is None
    assert changectx_for_revision(hg_repo, "zzzzzzzzzzzz") is None


def test_list_manifest(hg_repo):
    entries = {entry.path: entry for entry in list_manifest(_tip(hg_repo))}
    assert sorted(entries) == ["a/README", "b/README", "big.txt", "image.png", "latin1.txt", "link", "run.sh"]
    assert entries["a/README"].type == "file"
    assert entries["a/README"].size == len("from a\n")
    assert not entries["a/README"].executable
    assert entries["run.sh"].executable
    assert entries["link"].type == "symlink"
    assert not entries["link"].executable


def test_read_text_file(hg_repo):
    contents = _read(_tip(hg_repo), "a/README")
    assert contents.path == "a/README"
    assert contents.type == "file"
    assert contents.size == len("from a\n")
    assert not contents.binary
    assert not contents.truncated
    assert contents.content == "from a\n"


def test_same_basename_in_different_directories(hg_repo):
    ctx = _tip(hg_repo)
    a_contents = _read(ctx, "a/README")
    b_contents = _read(ctx, "b/README")
    assert a_contents.content == "from a\n"
    assert b_contents.content == "from b\n"


def test_read_binary_file(hg_repo):
    contents = _read(_tip(hg_repo), "image.png")
    assert contents.binary
    assert not contents.truncated
    assert contents.size == len(BINARY_CONTENTS)
    assert contents.content is None


def test_read_non_utf8_file(hg_repo):
    contents = _read(_tip(hg_repo), "latin1.txt")
    assert not contents.binary
    assert contents.content == "caf� au lait\n"


def test_read_symlink_has_no_content(hg_repo):
    contents = _read(_tip(hg_repo), "link")
    assert contents.type == "symlink"
    assert contents.content is None
    assert not contents.binary
    assert not contents.truncated


def test_read_over_size_cap(hg_repo):
    ctx = _tip(hg_repo)
    contents = _read(ctx, "big.txt", max_bytes=99)
    assert contents.truncated
    assert contents.size == 100
    assert contents.content is None
    at_cap = _read(ctx, "big.txt", max_bytes=100)
    assert not at_cap.truncated
    assert at_cap.content == "x" * 100


@pytest.fixture
def no_file_reads(monkeypatch):
    # Both rawdata() and revision() go through _revisiondata; manifest reads stay allowed.
    original = revlog.revlog._revisiondata

    def _revisiondata(self, *args, **kwargs):
        if self.target[0] == KIND_FILELOG:
            raise AssertionError("file revision data was read")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(revlog.revlog, "_revisiondata", _revisiondata)


def test_list_manifest_does_not_read_files(hg_repo, no_file_reads):
    entries = {entry.path: entry for entry in list_manifest(_tip(hg_repo))}
    assert entries["big.txt"].size == 100


def test_read_over_size_cap_does_not_read_file(hg_repo, no_file_reads):
    contents = _read(_tip(hg_repo), "big.txt", max_bytes=99)
    assert contents.truncated
    assert contents.size == 100


def test_validators_do_not_read_files(hg_repo, no_file_reads):
    ctx = _tip(hg_repo)
    assert ctx.hex().decode() in listing_validator(ctx)
    a_readme = find_manifest_file(ctx, "a/README")
    b_readme = find_manifest_file(ctx, "b/README")
    script = find_manifest_file(ctx, "run.sh")
    assert a_readme is not None and b_readme is not None and script is not None
    validators = {a_readme.validator(), b_readme.validator(), script.validator(), listing_validator(ctx)}
    assert len(validators) == 4
    assert a_readme.validator() != a_readme.validator(max_bytes=10)
    assert find_manifest_file(ctx, "missing.txt") is None


def test_file_validator_tracks_file_revision_not_changeset(hg_repo):
    repo_path = hg_repo.root.decode()
    first = _tip(hg_repo)
    (Path(repo_path) / "a" / "README").write_text("changed\n")
    hg_util.commit_changeset(repo_path, repo_path, "testuser", "change a/README")
    second = _tip(hg.repository(ui.ui(), hg_repo.root))
    assert listing_validator(first) != listing_validator(second)

    def validator(ctx, path):
        manifest_file = find_manifest_file(ctx, path)
        assert manifest_file is not None
        return manifest_file.validator()

    assert validator(first, "b/README") == validator(second, "b/README")
    assert validator(first, "a/README") != validator(second, "a/README")


def test_read_copied_file_size_excludes_copy_metadata(hg_repo):
    repo_path = hg_repo.root.decode()
    subprocess.check_output(["hg", "copy", "a/README", "copied"], cwd=repo_path)
    hg_util.commit_changeset(repo_path, repo_path, "testuser", "copy")
    ctx = _tip(hg.repository(ui.ui(), hg_repo.root))
    contents = _read(ctx, "copied")
    assert contents.size == len("from a\n")
    assert contents.content == "from a\n"


@pytest.mark.parametrize(
    "path",
    [
        "missing.txt",
        "a",
        "a/",
        "../a/README",
        "/a/README",
        ".hg/hgrc",
        "",
        "./a/README",
        # Mercurial's C manifest compares NUL-terminated, so these would otherwise match a/README.
        "a/README\x00",
        "a/README\x00junk",
    ],
)
def test_read_paths_not_in_manifest(hg_repo, path):
    assert find_manifest_file(_tip(hg_repo), path) is None
