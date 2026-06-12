import csv
import json
import tempfile
from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

import pytest

from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.tabular import (
    CSV,
    MAX_DATA_LINES,
    Tabular,
    TabularData,
    TSV,
)
from galaxy.exceptions import RequestParameterInvalidException
from .util import MockDataset


@pytest.mark.parametrize("datatype", [CSV(), TSV()], ids=["csv", "tsv"])
@pytest.mark.parametrize(
    "header, rows",
    [
        (["name", "value"], []),
        (["name", "value"], [["first", "1"]]),
        (["name", "value"], [["first", "1"], ["second", "text"]]),
        (["name", "value"], [["first\nnext\rline", "1"], ["second", "2"]]),
        (["name\ncontinued", "value"], [["first", "1"]]),
        (["name\ncontinued", "value"], [["first\nnext", "1"], ["second\nnext", "2"]]),
    ],
    ids=["header_only", "one_row", "two_rows", "multiline_cell", "multiline_header", "multiline_both"],
)
def test_delimited_metadata_counts_logical_records(tmp_path, datatype, header, rows):
    source = tmp_path / f"input.{datatype.file_ext}"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, dialect=datatype.dialect)
        writer.writerow(header)
        writer.writerows(rows)
    dataset = MockDataset(id=1)
    dataset.set_file_name(str(source))
    datatype.set_meta(dataset)
    assert dataset.metadata.data_lines == len(rows)
    assert dataset.metadata.comment_lines == 1
    assert dataset.metadata.columns == 2
    assert dataset.metadata.column_names == header
    assert dataset.metadata.delimiter == datatype.dialect.delimiter
    # Type inference remains based on the first data record, not a later one.
    assert dataset.metadata.column_types == (["str", "int"] if rows else [])


@pytest.mark.parametrize("datatype", [CSV(), TSV()], ids=["csv", "tsv"])
def test_delimited_metadata_empty_input(tmp_path, datatype):
    source = tmp_path / f"empty.{datatype.file_ext}"
    source.touch()
    dataset = MockDataset(id=1)
    dataset.set_file_name(str(source))
    datatype.set_meta(dataset)
    assert dataset.metadata.data_lines == 0
    assert dataset.metadata.comment_lines == 0
    assert dataset.metadata.column_types == []
    assert dataset.metadata.columns == 0
    assert dataset.metadata.column_names == []


def _dataset_protocol(dataset: MockDataset) -> DatasetProtocol:
    return cast(DatasetProtocol, dataset)


def _display_peek(datatype: TabularData, dataset: MockDataset, contents: str) -> str:
    metadata = cast(Any, dataset.metadata)
    metadata.spec = {}
    dataset_for_peek = cast(Any, dataset)
    dataset_for_peek.peek = contents
    return datatype.display_peek(_dataset_protocol(dataset))


def test_tabular_set_meta_large_file():
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        for _ in range(MAX_DATA_LINES + 1):
            test_file.write("A\tB\n")
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(_dataset_protocol(dataset))
        # data and comment lines are not stored if more than MAX_DATA_LINES
        assert dataset.metadata.data_lines is None
        assert dataset.metadata.comment_lines is None
        assert dataset.metadata.column_types == ["str", "str"]
        assert dataset.metadata.columns == 2
        assert dataset.metadata.delimiter == "\t"
        assert not hasattr(dataset.metadata, "column_names")


def test_tabular_set_meta_with_header():
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write("TMB\tSystemic_therapy_history\tAlbumin\n")
        test_file.write("32.5\t1\t4.3\n")
        test_file.write("19.3\t1\t3.8\n")
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(_dataset_protocol(dataset))
        assert dataset.metadata.data_lines == 2
        assert dataset.metadata.comment_lines == 1
        assert dataset.metadata.column_types == ["float", "int", "float"]
        assert dataset.metadata.columns == 3
        assert dataset.metadata.delimiter == "\t"
        assert dataset.metadata.column_names == ["TMB", "Systemic_therapy_history", "Albumin"]


def test_tabular_quick_view_uses_column_names_only_as_headers():
    contents = "question_id\tcurator_name\nensembl-grab-q1\tLG\nbam-infer-read-length-q1\tSN\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        datatype = Tabular()
        datatype.set_meta(_dataset_protocol(dataset))
        html = _display_peek(datatype, dataset, contents)
        assert "<th>1.question_id</th>" in html
        assert "<th>2.curator_name</th>" in html
        assert "<td>question_id</td>" not in html
        assert "<td>curator_name</td>" not in html


