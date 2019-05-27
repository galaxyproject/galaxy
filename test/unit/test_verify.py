import collections
import os
import tempfile

import pytest

from galaxy.tools.verify import (
    files_contains,
    files_diff,
    files_re_match,
    files_re_match_multiline,
)


F1 = b"A\nB\nC"
F2 = b"A\nB\nD\nE" * 61
F3 = b"A\nB\n\xfc"
F4 = b"A\r\nB\nC"
MULTILINE_MATCH = b".*"
TestFile = collections.namedtuple('TestFile', 'value path')


def generate_tests(multiline=False):
    files = []
    for b, ext in [(F1, '.txt'), (F2, '.txt'), (F3, '.pdf'), (F4, '.txt'), (MULTILINE_MATCH, '.txt')]:
        fd, path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, 'wb') as out:
            out.write(b)
        files.append(TestFile(b, path))
    f1, f2, f3, f4, multiline_match = files
    if multiline:
        tests = [(multiline_match, f1, {'lines_diff': 0, 'sort': True}, None)]
    else:
        tests = [(f1, f1, {'lines_diff': 0, 'sort': True}, None)]
    tests.extend([
        (f1, f2, {'lines_diff': 0, 'sort': True}, AssertionError),
        (f1, f3, None, AssertionError),
        (f1, f4, None, None),
    ])
    return tests


@pytest.mark.parametrize('file1,file2,attributes,expect', generate_tests())
def test_files_contains(file1, file2, attributes, expect):
    if expect is not None:
        with pytest.raises(expect):
            files_contains(file1.path, file2.path, attributes)
    else:
        files_contains(file2.path, file2.path, attributes)


@pytest.mark.parametrize('file1,file2,attributes,expect', generate_tests())
def test_files_diff(file1, file2, attributes, expect):
    if expect is not None:
        with pytest.raises(expect):
            files_diff(file1.path, file2.path, attributes)
    else:
        files_diff(file1.path, file2.path, attributes)


@pytest.mark.parametrize('file1,file2,attributes,expect', generate_tests())
def test_files_re_match(file1, file2, attributes, expect):
    if expect is not None:
        with pytest.raises(expect):
            files_re_match(file1.path, file2.path, attributes)
    else:
        files_re_match(file1.path, file2.path, attributes)


@pytest.mark.parametrize('file1,file2,attributes,expect', generate_tests(multiline=True))
def test_files_re_match_multiline(file1, file2, attributes, expect):
    if expect is not None:
        with pytest.raises(expect):
            files_re_match_multiline(file1.path, file2.path, attributes)
    else:
        files_re_match_multiline(file1.path, file2.path, attributes)
