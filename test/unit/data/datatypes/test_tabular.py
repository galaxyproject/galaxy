import tempfile

import pytest

from galaxy.datatypes.tabular import (
    MAX_DATA_LINES,
    Tabular,
)
from galaxy.exceptions import RequestParameterInvalidException
from .util import MockDataset


def test_tabular_set_meta_large_file():
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        for _ in range(MAX_DATA_LINES + 1):
            test_file.write("A\tB\n")
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(dataset)  # type: ignore [arg-type]
        # data and comment lines are not stored if more than MAX_DATA_LINES
        assert dataset.metadata.data_lines is None
        assert dataset.metadata.comment_lines is None
        assert dataset.metadata.column_types == ["str", "str"]
        assert dataset.metadata.columns == 2
        assert dataset.metadata.delimiter == "\t"
        assert not hasattr(dataset.metadata, "column_names")


def test_tabular_set_meta_empty():
    """
    empty file
    """
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(dataset)  # type: ignore [arg-type]
        # data and comment lines are not stored if more than MAX_DATA_LINES
        assert dataset.metadata.data_lines == 0
        assert dataset.metadata.comment_lines == 0
        assert dataset.metadata.column_types == []
        assert dataset.metadata.columns == 0
        assert dataset.metadata.delimiter == "\t"
        assert not hasattr(dataset.metadata, "column_names")


def test_tabular_set_meta_nearly_empty():
    """
    file just containing a single new line
    - empty lines are treated as comments
    """
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write("\n")
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(dataset)  # type: ignore [arg-type]
        # data and comment lines are not stored if more than MAX_DATA_LINES
        assert dataset.metadata.data_lines == 0
        assert dataset.metadata.comment_lines == 1
        assert dataset.metadata.column_types == []
        assert dataset.metadata.columns == 0
        assert dataset.metadata.delimiter == "\t"
        assert not hasattr(dataset.metadata, "column_names")


def test_tabular_column_types():
    """
    file containing a single containing only tab characters terminated with a new line character
    - empty lines are treated as comments
    """
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        # 1st line has special treatment which we want to ignore in this test
        test_file.write("\t\t\t\t\n")
        # note that the 1st column of this line will be detected as None
        # but this is overwritten by the default column type (str) after
        # checking all lines
        test_file.write("\tstr\t23\t42.00\ta,b,c\n")
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(dataset)  # type: ignore [arg-type]
        # data and comment lines are not stored if more than MAX_DATA_LINES
        assert dataset.metadata.data_lines == 2
        assert dataset.metadata.comment_lines == 0
        assert dataset.metadata.column_types == ["str", "str", "int", "float", "list"]
        assert dataset.metadata.columns == 5
        assert dataset.metadata.delimiter == "\t"
        assert not hasattr(dataset.metadata, "column_names")


def test_tabular_column_types_override():
    """
    check that guessed column types can be improved
    by the types guessed for later lines
    overwriting is only possible in the following order None -> int -> float -> list -> str

    also check that more columns can be added by later lines
    """
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        # 1st line has special treatment which we want to ignore in this test
        test_file.write("\t\t\t\t\n")
        # note that the first column in detected as None which can be overwritten by int
        test_file.write("\t23\t42.00\ta,b,c\tstr\n")
        test_file.write("23\t42.0\t23,42.0\tstr\t42\tanother column\n")
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(dataset)  # type: ignore [arg-type]
        # data and comment lines are not stored if more than MAX_DATA_LINES
        assert dataset.metadata.data_lines == 3
        assert dataset.metadata.comment_lines == 0
        assert dataset.metadata.column_types == ["int", "float", "list", "str", "str", "str"]
        assert dataset.metadata.columns == 6
        assert dataset.metadata.delimiter == "\t"
        assert not hasattr(dataset.metadata, "column_names")


@pytest.mark.parametrize(
    "value, expected",
    [("3", 3), (3, 3), ("0", 0), (" 7 ", 7), (None, None), ("", None), (3.0, 3)],
)
def test_tabular_comment_lines_unwrap_stores_int(value, expected):
    spec = Tabular.metadata_spec["comment_lines"]
    unwrapped = spec.unwrap(value)
    assert unwrapped == expected
    assert type(unwrapped) is type(expected)
    assert spec.unwrap(unwrapped) == expected


@pytest.mark.parametrize("value", ["abc", "2.5", True, False, 3.7])
def test_tabular_comment_lines_unwrap_rejects_non_integer(value):
    with pytest.raises(RequestParameterInvalidException):
        Tabular.metadata_spec["comment_lines"].unwrap(value)


@pytest.mark.parametrize("stored, expected", [("3", 3), (3, 3), (None, None), ("abc", "abc")])
def test_tabular_comment_lines_wrap_converts_stored_strings(stored, expected):
    assert Tabular.metadata_spec["comment_lines"].wrap(stored, None) == expected
