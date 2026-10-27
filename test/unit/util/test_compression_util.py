import shutil
import tempfile
import zipfile

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
        # A zip end-of-central-directory record near the end of a tar fools zipfile.is_zipfile.
        path = "test-data/tar_with_stray_zip_end_record.tar"
        assert zipfile.is_zipfile(path)
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
