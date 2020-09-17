import tempfile

import pytest

from galaxy.datatypes.sniff import (
    convert_newlines,
    convert_newlines_sep2tabs,
    get_test_fname,
)


def assert_converts_to_1234_convert_sep2tabs(content, expected='1\t2\n3\t4\n'):
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as tf:
        tf.write(content)
    rval = convert_newlines_sep2tabs(tf.name, tmp_prefix="gxtest", tmp_dir=tempfile.gettempdir())
    assert expected == open(tf.name).read()
    assert rval == (2, None), rval


def assert_converts_to_1234_convert(content, block_size=1024):
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as tf:
        tf.write(content)
    rval = convert_newlines(tf.name, tmp_prefix="gxtest", tmp_dir=tempfile.gettempdir(), block_size=block_size)
    actual_contents = open(tf.name).read()
    assert '1 2\n3 4\n' == actual_contents, actual_contents
    assert rval == (2, None), "rval != %s for %s" % (rval, content)


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
    fname = get_test_fname("dosimzml")
    rval = convert_newlines(fname, tmp_prefix="gxtest", tmp_dir=tempfile.gettempdir(), in_place=False)
    new_file = rval[1]
    assert open(new_file, "rb").read() == open(get_test_fname("1imzml"), "rb").read()


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
