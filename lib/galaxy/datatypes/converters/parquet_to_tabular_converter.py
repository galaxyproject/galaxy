#!/usr/bin/env python
"""Export Parquet as plain tabular or quoted TSV, without retaining its schema."""

import argparse
import base64
import csv
import json
import math
import sys
from datetime import (
    date,
    datetime,
    time,
    timedelta,
)
from decimal import Decimal
from uuid import UUID

try:
    import pyarrow as pa
    import pyarrow.parquet as parquet
except ImportError as exc:
    if __name__ == "__main__":
        sys.exit("Cannot run conversion: pyarrow is not installed. Install the converter's pyarrow requirement.")
    raise ImportError(
        "Cannot run conversion: pyarrow is not installed. Install the converter's pyarrow requirement."
    ) from exc


def _json_value(value):
    """Represent Arrow's nested Python values using JSON-compatible values."""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return {"$binary": base64.b64encode(value).decode("ascii")}
    if isinstance(value, Decimal):
        return {"$decimal": str(value)}
    if isinstance(value, float) and not math.isfinite(value):
        return {"$float": str(value)}
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple, dict, bytes)):
        return json.dumps(_json_value(value), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return str(value)


def _plain_record(values, is_header=False):
    if any(any(character in value for character in "\t\r\n") for value in values):
        raise ValueError("Embedded tabs or newlines cannot be represented as plain tabular; use quoted TSV instead")
    if not is_header and (values[0].startswith("#") or (len(values) == 1 and not values[0])):
        raise ValueError("Comment-like or empty records cannot be represented as plain tabular; use quoted TSV instead")
    return "\t".join(values) + "\n"


def _write_tabular(table, outfile, output_format="tabular"):
    if output_format not in ("tabular", "tsv"):
        raise ValueError("Unsupported output format")
    if not table.num_columns:
        raise ValueError("Input has no columns")
    with open(outfile, "w", encoding="utf-8", newline="") as handle:
        # The standard TSV dialect quotes delimiters, quotes, and both CR and LF.
        writer = csv.writer(handle, dialect="excel-tab") if output_format == "tsv" else None
        if writer:
            writer.writerow(table.column_names)
        else:
            handle.write(_plain_record(table.column_names, is_header=True))
        for batch in table.to_batches():
            columns = [column.to_pylist() for column in batch.columns]
            for row in zip(*columns):
                values = [_cell_text(value) for value in row]
                if writer:
                    writer.writerow(values)
                else:
                    handle.write(_plain_record(values))


def convert(infile, outfile, output_format="tabular"):
    _write_tabular(parquet.read_table(infile), outfile, output_format=output_format)


def __main__():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("infile")
    parser.add_argument("outfile")
    parser.add_argument("--output-format", choices=("tabular", "tsv"), default="tabular")
    args = parser.parse_args()
    try:
        convert(args.infile, args.outfile, output_format=args.output_format)
    except FileNotFoundError as exc:
        parser.exit(1, f"Conversion failed: No such file: {exc.filename or args.infile}\n")
    except (OSError, ValueError, pa.ArrowException) as exc:
        parser.exit(1, f"Conversion failed: {exc}\n")


if __name__ == "__main__":
    __main__()
