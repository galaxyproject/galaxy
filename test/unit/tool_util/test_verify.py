import collections
import gzip
import tempfile
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
)

import pytest

from galaxy.tool_util.verify import (
    files_contains,
    files_delta,
    files_diff,
    files_re_match,
    files_re_match_multiline,
)

F1 = b"A\nB\nC"
F2 = b"A\nB\nD\nE" * 61
F3 = b"A\nB\n\xfc"
F4 = b"A\r\nB\nC"
MULTILINE_MATCH = b".*"
TestFile = collections.namedtuple("TestFile", "value path")

TestDef = Tuple[bytes, bytes, Optional[Dict[str, Any]], Optional[Type[AssertionError]]]


def test_file_list():
    files = []
    for b, ext in [(F1, ".txt"), (F2, ".txt"), (F3, ".pdf"), (F4, ".txt"), (MULTILINE_MATCH, ".txt"), (F1, ".txt.gz")]:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=ext, delete=False) as out:
            if ext == ".txt.gz":
                b = gzip.compress(b)
            out.write(b)
        files.append(TestFile(b, out.name))
    return files


def generate_tests(multiline=False):
    f1, f2, f3, f4, multiline_match, f5 = test_file_list()
    tests: List[TestDef]
    if multiline:
        tests = [(multiline_match, f1, {"lines_diff": 0, "sort": True}, None)]
    else:
        tests = [(f1, f1, {"lines_diff": 0, "sort": True}, None)]
    tests.extend(
        [
            (f1, f2, {"lines_diff": 0, "sort": True}, AssertionError),
            (f1, f3, None, AssertionError),
            (f1, f4, None, None),
            (f1, f5, {"decompress": True}, None),
        ]
    )
    return tests


def generate_tests_sim_size():
    f1, f2, f3, f4, multiline_match, f5 = test_file_list()
    # tests for equal files
    tests: List[TestDef] = [
        (f1, f1, None, None),  # pass default values
        (f1, f1, {"delta": 0}, None),  # pass for values that should always pass
        (f1, f1, {"delta_frac": 0.0}, None),
    ]
    # tests for two different file (diff is 422 lines, 0.011709602)
    tests += [
        (f1, f2, None, None),  # pass default values
        (f1, f2, {"delta": 422}, None),  # test around the actual difference of two different
        (f1, f2, {"delta_frac": 84.4}, None),
        (f1, f2, {"delta": 421}, AssertionError),
        (f1, f2, {"delta_frac": 84.3}, AssertionError),
        (
            f1,
            f2,
            {"delta": 422, "delta_frac": 84.3},
            AssertionError,
        ),  # test with combination where at least one leads to an assertion
        (f1, f2, {"delta": 421, "delta_frac": 84.4}, AssertionError),
    ]
    return tests


@pytest.mark.parametrize("file1,file2,attributes,expect", generate_tests())
def test_files_contains(file1, file2, attributes, expect):
    if expect is not None:
        with pytest.raises(expect):
            files_contains(file1.path, file2.path, attributes)
    else:
        files_contains(file2.path, file2.path, attributes)


@pytest.mark.parametrize("file1,file2,attributes,expect", generate_tests_sim_size())
def test_files_delta(file1, file2, attributes, expect):
    if expect is not None:
        with pytest.raises(expect):
            files_delta(file1.path, file2.path, attributes)
    else:
        files_delta(file1.path, file2.path, attributes)


@pytest.mark.parametrize("file1,file2,attributes,expect", generate_tests())
def test_files_diff(file1, file2, attributes, expect):
    if expect is not None:
        with pytest.raises(expect):
            files_diff(file1.path, file2.path, attributes)
    else:
        files_diff(file1.path, file2.path, attributes)


@pytest.mark.parametrize("file1,file2,attributes,expect", generate_tests())
def test_files_re_match(file1, file2, attributes, expect):
    if expect is not None:
        with pytest.raises(expect):
            files_re_match(file1.path, file2.path, attributes)
    else:
        files_re_match(file1.path, file2.path, attributes)


@pytest.mark.parametrize("file1,file2,attributes,expect", generate_tests(multiline=True))
def test_files_re_match_multiline(file1, file2, attributes, expect):
    if expect is not None:
        with pytest.raises(expect):
            files_re_match_multiline(file1.path, file2.path, attributes)
    else:
        files_re_match_multiline(file1.path, file2.path, attributes)
