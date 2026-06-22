import json
import tempfile
from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.tabular import (
    CSV,
    MAX_DATA_LINES,
    Tabular,
    TabularData,
)
from .util import MockDataset


def _dataset_protocol(dataset: MockDataset) -> DatasetProtocol:
    return cast(DatasetProtocol, dataset)


def _display_peek(datatype: TabularData, dataset: MockDataset, contents: str) -> str:
    metadata = cast(Any, dataset.metadata)
    metadata.spec = {}
    if not hasattr(metadata, "column_names"):
        metadata.column_names = []
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


def test_tabular_quick_view_keeps_header_like_first_row_as_data():
    contents = "question_id\tcurator_name\nensembl-grab-q1\tLG\nbam-infer-read-length-q1\tSN\n"
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        test_file.write(contents)
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.set_file_name(test_file.name)
        datatype = Tabular()
        datatype.set_meta(_dataset_protocol(dataset))
        assert not hasattr(dataset.metadata, "column_names")
        html = _display_peek(datatype, dataset, contents)
        assert "<th>1</th>" in html
        assert "<th>2</th>" in html
        assert "<th>1.question_id</th>" not in html
        assert "<td>question_id</td>" in html
        assert "<td>curator_name</td>" in html


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
