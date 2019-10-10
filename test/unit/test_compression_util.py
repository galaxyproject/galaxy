import tempfile

from galaxy.util.compression_utils import CompressedFile


def test_compression_safety():
    assert_safety("test-data/unsafe.tar", expected_to_be_safe=False)
    assert_safety("test-data/unsafe_relative_symlink.tar", expected_to_be_safe=False)
    assert_safety("test-data/unsafe.zip", expected_to_be_safe=False)
    assert_safety("test-data/4.bed.zip", expected_to_be_safe=True)
    assert_safety("test-data/testdir.tar", expected_to_be_safe=True)
    assert_safety("test-data/safetar_with_symlink.tar", expected_to_be_safe=True)


def assert_safety(path, expected_to_be_safe=False):
    d = tempfile.mkdtemp()
    is_safe = True
    try:
        CompressedFile(path).extract(d)
    except Exception:
        is_safe = False

    assert is_safe is expected_to_be_safe
