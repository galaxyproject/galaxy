import csv
import json
import tempfile
from typing import (
    Any,
    cast,
)

import pytest

from galaxy.datatypes.interval import (
    Bed,
    Interval,
)
from galaxy.datatypes.tabular import (
    column_index_header_cell,
    CSV,
    MAX_DATA_LINES,
    Tabular,
    TSV,
)
from galaxy.exceptions import RequestParameterInvalidException
from .util import (
    MockDataset,
    MockMetadata,
)


def _write_delimited(path, datatype, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, dialect=datatype.dialect).writerows(rows)


@pytest.mark.parametrize("datatype", [CSV(), TSV()], ids=["csv", "tsv"])
def test_delimited_display_peek_keeps_header_line_in_rows(tmp_path, datatype):
    # The column index shows the names, and the header line is still shown as a line of the file.
    source = tmp_path / f"input.{datatype.file_ext}"
    _write_delimited(source, datatype, [["name", "value"], ["first", "1"]])
    dataset = MockDataset(id=1)
    dataset.set_file_name(str(source))
    datatype.set_meta(dataset)
    cast(Any, dataset.metadata).spec = {}
    cast(Any, dataset).peek = source.read_text()

    html = datatype.display_peek(dataset)

    assert column_index_header_cell("1", "name") in html
    assert "<td>name</td>" in html
    assert "<td>first</td>" in html


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


def test_tabular_display_peek_header_numbers_columns():
    dataset = MockDataset(id=1)
    dataset_for_peek = cast(Any, dataset)
    metadata = cast(Any, dataset.metadata)
    dataset_for_peek.peek = "question_id\tcurator_name\nensembl-grab-q1\tLG\n"
    metadata.columns = 2
    metadata.delimiter = "\t"
    metadata.column_names = None
    metadata.spec = MockMetadata()

    html = Tabular().display_peek(dataset)  # type: ignore [arg-type]

    assert f"<tr>{column_index_header_cell('1')}{column_index_header_cell('2')}</tr>" in html
    assert "<td>question_id</td>" in html


def test_tabular_display_peek_header_includes_metadata_column_names():
    dataset = MockDataset(id=1)
    dataset_for_peek = cast(Any, dataset)
    metadata = cast(Any, dataset.metadata)
    dataset_for_peek.peek = "FBgn0026562\t43868.5\nFBgn0039155\t735.9\n"
    metadata.columns = 2
    metadata.delimiter = "\t"
    metadata.column_names = ["GeneID", "Base mean"]
    metadata.spec = MockMetadata()

    html = Tabular().display_peek(dataset)  # type: ignore [arg-type]

    assert column_index_header_cell("1", "GeneID") + column_index_header_cell("2", "Base mean") in html
    assert "<td>FBgn0026562</td>" in html


def _dataset_with_metadata(tmp_path, datatype, text):
    source = tmp_path / f"input.{datatype.file_ext}"
    source.write_text(text)
    dataset = MockDataset(id=1)
    dataset.set_file_name(str(source))
    metadata = cast(Any, dataset.metadata)
    metadata.spec = datatype.metadata_spec
    metadata.column_names = datatype.metadata_spec.column_names.no_value
    datatype.set_meta(dataset)
    cast(Any, dataset).peek = text
    return dataset


def test_bed_preview_chunk_and_peek_name_the_same_columns(tmp_path):
    bed = Bed()
    dataset = _dataset_with_metadata(tmp_path, bed, "chr1\t100\t200\tfeature\t0\t+\n")

    chunk = json.loads(bed.get_chunk(None, dataset, 0, 1024))
    html = bed.display_peek(dataset)

    assert chunk["column_names"] == ["Chrom", "Start", "End", "Name", "Score", "Strand"]
    peek_cells = "".join(column_index_header_cell(str(i + 1), name) for i, name in enumerate(chunk["column_names"]))
    assert f"<tr>{peek_cells}</tr>" in html


def test_interval_preview_chunk_names_column_parameters(tmp_path):
    interval = Interval()
    dataset = _dataset_with_metadata(tmp_path, interval, "feature\tchr1\t100\t200\t+\n")
    metadata = cast(Any, dataset.metadata)
    metadata.chromCol, metadata.startCol, metadata.endCol, metadata.strandCol = 2, 3, 4, 5

    chunk = json.loads(interval.get_chunk(None, dataset, 0, 1024))

    assert chunk["column_names"] == [None, "Chrom", "Start", "End", "Strand"]


def test_column_index_header_cell_escapes_name():
    assert column_index_header_cell("1") == (
        '<th title="Column 1. Galaxy metadata, not part of the file."><span class="column-index">'
        '<span class="column-number">1</span></span></th>'
    )
    assert column_index_header_cell("2", 'log2(FC) "<b>') == (
        '<th title="Column 2: log2(FC) &#34;&lt;b&gt;. Galaxy metadata, not part of the file.">'
        '<span class="column-index"><span class="column-number">2</span>'
        ' <span class="column-name">log2(FC) &#34;&lt;b&gt;</span></span></th>'
    )


@pytest.mark.parametrize(
    "value, expected",
    [("3", 3), (3, 3), ("0", 0), (" 7 ", 7), (None, None), ("", None), (3.0, 3), (["7"], 7), ([3], 3)],
)
def test_tabular_comment_lines_unwrap_stores_int(value, expected):
    spec = Tabular.metadata_spec["comment_lines"]
    unwrapped = spec.unwrap(value)
    assert unwrapped == expected
    assert type(unwrapped) is type(expected)
    assert spec.unwrap(unwrapped) == expected


@pytest.mark.parametrize("value", ["abc", "2.5", True, False, 3.7, [], ["3", "7"], [True], [3.7], [["7"]]])
def test_tabular_comment_lines_unwrap_rejects_non_integer(value):
    with pytest.raises(RequestParameterInvalidException):
        Tabular.metadata_spec["comment_lines"].unwrap(value)


@pytest.mark.parametrize("stored, expected", [("3", 3), (3, 3), (["7"], 7), (None, None), ("abc", "abc")])
def test_tabular_comment_lines_wrap_converts_stored_strings(stored, expected):
    assert Tabular.metadata_spec["comment_lines"].wrap(stored, None) == expected
