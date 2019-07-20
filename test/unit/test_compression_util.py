import shutil
import tempfile
import unittest

from galaxy.util.compression_utils import CompressedFile, get_fileobj_raw


class CompressionUtilTestCase(unittest.TestCase):

    def test_compression_safety(self):
        self.assert_safety("test-data/unsafe_relative_symlink.tar", False)
        self.assert_safety("test-data/unsafe.zip", False)
        self.assert_safety("test-data/4.bed.zip", True)
        self.assert_safety("test-data/testdir.tar", True)
        self.assert_safety("test-data/safetar_with_symlink.tar", True)
        self.assert_safety("test-data/safe_relative_symlink.tar", True)

    def test_get_fileobj_raw(self):
        self.assert_format_detected("test-data/4.bed.zip", "zip")
        self.assert_format_detected(
            "test-data/4.bed.zip", None, ["bz2", "gzip"]
        )
        self.assert_format_detected("test-data/4.bed.gz", "gzip")
        self.assert_format_detected(
            "test-data/4.bed.gz", None, ["bz2", "zip"]
        )
        self.assert_format_detected("test-data/4.bed.bz2", "bz2")
        self.assert_format_detected(
            "test-data/4.bed.bz2", None, ["gzip", "zip"]
        )

    def assert_safety(self, path, expected_to_be_safe):
        temp_dir = tempfile.mkdtemp()
        try:
            if expected_to_be_safe:
                CompressedFile(path).extract(temp_dir)
            else:
                with self.assertRaises(Exception):
                    CompressedFile(path).extract(temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def assert_format_detected(self, path, expected_fmt, allowed_fmts=None):
        fmt1 = get_fileobj_raw(path, "r", allowed_fmts)[0]
        fmt2 = get_fileobj_raw(path, "rb", allowed_fmts)[0]
        fmt3 = get_fileobj_raw(path, "rt", allowed_fmts)[0]
        fmt4 = get_fileobj_raw(path, "U", allowed_fmts)[0]
        self.assertEqual(fmt1, fmt2)
        self.assertEqual(fmt1, fmt3)
        self.assertEqual(fmt1, fmt4)
        self.assertEqual(fmt1, expected_fmt)