def test_headerless_numeric_tabular_set_meta_does_not_promote_first_row_to_header():
    contents = "32.5\t1\t4.3\n19.3\t1\t3.8\n10.5\t1\t4.2\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(_dataset_protocol(dataset))
        assert dataset.metadata.data_lines == 3
        assert dataset.metadata.comment_lines == 0
        assert dataset.metadata.column_types == ["float", "int", "float"]
        assert dataset.metadata.columns == 3
        assert not hasattr(dataset.metadata, "column_names")


def test_single_row_numeric_tabular_set_meta_does_not_promote_first_row_to_header():
    contents = "32.5\t1\t4.3\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(_dataset_protocol(dataset))
        assert dataset.metadata.data_lines == 1
        assert dataset.metadata.comment_lines == 0
        assert dataset.metadata.column_types == ["float", "int", "float"]
        assert dataset.metadata.columns == 3
        assert not hasattr(dataset.metadata, "column_names")


def test_tabular_set_meta_preserves_existing_column_names_for_headerless_data():
    contents = "32.5\t1\t4.3\n19.3\t1\t3.8\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        metadata = cast(Any, dataset.metadata)
        metadata.column_names = ["First", "2.tabular"]
        Tabular().set_meta(_dataset_protocol(dataset))
        assert dataset.metadata.data_lines == 2
        assert dataset.metadata.comment_lines == 0
        assert dataset.metadata.column_names == ["First", "2.tabular"]


def test_tabular_set_meta_replaces_existing_column_names_when_header_is_detected():
    with tempfile.NamedTemporaryFile(mode="w") as header_file, tempfile.NamedTemporaryFile(mode="w") as data_file:
        header_file.write("name\tvalue\nA\t1\nB\t2\n")
        header_file.flush()
        data_file.write("sample\tcount\nC\t3\nD\t4\n")
        data_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(header_file.name)
        datatype = Tabular()
        datatype.set_meta(_dataset_protocol(dataset))
        assert dataset.metadata.column_names == ["name", "value"]
        dataset.set_file_name(data_file.name)
        datatype.set_meta(_dataset_protocol(dataset))
        assert dataset.metadata.data_lines == 2
        assert dataset.metadata.comment_lines == 1
        assert dataset.metadata.column_names == ["sample", "count"]


def test_tabular_set_meta_does_not_use_comment_line_as_column_names():
    contents = "#comment\tthing\n1\t2\n3\t4\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(_dataset_protocol(dataset))
        assert dataset.metadata.data_lines == 2
        assert dataset.metadata.comment_lines == 1
        assert dataset.metadata.column_types == ["int", "int"]
        assert dataset.metadata.columns == 2
        assert not hasattr(dataset.metadata, "column_names")


def test_tabular_quick_view_skips_header_when_line_counts_are_unset():
    contents = "name\tvalue\nA\t1\nB\t2\nC\t3\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        datatype = Tabular()
        datatype.set_meta(_dataset_protocol(dataset), max_data_lines=2)
        html = _display_peek(datatype, dataset, contents)
        assert dataset.metadata.data_lines is None
        assert dataset.metadata.comment_lines is None
        assert dataset.metadata.column_names == ["name", "value"]
        assert "<th>1.name</th>" in html
        assert "<th>2.value</th>" in html
        assert "<td>name</td>" not in html
        assert "<td>value</td>" not in html


def test_tabular_quick_view_skips_header_after_comments_when_line_counts_are_unset():
    contents = "# generated\nname\tvalue\nA\t1\nB\t2\nC\t3\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        datatype = Tabular()
        datatype.set_meta(_dataset_protocol(dataset), max_data_lines=2)
        html = _display_peek(datatype, dataset, contents)
        assert dataset.metadata.data_lines is None
        assert dataset.metadata.comment_lines is None
        assert dataset.metadata.column_names == ["name", "value"]
        assert "<th>1.name</th>" in html
        assert "<th>2.value</th>" in html
        assert "<td># generated</td>" not in html
        assert "<td>name</td>" not in html
        assert "<td>A</td>" in html


def test_tabular_quick_view_uses_peek_for_unset_line_count_offset():
    contents = "name\tvalue\nA\t1\nB\t2\nC\t3\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        datatype = Tabular()
        datatype.set_meta(_dataset_protocol(dataset), max_data_lines=2)

        def fail_get_file_name(sync_cache=True):
            raise AssertionError("quick view should not open the dataset file")

        dataset_for_peek = cast(Any, dataset)
        dataset_for_peek.get_file_name = fail_get_file_name
        html = _display_peek(datatype, dataset, contents)
        assert "<th>1.name</th>" in html
        assert "<td>name</td>" not in html
        assert "<td>A</td>" in html


