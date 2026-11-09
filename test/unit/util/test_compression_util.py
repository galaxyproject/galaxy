import os
import shutil
import tarfile
import tempfile
import zipfile

from galaxy.util.checkers import (
    check_zip,
    is_zipfile_strict,
)
from galaxy.util.compression_utils import (
    CompressedFile,
    get_fileobj_raw,
)
from galaxy.util.unittest import TestCase


class TestCompressionUtil(TestCase):
    def test_compression_safety(self):
        self.assert_safety("test-data/unsafe.tar", False)
        self.assert_safety("test-data/unsafe_relative_symlink.tar", False)
        self.assert_safety("test-data/unsafe.zip", False)
        self.assert_safety("test-data/4.bed.zip", True)
        self.assert_safety("test-data/testdir.tar", True)
        self.assert_safety("test-data/testdir1.tar.gz", True)
        self.assert_safety("test-data/safetar_with_symlink.tar", True)
        self.assert_safety("test-data/safe_relative_symlink.tar", True)

    def test_get_fileobj_raw(self):
        self.assert_format_detected("test-data/4.bed.zip", "zip")
        self.assert_format_detected("test-data/4.bed.zip", None, ["bz2", "gzip"])
        self.assert_format_detected("test-data/4.bed.gz", "gzip")
        self.assert_format_detected("test-data/4.bed.gz", None, ["bz2", "zip"])
        self.assert_format_detected("test-data/4.bed.bz2", "bz2")
        self.assert_format_detected("test-data/4.bed.bz2", None, ["gzip", "zip"])

    def test_get_fileobj_raw_tar_with_stray_zip_end_record(self):
        # A zip end-of-central-directory record near the end of a tar fools zipfile.is_zipfile
        # before Python 3.14, which also checks for the central directory itself.
        path = "test-data/tar_with_stray_zip_end_record.tar"
        with open(path, "rb") as expected:
            expected_bytes = expected.read()
        fmt, fh = get_fileobj_raw(path, "rb")
        with fh:
            assert fmt is None
            assert fh.read() == expected_bytes

    def assert_safety(self, path, expected_to_be_safe):
        temp_dir = tempfile.mkdtemp()
        try:
            if expected_to_be_safe:
                with CompressedFile(path) as cf:
                    cf.extract(temp_dir)
            else:
                with self.assertRaisesRegex(Exception, "is blocked"):
                    with CompressedFile(path) as cf:
                        cf.extract(temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def assert_format_detected(self, path, expected_fmt, allowed_fmts=None):
        expected_type: type
        for mode in ["r", "rb", "rt", "U"]:
            if "b" in mode:
                expected_type = bytes
            else:
                expected_type = str
            fmt, fh = get_fileobj_raw(path, mode, allowed_fmts)
            assert fmt == expected_fmt
            assert isinstance(fh.read(0), expected_type)


def test_get_fileobj_raw_empty_zip_read_raw(tmp_path):
    path = str(tmp_path / "empty.zip")
    zipfile.ZipFile(path, "w").close()
    fmt, fh = get_fileobj_raw(path, "rb")
    with fh:
        assert fmt is None
        assert fh.read(4) == b"PK\x05\x06"


def test_get_fileobj_raw_zip_skips_directory_entries(tmp_path):
    path = str(tmp_path / "dir_first.zip")
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("d/", "")
        zf.writestr("d/a.txt", "content\n")
    fmt, fh = get_fileobj_raw(path, "rb")
    with fh:
        assert fmt == "zip"
        assert fh.read() == b"content\n"


def test_compressed_file_tar_with_stray_zip_end_record(tmp_path):
    with CompressedFile("test-data/tar_with_stray_zip_end_record.tar") as cf:
        assert cf.file_type == "tar"
        outdir = cf.extract(str(tmp_path))
    assert os.path.isfile(os.path.join(outdir, "member.bin"))


def _tar_with_trailing_zip(tmp_path):
    inner = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner, "w") as zf:
        zf.writestr("inner.txt", "inner\n")
    member = tmp_path / "member.txt"
    member.write_text("outer\n")
    path = tmp_path / "outer.tar"
    with tarfile.open(path, "w") as tf:
        tf.add(member, arcname="member.txt")
        tf.add(inner, arcname="inner.zip")
    return str(path)


def test_tar_whose_last_member_is_zip_is_not_zip(tmp_path):
    path = _tar_with_trailing_zip(tmp_path)
    assert zipfile.is_zipfile(path)
    assert not is_zipfile_strict(path)
    fmt, fh = get_fileobj_raw(path, "rb")
    with fh:
        assert fmt is None
    assert not check_zip(path)[0]
    with CompressedFile(path) as cf:
        assert cf.file_type == "tar"


def test_is_zipfile_strict_accepts_zip_and_empty_zip(tmp_path):
    path = str(tmp_path / "a.zip")
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("a.txt", "a")
    empty = str(tmp_path / "empty.zip")
    zipfile.ZipFile(empty, "w").close()
    assert is_zipfile_strict(path)
    assert is_zipfile_strict(empty)


def test_tar_fixture_with_zip_last_member_is_tar():
    path = "test-data/tar_with_zip_last_member.tar"
    assert not is_zipfile_strict(path)
    assert check_zip(path) == (False, False)
    fmt, fh = get_fileobj_raw(path, "rb")
    with fh:
        assert fmt is None
    with CompressedFile(path) as cf:
        assert cf.file_type == "tar"
