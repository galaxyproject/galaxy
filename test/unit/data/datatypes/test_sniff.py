import tempfile

import pytest

from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.datatypes.sniff import (
    convert_newlines,
    convert_newlines_sep2tabs,
    convert_sep2tabs,
    get_test_fname,
    get_test_iter,
    guess_ext,
)


def assert_converts_to_1234_convert_sep2tabs(content, expected='1\t2\n3\t4\n'):
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as tf:
        tf.write(content)
    rval = convert_newlines_sep2tabs(tf.name, tmp_prefix="gxtest", tmp_dir=tempfile.gettempdir())
    assert expected == open(tf.name).read()
    assert rval[0:2] == (2, None), rval


def assert_converts_to_1234_convert(content, block_size=1024):
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as tf:
        tf.write(content)
    rval = convert_newlines(tf.name, tmp_prefix="gxtest", tmp_dir=tempfile.gettempdir(), block_size=block_size)
    actual_contents = open(tf.name).read()
    assert '1 2\n3 4\n' == actual_contents, actual_contents
    assert rval[0:2] == (2, None), f"rval != {rval} for {content}"


def assert_converts_to_1234_convert_sep2tabs_only(content: bytes, expected: bytes):
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tf:
        tf.write(content)
    convert_sep2tabs(tf.name, tmp_prefix="gxtest", tmp_dir=tempfile.gettempdir())
    assert expected == open(tf.name, "rb").read()


@pytest.mark.parametrize('source,block_size', [
    ("1 2\r3 4", None),
    ("1 2\n3 4", None),
    ("1 2\r\n3 4", None),
    ("1 2\r3 4\r", None),
    ("1 2\n3 4\n", None),
    ("1 2\r\n3 4\r\n", None),
    ("1 2\r3 4", 2),
    ("1 2\n3 4", 2),
    ("1 2\r\n3 4", 2),
    ("1 2\r3 4\r", 2),
    ("1 2\n3 4\n", 2),
    ("1 2\r\n3 4\r\n", 2),
    ("1 2\r3 4", 3),
    ("1 2\n3 4", 3),
    ("1 2\r\n3 4", 3),
    ("1 2\r3 4\r", 3),
    ("1 2\n3 4\n", 3),
    ("1 2\r\n3 4\r\n", 3),
])
def test_convert_newlines(source, block_size):
    # Verify ends with newline - with or without that on inputs - for any of
    # \r \\n or \\r\\n newlines.
    if block_size:
        assert_converts_to_1234_convert(source, block_size)
    else:
        assert_converts_to_1234_convert(source)


def test_convert_newlines_non_utf():
    fname = get_test_fname("dosimzml.data")
    rval = convert_newlines(fname, tmp_prefix="gxtest", tmp_dir=tempfile.gettempdir(), in_place=False)
    new_file = rval[1]
    assert new_file
    assert open(new_file, "rb").read() == open(get_test_fname("1imzml.data"), "rb").read()


@pytest.mark.parametrize('source,expected', [
    ("1 2\n3 4\n", None),
    ("1    2\n3    4\n", None),
    ("1\t2\n3\t4\n", None),
    ("1\t2\r3\t4\r", None),
    ("1\t2\r\n3\t4\r\n", None),
    ("1    2\r\n3       4\r\n", None),
    ("1 2     \n3 4 \n", '1\t2\t\n3\t4\t\n'),
])
def test_convert_sep2tabs(source, expected):
    if expected:
        assert_converts_to_1234_convert_sep2tabs(source, expected=expected)
    else:
        assert_converts_to_1234_convert_sep2tabs(source)


def test_convert_sep2tabs_only():
    assert_converts_to_1234_convert_sep2tabs_only(b"1 2\r3 4", b"1\t2\r3\t4")
    assert_converts_to_1234_convert_sep2tabs_only(b"1 2\n3 4", b"1\t2\n3\t4")
    assert_converts_to_1234_convert_sep2tabs_only(b"1    2\n3    4", b"1\t2\n3\t4")


def test_all_guess_ext():
    """
    test guess_ext on all files in lib/galaxy/datatypes/tests
    the extension of the files in this dir needs to match the guessed extension
    """
    datatypes_registry = example_datatype_registry_for_sample()
    _, testdata = get_test_iter([])
    for f in testdata:
        ext = guess_ext(f, datatypes_registry.sniff_order)
        assert f.endswith(ext), f"{f} is recognized as {ext}"
