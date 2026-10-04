import csv
import subprocess
import sys

import pyarrow as pa
import pyarrow.parquet as parquet
import pytest

from ._parquet_converter_test_utils import (
    converter_script,
    run_converter,
    to_parquet,
)


def test_mixed_column_cli_retains_text(tmp_path):
    source = tmp_path / "input.tabular"
    destination = tmp_path / "output.parquet"
    source.write_text("value\n1\ntext\n", encoding="utf-8")
    run_converter("tabular_to_parquet_converter", source, destination, "--header-mode", "first")
    assert parquet.read_table(destination).to_pydict() == {"value": ["1", "text"]}


def test_headerless_tabular_preserves_first_row(tmp_path):
    source = tmp_path / "input.tabular"
    source.write_text("1\tapple\n2\tpear\n", encoding="utf-8")
    table = to_parquet.read_table(source)
    assert table.to_pydict() == {"column1": [1, 2], "column2": ["apple", "pear"]}


def test_explicit_commented_header_preserves_all_data(tmp_path):
    source = tmp_path / "input.tabular"
    source.write_text("\n#CHROM\tPOS\nchr1\t10\n# comment\nchr2\t20\n", encoding="utf-8")
    assert to_parquet.read_table(source, header_mode="first").to_pydict() == {
        "#CHROM": ["chr1", "chr2"],
        "POS": [10, 20],
    }


def test_tsv_read_restores_csv_field_limit_on_success_and_failure(tmp_path):
    source = tmp_path / "input.tsv"
    previous = csv.field_size_limit(128)
    try:
        source.write_text("name\n" + "x" * 1000 + "\n", encoding="utf-8")
        assert to_parquet.read_table(source, input_format="tsv", header_mode="first").num_rows == 1
        assert csv.field_size_limit() == 128
        source.write_text('name\n"unterminated\n', encoding="utf-8")
        with pytest.raises(csv.Error):
            to_parquet.read_table(source, input_format="tsv", header_mode="first")
        assert csv.field_size_limit() == 128
    finally:
        csv.field_size_limit(previous)


@pytest.mark.parametrize("name", ["tabular_to_parquet_converter"])
def test_tabular_to_parquet_cli_missing_input_has_a_friendly_error(tmp_path, name):
    result = subprocess.run(
        [sys.executable, str(converter_script(name)), str(tmp_path / "missing"), str(tmp_path / "output")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "No such file" in result.stderr
    assert "Traceback" not in result.stderr


def test_tabular_to_parquet_cli_empty_input_has_a_friendly_error(tmp_path):
    source = tmp_path / "empty.tabular"
    source.touch()
    result = subprocess.run(
        [sys.executable, str(converter_script("tabular_to_parquet_converter")), str(source), str(tmp_path / "output")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Input has no columns" in result.stderr
    assert "Traceback" not in result.stderr


def test_tabular_to_parquet_cli_missing_pyarrow_has_an_installation_hint(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(converter_script("tabular_to_parquet_converter")),
            str(tmp_path / "input"),
            str(tmp_path / "output"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "pyarrow is not installed" in result.stderr
    assert "Install the converter's pyarrow requirement" in result.stderr
    assert "Traceback" not in result.stderr


def test_tabular_to_parquet_cli_malformed_tsv_has_a_friendly_error(tmp_path):
    source = tmp_path / "input.tsv"
    source.write_text('name\n"unterminated\n', encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(converter_script("tabular_to_parquet_converter")),
            str(source),
            str(tmp_path / "output"),
            "--input-format",
            "tsv",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "unexpected end of data" in result.stderr
    assert "Traceback" not in result.stderr


def test_explicit_header_and_header_only_input(tmp_path):
    source = tmp_path / "input.tabular"
    source.write_text("number\tlabel\n1\tapple\n", encoding="utf-8")
    assert to_parquet.read_table(source, header_mode="first").to_pydict() == {
        "number": [1],
        "label": ["apple"],
    }
    source.write_text("number\tlabel\n", encoding="utf-8")
    table = to_parquet.read_table(source, header_mode="first")
    assert table.column_names == ["number", "label"]
    assert table.num_rows == 0


@pytest.mark.parametrize(
    "values, expected, expected_type",
    [
        (["1", "text", "001", "NA", ""], ["1", "text", "001", "NA", None], pa.string()),
        (["1", "2", ""], [1, 2, None], pa.int64()),
        (["1", "2.5", ""], [1.0, 2.5, None], pa.float64()),
        (["001", "002"], ["001", "002"], pa.string()),
        ([str(2**63), "1"], [str(2**63), "1"], pa.string()),
        ([str(2**53 + 1), "1.5"], [str(2**53 + 1), "1.5"], pa.string()),
        (["1e999", "1.5"], ["1e999", "1.5"], pa.string()),
        (["1e-999", "1.5"], ["1e-999", "1.5"], pa.string()),
        (["9007199254740993e0", "1.5"], ["9007199254740993e0", "1.5"], pa.string()),
        (["9007199254740993.5", "1.5", ""], ["9007199254740993.5", "1.5", None], pa.string()),
        (["-9007199254740993.5", "1.5"], ["-9007199254740993.5", "1.5"], pa.string()),
        (["9.0071992547409935e15", "1.5"], ["9.0071992547409935e15", "1.5"], pa.string()),
        (["9007199254740992.0", "1.5"], [float(2**53), 1.5], pa.float64()),
        (["0.1", "2.5"], [0.1, 2.5], pa.float64()),
        (["9" * 5000, "1"], ["9" * 5000, "1"], pa.string()),
        (["", ""], [None, None], pa.string()),
    ],
)
def test_column_inference_preserves_original_mixed_values(values, expected, expected_type):
    column = to_parquet._column_array(values)
    assert column.to_pylist() == expected
    assert column.type == expected_type


def test_tsv_header_can_be_disabled_and_tabular_quotes_are_literal(tmp_path):
    source = tmp_path / "input.tsv"
    source.write_text('"first"\t1\n"second"\t2\n', encoding="utf-8")
    assert to_parquet.read_table(source, input_format="tsv", header_mode="none").to_pydict() == {
        "column1": ["first", "second"],
        "column2": [1, 2],
    }
    assert to_parquet.read_table(source).column(0).to_pylist() == ['"first"', '"second"']


def test_generic_tabular_comments_and_blank_lines(tmp_path):
    source = tmp_path / "input.tabular"
    source.write_text("# comment\n\n1\tapple\n\n\t\n2\tpear\n", encoding="utf-8")
    assert to_parquet.read_table(source).to_pydict() == {"column1": [1, None, 2], "column2": ["apple", None, "pear"]}
    source.write_text("label\tvalue\n#literal\t1\n", encoding="utf-8")
    assert to_parquet.read_table(source, input_format="tsv", header_mode="first").to_pydict() == {
        "label": ["#literal"],
        "value": [1],
    }


@pytest.mark.parametrize(
    "text, header_mode",
    [
        ("a\tb\n1\n", "first"),
        ("1\t2\n3\t4\t5\n", "none"),
        ("a\ta\n1\t2\n", "first"),
        ("\ta\n1\t2\n", "first"),
        ("", "none"),
    ],
)
def test_invalid_input_is_rejected_instead_of_losing_data(tmp_path, text, header_mode):
    source = tmp_path / "input.tabular"
    source.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        to_parquet.read_table(source, header_mode=header_mode)
