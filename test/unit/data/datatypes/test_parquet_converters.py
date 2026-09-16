import csv
import importlib.util
import json
import subprocess
import sys
from datetime import (
    date,
    datetime,
)
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from xml.etree import ElementTree

import pyarrow as pa
import pyarrow.parquet as parquet
import pytest

from galaxy.datatypes.binary import Parquet
from galaxy.datatypes.registry import Registry
from galaxy.datatypes.tabular import (
    CSV,
    Tabular,
    TSV,
)
from galaxy.util.template import fill_template

ROOT = Path(__file__).resolve().parents[4]
CONVERTERS = ROOT / "lib/galaxy/datatypes/converters"


def load_converter(name):
    spec = importlib.util.spec_from_file_location(name, CONVERTERS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


to_parquet = load_converter("tabular_to_parquet_converter")
to_tsv = load_converter("parquet_to_tabular_converter")


def run_converter(name, source, destination, *args):
    subprocess.run([sys.executable, str(CONVERTERS / f"{name}.py"), str(source), str(destination), *args], check=True)


def test_headerless_cli_does_not_consume_first_row(tmp_path):
    source = tmp_path / "input.tabular"
    destination = tmp_path / "output.parquet"
    source.write_text("1\tapple\n2\tpear\n", encoding="utf-8")
    run_converter("tabular_to_parquet_converter", source, destination)
    assert parquet.read_table(destination).to_pydict() == {"column1": [1, 2], "column2": ["apple", "pear"]}


def test_mixed_column_cli_retains_text(tmp_path):
    source = tmp_path / "input.tabular"
    destination = tmp_path / "output.parquet"
    source.write_text("value\n1\ntext\n", encoding="utf-8")
    run_converter("tabular_to_parquet_converter", source, destination, "--header-mode", "first")
    assert parquet.read_table(destination).to_pydict() == {"value": ["1", "text"]}


def test_export_cli_keeps_tab_and_newline_in_one_cell(tmp_path):
    source = tmp_path / "input.parquet"
    destination = tmp_path / "output.tsv"
    parquet.write_table(pa.table({"text": ["a\tb", "line\nnext", "[literal]"]}), source)
    run_converter("parquet_to_tabular_converter", source, destination, "--output-format", "tsv")
    with destination.open(encoding="utf-8", newline="") as handle:
        assert list(csv.reader(handle, dialect="excel-tab")) == [["text"], ["a\tb"], ["line\nnext"], ["[literal]"]]


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
    tsv = tmp_path / "output.tsv"
    run_converter(
        "parquet_to_tabular_converter", ROOT / "test-data/parq_to_tabular_conv.parquet", tsv, "--output-format", "tsv"
    )
    assert tsv.read_text(encoding="utf-8") == (ROOT / "test-data/parq_to_tabular_conv.tabular").read_text(
        encoding="utf-8"
    )


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
        assert to_parquet.read_table(source, input_format="tsv").num_rows == 1
        assert csv.field_size_limit() == 128
        source.write_text('name\n"unterminated\n', encoding="utf-8")
        with pytest.raises(csv.Error):
            to_parquet.read_table(source, input_format="tsv")
        assert csv.field_size_limit() == 128
    finally:
        csv.field_size_limit(previous)


@pytest.mark.parametrize("value", ["a\tb", "a\nb", "a\rb", "#comment", ""])
def test_plain_export_rejects_unrepresentable_records(tmp_path, value):
    source = tmp_path / "input.parquet"
    destination = tmp_path / "output.tabular"
    parquet.write_table(pa.table({"text": [value]}), source)
    result = subprocess.run(
        [sys.executable, str(CONVERTERS / "parquet_to_tabular_converter.py"), str(source), str(destination)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "quoted TSV" in result.stderr
    assert "Traceback" not in result.stderr


def test_plain_export_keeps_quotes_literal(tmp_path):
    source = tmp_path / "input.parquet"
    destination = tmp_path / "output.tabular"
    parquet.write_table(pa.table({"text": ['"quoted"', "[literal]", "{literal}"]}), source)
    run_converter("parquet_to_tabular_converter", source, destination)
    assert destination.read_text() == 'text\n"quoted"\n[literal]\n{literal}\n'


@pytest.mark.parametrize("name", ["a\tb", "a\nb", "a\rb"])
def test_plain_export_rejects_unrepresentable_headers(tmp_path, name):
    source = tmp_path / "input.parquet"
    destination = tmp_path / "output.tabular"
    parquet.write_table(pa.table({name: ["value"]}), source)
    with pytest.raises(ValueError, match="quoted TSV"):
        to_tsv.convert(source, destination)


@pytest.mark.parametrize("name", ["tabular_to_parquet_converter", "parquet_to_tabular_converter"])
def test_cli_missing_input_has_a_friendly_error(tmp_path, name):
    result = subprocess.run(
        [sys.executable, str(CONVERTERS / f"{name}.py"), str(tmp_path / "missing"), str(tmp_path / "output")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "No such file" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_empty_input_has_a_friendly_error(tmp_path):
    source = tmp_path / "empty.tabular"
    source.touch()
    result = subprocess.run(
        [sys.executable, str(CONVERTERS / "tabular_to_parquet_converter.py"), str(source), str(tmp_path / "output")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Input has no columns" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("name", ["tabular_to_parquet_converter", "parquet_to_tabular_converter"])
def test_cli_missing_pyarrow_has_an_installation_hint(tmp_path, name):
    # Isolated Python without site-packages exercises an unresolved tool requirement.
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(CONVERTERS / f"{name}.py"), str(tmp_path / "input"), str(tmp_path / "output")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "pyarrow is not installed" in result.stderr
    assert "Install the converter's pyarrow requirement" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_malformed_tsv_has_a_friendly_error(tmp_path):
    source = tmp_path / "input.tsv"
    source.write_text('name\n"unterminated\n', encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(CONVERTERS / "tabular_to_parquet_converter.py"),
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


def test_plain_export_of_existing_fixture(tmp_path):
    destination = tmp_path / "output.tabular"
    run_converter("parquet_to_tabular_converter", ROOT / "test-data/parq_to_tabular_conv.parquet", destination)
    assert destination.read_text() == (ROOT / "test-data/parq_to_tabular_conv.tabular").read_text()


def test_plain_export_serializes_nested_values_without_csv_quotes(tmp_path):
    source = tmp_path / "input.parquet"
    destination = tmp_path / "output.tabular"
    parquet.write_table(pa.table({"nested": [["a\tb", "line\nnext"]], "other": ["value"]}), source)
    run_converter("parquet_to_tabular_converter", source, destination)
    records = destination.read_text().splitlines()
    assert len(records) == 2
    fields = records[1].split("\t")
    assert len(fields) == 2
    assert json.loads(fields[0]) == ["a\tb", "line\nnext"]
    assert fields[1] == "value"


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
    to_parquet.convert(tsv, destination, input_format="tsv")
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
        "first" if output_format == "tabular" else "auto",
    )
    actual = parquet.read_table(restored)
    assert actual.num_rows == table.num_rows
    assert actual.schema == table.schema
    assert actual.equals(table)


@pytest.mark.parametrize("output_format", ["tabular", "tsv"])
@pytest.mark.parametrize("header_mode", ["auto", "first"], ids=["headerless", "explicit_commented_header"])
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
    # The final tab-only record is an all-null data row, not a blank line.
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
    # Assert independently specified values before the reverse conversion too:
    # a symmetrical bug in both converters must not make this test pass.
    assert parquet.read_table(binary).equals(expected)
    run_converter("parquet_to_tabular_converter", binary, exported, "--output-format", output_format)
    run_converter(
        "tabular_to_parquet_converter",
        exported,
        restored,
        "--input-format",
        output_format,
        "--header-mode",
        "first" if output_format == "tabular" else "auto",
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
        "first" if output_format == "tabular" else "auto",
    )
    # Text export cannot distinguish null from empty or recover a numeric column's
    # original string type. Assert the documented new inference, not schema recovery.
    expected = pa.table({"numeric_text": [1, 2, None], "empty_text": [None, "filled", None]})
    assert parquet.read_table(restored).equals(expected)


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
    assert to_parquet.read_table(source, input_format="tsv").to_pydict() == {"label": ["#literal"], "value": [1]}


def test_nested_uuid_export(tmp_path):
    value = UUID("12345678-1234-5678-1234-567812345678")
    uuids = pa.ExtensionArray.from_storage(pa.uuid(), pa.array([value.bytes], type=pa.binary(16)))
    nested = pa.StructArray.from_arrays([uuids], names=["id"])
    source = tmp_path / "input.parquet"
    destination = tmp_path / "output.tsv"
    parquet.write_table(pa.table({"nested": nested}), source)
    to_tsv.convert(source, destination, output_format="tsv")
    with destination.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle, dialect="excel-tab"))
    assert json.loads(rows[1][0]) == {"id": str(value)}


def test_nested_temporal_binary_decimal_and_map_export(tmp_path):
    table = pa.table(
        {
            "nested": [
                {
                    "date": date(2026, 9, 16),
                    "timestamp": datetime(2026, 9, 16, 12),
                    "binary": b"\x00\xff",
                    "decimal": Decimal("1.25"),
                },
                None,
            ],
            "dates": [[date(2026, 9, 16)], []],
            "map": pa.array([[("key", b"\xff")], None], type=pa.map_(pa.string(), pa.binary())),
            "binary": [b"\x00\xff", None],
        }
    )
    source = tmp_path / "input.parquet"
    destination = tmp_path / "output.tsv"
    parquet.write_table(table, source)
    to_tsv.convert(source, destination, output_format="tsv")
    with destination.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle, dialect="excel-tab"))
    assert json.loads(rows[1][0]) == {
        "date": "2026-09-16",
        "timestamp": "2026-09-16T12:00:00",
        "binary": {"$binary": "AP8="},
        "decimal": {"$decimal": "1.25"},
    }
    assert json.loads(rows[1][1]) == ["2026-09-16"]
    assert json.loads(rows[1][2]) == [["key", {"$binary": "/w=="}]]
    assert json.loads(rows[1][3]) == {"$binary": "AP8="}
    assert rows[2] == ["", "[]", "", ""]


@pytest.mark.parametrize(
    "text, header_mode",
    [
        ("a\tb\n1\n", "first"),
        ("1\t2\n3\t4\t5\n", "none"),
        ("a\ta\n1\t2\n", "first"),
        ("\ta\n1\t2\n", "first"),
        ("", "auto"),
    ],
)
def test_invalid_input_is_rejected_instead_of_losing_data(tmp_path, text, header_mode):
    source = tmp_path / "input.tabular"
    source.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        to_parquet.read_table(source, header_mode=header_mode)


@pytest.mark.parametrize(
    "extension, parser_format",
    [("tabular", "tabular"), ("bed", "tabular"), ("tsv", "tsv"), ("intermine_tabular", "tsv")],
)
def test_input_subtypes_use_the_correct_parser(extension, parser_format):
    class Input:
        ext = extension

        def __str__(self):
            return "input.dat"

        def is_of_type(self, datatype):
            assert datatype == "tsv"
            return extension in ("tsv", "intermine_tabular")

    tool = ElementTree.parse(CONVERTERS / "tabular_to_parquet_converter.xml")
    command = fill_template(
        tool.find("command").text,
        context={
            "input": Input(),
            "output": "output.parquet",
            "header_mode": "auto",
            "__tool_directory__": str(CONVERTERS),
        },
    )
    assert f"--input-format '{parser_format}'" in command
    assert "--header-mode 'auto'" in command


def test_converter_commands_and_datatype_registration(tmp_path):
    source = tmp_path / "input.tabular"
    binary = tmp_path / "output.parquet"
    tsv = tmp_path / "output.tsv"
    source.write_text("1\tapple\n2\tpear\n", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(CONVERTERS / "tabular_to_parquet_converter.py"),
            str(source),
            str(binary),
            "--input-format",
            "tabular",
            "--header-mode",
            "auto",
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(CONVERTERS / "parquet_to_tabular_converter.py"),
            str(binary),
            str(tsv),
            "--output-format",
            "tsv",
        ],
        check=True,
    )
    assert to_parquet.read_table(tsv, input_format="tsv").equals(parquet.read_table(binary))
    tool = ElementTree.parse(CONVERTERS / "parquet_to_tabular_converter.xml")
    assert tool.getroot().get("id") == "CONVERTER_parquet_to_tabular"
    assert tool.find("outputs/data").get("format") == "tabular"
    tsv_tool = ElementTree.parse(CONVERTERS / "parquet_to_tsv_converter.xml")
    assert tsv_tool.getroot().get("id") == "CONVERTER_parquet_to_tsv"
    assert tsv_tool.find("outputs/data").get("format") == "tsv"
    assert "--output-format tsv" in tsv_tool.find("command").text
    registry = ElementTree.parse(ROOT / "lib/galaxy/config/sample/datatypes_conf.xml.sample")
    assert (
        registry.find(".//datatype[@extension='parquet']/converter[@file='parquet_to_tabular_converter.xml']").get(
            "target_datatype"
        )
        == "tabular"
    )
    assert (
        registry.find(".//datatype[@extension='parquet']/converter[@file='parquet_to_tsv_converter.xml']").get(
            "target_datatype"
        )
        == "tsv"
    )
    assert (
        registry.find(".//datatype[@extension='tsv']/converter[@file='tabular_to_parquet_converter.xml']") is not None
    )


@pytest.mark.parametrize("accepted_format", ["tabular", "tsv", "csv"])
def test_parquet_is_offered_to_tools_accepting_each_output_format(accepted_format):
    config = ElementTree.parse(ROOT / "lib/galaxy/config/sample/datatypes_conf.xml.sample")
    registry = Registry()
    registry.datatypes_by_extension = {"parquet": Parquet(), "tabular": Tabular(), "tsv": TSV(), "csv": CSV()}
    registry.datatype_converters = {
        "parquet": {
            converter.get("target_datatype"): object()
            for converter in config.findall(".//datatype[@extension='parquet']/converter")
        }
    }
    assert registry.find_conversion_destination_for_dataset_by_extensions("parquet", [accepted_format]) == (
        False,
        accepted_format,
        None,
    )