def test_csv_quick_view_uses_column_names_only_as_headers():
    contents = "TMB,Systemic_therapy_history,Albumin\n32.5,1,4.3\n19.3,1,3.8\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        datatype = CSV()
        datatype.set_meta(_dataset_protocol(dataset))
        html = _display_peek(datatype, dataset, contents)
        assert "<th>1.TMB</th>" in html
        assert "<th>2.Systemic_therapy_history</th>" in html
        assert "<td>TMB</td>" not in html
        assert "<td>Systemic_therapy_history</td>" not in html


def test_headerless_csv_sniffs_as_csv():
    contents = (
        "32.5,1,4.3,1.19,67.91512663,0,0,0,1,0\n"
        "19.3,1,3.8,1.38,62.50239562,0,0,0,0,0\n"
        "10.5,1,4.2,2.54,52.10677618,0,0,0,0,0\n"
    )
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        assert CSV().sniff(test_file.name)


def test_headerless_csv_set_meta_does_not_promote_first_row_to_header():
    contents = (
        "32.5,1,4.3,1.19,67.91512663,0,0,0,1,0\n"
        "19.3,1,3.8,1.38,62.50239562,0,0,0,0,0\n"
        "10.5,1,4.2,2.54,52.10677618,0,0,0,0,0\n"
    )
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        datatype = CSV()
        datatype.set_meta(_dataset_protocol(dataset))
        assert dataset.metadata.data_lines == 3
        assert dataset.metadata.comment_lines == 0
        assert dataset.metadata.column_names == []
        assert dataset.metadata.columns == 10


def test_headerless_csv_quick_view_keeps_first_row_as_data():
    contents = "32.5,1,4.3\n19.3,1,3.8\n10.5,1,4.2\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        datatype = CSV()
        datatype.set_meta(_dataset_protocol(dataset))
        html = _display_peek(datatype, dataset, contents)
        assert "<th>1</th>" in html
        assert "<th>2</th>" in html
        assert "<td>32.5</td>" in html
        assert "<td>4.3</td>" in html


def test_csv_chunked_view_skips_header_only_in_first_chunk():
    contents = "A,B\n1,2\n3,4\n5,6\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        datatype = CSV()
        datatype.set_meta(_dataset_protocol(dataset))
        trans = SimpleNamespace(app=SimpleNamespace(config=SimpleNamespace(display_chunk_size=6)))
        first_chunk = json.loads(datatype.get_chunk(trans, _dataset_protocol(dataset), 0, 6))
        next_chunk = json.loads(datatype.get_chunk(trans, _dataset_protocol(dataset), first_chunk["offset"], 6))
        assert first_chunk["data_line_offset"] == 1
        assert next_chunk["data_line_offset"] == 0


def test_tabular_chunked_view_skips_header_only_in_first_chunk():
    contents = "TMB\tSystemic_therapy_history\n32.5\t1\n19.3\t1\n10.5\t1\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        datatype = Tabular()
        datatype.set_meta(_dataset_protocol(dataset))
        trans = SimpleNamespace(app=SimpleNamespace(config=SimpleNamespace(display_chunk_size=18)))
        first_chunk = json.loads(datatype.get_chunk(trans, _dataset_protocol(dataset), 0, 18))
        next_chunk = json.loads(datatype.get_chunk(trans, _dataset_protocol(dataset), first_chunk["offset"], 18))
        assert first_chunk["data_line_offset"] == 1
        assert next_chunk["data_line_offset"] == 0


def test_tabular_set_meta_empty():
    """
    empty file
    """
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(_dataset_protocol(dataset))
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
        Tabular().set_meta(_dataset_protocol(dataset))
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
        Tabular().set_meta(_dataset_protocol(dataset))
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
        Tabular().set_meta(_dataset_protocol(dataset))
        # data and comment lines are not stored if more than MAX_DATA_LINES
        assert dataset.metadata.data_lines == 3
        assert dataset.metadata.comment_lines == 0
        assert dataset.metadata.column_types == ["int", "float", "list", "str", "str", "str"]
        assert dataset.metadata.columns == 6
        assert dataset.metadata.delimiter == "\t"
        assert not hasattr(dataset.metadata, "column_names")


def test_tabular_display_peek_does_not_render_table_header():
    dataset = MockDataset(id=1)
    dataset_for_peek = cast(Any, dataset)
    metadata = cast(Any, dataset.metadata)
    dataset_for_peek.peek = "question_id\tcurator_name\nensembl-grab-q1\tLG\n"
    metadata.columns = 2
    metadata.delimiter = "\t"

    html = Tabular().display_peek(dataset)  # type: ignore [arg-type]

    assert "<th>" not in html
    assert "<td>question_id</td>" in html
    assert "<td>curator_name</td>" in html


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
