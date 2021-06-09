import os
import tempfile

from galaxy.util.checkers import check_binary, check_html

# This is less than ideal as tests will break when test data files are added
# or removed.
EXPECTED_NUMBER_OF_BINARY_FILES = 91


def test_check_html():
    html_text = '<p>\n<a href="url">Link</a>\n</p>\n'
    assert check_html(html_text, file_path=False)
    # Test a non-HTML binary string
    assert not check_html(b'No HTML here\nSecond line\n', file_path=False)
    with tempfile.NamedTemporaryFile(mode='w') as tmp:
        tmp.write(html_text)
        tmp.flush()
        assert check_html(tmp.name)
    # Test a non-UTF8 binary file
    with tempfile.NamedTemporaryFile(mode='wb') as tmpb:
        tmpb.write(b'\x1f\x8b')
        tmpb.flush()
        assert not check_html(tmpb.name)
    with tempfile.NamedTemporaryFile(mode='wb') as tmp:
        tmp.write(b'\x1f\x8b')
        tmp.flush()
        assert not check_html(tmp.name)


def test_check_binary():
    assert check_binary(b'FCS3.0.........', False)
    assert check_binary(b'FCS3.1.........', False)
    assert check_binary(b'FCS2.0.........', False)
    assert check_binary(b'FCS1.0.........', False)
    assert check_binary(b'FCS............', False)
    assert not check_binary(b'FC.........', False)
    assert not check_binary(b'Hello world', False)


def test_check_binary_files():
    curr_dir = os.path.abspath(os.path.dirname(__file__))
    test_data_dir = os.path.join(curr_dir, '../../../lib/galaxy/datatypes/test')
    count = 0
    for f in os.listdir(test_data_dir):
        if check_binary(os.path.join(test_data_dir, f)):
            count += 1
    assert count == EXPECTED_NUMBER_OF_BINARY_FILES
