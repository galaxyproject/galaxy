import csv
import json
import subprocess
import sys
from datetime import (
    date,
    datetime,
)
from decimal import Decimal
from uuid import UUID

import pytest

pytest.importorskip("pyarrow")

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as parquet  # noqa: E402

from .test_parquet_converter_utils import (  # noqa: E402
    converter_script,
    run_converter,
    to_tsv,
)


@pytest.mark.parametrize("value", ["a\tb", "a\nb", "a\rb", "#comment", ""])
def test_plain_export_rejects_unrepresentable_records(tmp_path, value):
    source = tmp_path / "input.parquet"
    destination = tmp_path / "output.tabular"
    parquet.write_table(pa.table({"text": [value]}), source)
    result = subprocess.run(
        [sys.executable, str(converter_script("parquet_to_tabular_converter")), str(source), str(destination)],
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


def test_parquet_to_tabular_cli_missing_input_has_a_friendly_error(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(converter_script("parquet_to_tabular_converter")),
            str(tmp_path / "missing"),
            str(tmp_path / "output"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "No such file" in result.stderr
    assert "Traceback" not in result.stderr


def test_parquet_to_tabular_cli_missing_pyarrow_has_an_installation_hint(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(converter_script("parquet_to_tabular_converter")),
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
