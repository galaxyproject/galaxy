import shutil
import tempfile
import unittest

from galaxy.util.compression_utils import CompressedFile


class CompressionUtilTestCase(unittest.TestCase):

    def test_compression_safety(self):
        self.assert_safety("test-data/unsafe.tar", False)
        self.assert_safety("test-data/unsafe_relative_symlink.tar", False)
        self.assert_safety("test-data/unsafe.zip", False)
        self.assert_safety("test-data/4.bed.zip", True)
        self.assert_safety("test-data/testdir.tar", True)
        self.assert_safety("test-data/safetar_with_symlink.tar", True)
        self.assert_safety("test-data/safe_relative_symlink.tar", True)

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
