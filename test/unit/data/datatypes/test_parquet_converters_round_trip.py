import csv

import pyarrow as pa
import pyarrow.parquet as parquet
import pytest

from ._parquet_converter_test_utils import (
    ROOT,
    run_converter,
    to_parquet,
    to_tsv,
)


def test_existing_tool_fixtures(tmp_path):
    binary = tmp_path / "output.parquet"
    run_converter(
        "tabular_to_parquet_converter",
        ROOT / "test-data/tabular_to_parquet_conv.tabular",
        binary,
        "--header-mode",
        "first",
    )
    assert parquet.read_table(binary).equals(parquet.read_table(ROOT / "test-data/tabular_to_parquet_conv.parquet"))
    expected_text = (ROOT / "test-data/parq_to_tabular_conv.tabular").read_text(encoding="utf-8")
    for destination_name, args in (("output.tabular", ()), ("output.tsv", ("--output-format", "tsv"))):
        destination = tmp_path / destination_name
        run_converter(
            "parquet_to_tabular_converter", ROOT / "test-data/parq_to_tabular_conv.parquet", destination, *args
        )
        assert destination.read_text(encoding="utf-8") == expected_text


def test_quoted_tsv_round_trip_preserves_cells_and_headers(tmp_path):
    table = pa.table(
        {
            'label\t"name"': ["a\tb", "line\nnext", "carriage\rreturn", '"quoted"', "[literal]", "{literal}", "日本語"],
            "other\ncolumn": ["NA"] * 7,
        }
    )
    source = tmp_path / "input.parquet"
    tsv = tmp_path / "output.tsv"
    destination = tmp_path / "output.parquet"
    parquet.write_table(table, source)
    to_tsv.convert(source, tsv, output_format="tsv")
    with tsv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle, dialect="excel-tab"))
    assert rows == [table.column_names] + [list(row) for row in zip(*table.to_pydict().values())]
    to_parquet.convert(tsv, destination, input_format="tsv", header_mode="first")
    assert parquet.read_table(destination).equals(table)


@pytest.mark.parametrize("output_format", ["tabular", "tsv"])
def test_scalar_parquet_round_trip_preserves_inferred_columns(tmp_path, output_format):
    table = pa.table(
        {
            "integer": pa.array([-(2**63), 2**63 - 1, None, 0, 42], type=pa.int64()),
            "float": pa.array([0.1, 2.5, -3.75, None, 0.0], type=pa.float64()),
            "mixed": ["1", "text", "001", "NA", None],
            "identifier": ["001", "000", "009", None, "042"],
            "large_decimal": ["9007199254740993.5", "1.5", "-9007199254740993.5", None, "9.0071992547409935e15"],
            "overflow_integer": [str(2**63), "1", None, str(-(2**63) - 1), str(2**63 - 1)],
            "nonfinite_text": ["inf", "nan", "-inf", None, "infinity"],
            "literal": ['"quoted"', "[literal]", "{literal}", "日本語", None],
            "all_null": pa.array([None] * 5, type=pa.string()),
        }
    )
    source = tmp_path / "input.parquet"
    text = tmp_path / f"export.{output_format}"
    restored = tmp_path / "restored.parquet"
    parquet.write_table(table, source)
    run_converter("parquet_to_tabular_converter", source, text, "--output-format", output_format)
    run_converter(
        "tabular_to_parquet_converter",
        text,
        restored,
        "--input-format",
        output_format,
        "--header-mode",
        "first",
    )
    actual = parquet.read_table(restored)
    assert actual.num_rows == table.num_rows
    assert actual.schema == table.schema
    assert actual.equals(table)


@pytest.mark.parametrize("output_format", ["tabular", "tsv"])
@pytest.mark.parametrize("header_mode", ["none", "first"], ids=["headerless", "explicit_commented_header"])
def test_plain_tabular_round_trip_preserves_all_data_rows(tmp_path, output_format, header_mode):
    names = (
        ["#CHROM", "mixed", "identifier", "float", "large_decimal", "literal"]
        if header_mode == "first"
        else [f"column{index}" for index in range(1, 7)]
    )
    source = tmp_path / "input.tabular"
    binary = tmp_path / "converted.parquet"
    exported = tmp_path / f"export.{output_format}"
    restored = tmp_path / "restored.parquet"
    header = "\t".join(names) + "\n" if header_mode == "first" else ""
    source.write_text(
        header + "1\tapple\t001\t0.1\t9007199254740993.5\tNA\n2\t1\t002\t2.5\t1.5\ttext\n\t\t\t\t\t\n",
        encoding="utf-8",
    )
    expected = pa.Table.from_arrays(
        [
            pa.array([1, 2, None], type=pa.int64()),
            pa.array(["apple", "1", None]),
            pa.array(["001", "002", None]),
            pa.array([0.1, 2.5, None], type=pa.float64()),
            pa.array(["9007199254740993.5", "1.5", None]),
            pa.array(["NA", "text", None]),
        ],
        names=names,
    )
    run_converter("tabular_to_parquet_converter", source, binary, "--header-mode", header_mode)
    assert parquet.read_table(binary).equals(expected)
    run_converter("parquet_to_tabular_converter", binary, exported, "--output-format", output_format)
    run_converter(
        "tabular_to_parquet_converter",
        exported,
        restored,
        "--input-format",
        output_format,
        "--header-mode",
        "first",
    )
    assert parquet.read_table(restored).equals(expected)


@pytest.mark.parametrize("output_format", ["tabular", "tsv"])
def test_scalar_round_trip_documents_reinference_and_empty_string_loss(tmp_path, output_format):
    source = tmp_path / "input.parquet"
    text = tmp_path / f"export.{output_format}"
    restored = tmp_path / "restored.parquet"
    parquet.write_table(pa.table({"numeric_text": ["1", "2", None], "empty_text": ["", "filled", None]}), source)
    run_converter("parquet_to_tabular_converter", source, text, "--output-format", output_format)
    run_converter(
        "tabular_to_parquet_converter",
        text,
        restored,
        "--input-format",
        output_format,
        "--header-mode",
        "first",
    )
    expected = pa.table({"numeric_text": [1, 2, None], "empty_text": [None, "filled", None]})
    assert parquet.read_table(restored).equals(expected)
