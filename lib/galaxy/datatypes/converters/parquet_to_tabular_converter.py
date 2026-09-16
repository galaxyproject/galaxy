#!/usr/bin/env python
"""Export Parquet as quoted TSV: a text projection, not a schema-preserving format."""

import argparse
import base64
import csv
import json
import math
from datetime import (
    date,
    datetime,
    time,
    timedelta,
)
from decimal import Decimal
from uuid import UUID

import pyarrow.parquet as parquet


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


def _write_tabular(table, outfile):
    with open(outfile, "w", encoding="utf-8", newline="") as handle:
        # The standard TSV dialect quotes delimiters, quotes, and both CR and LF.
        writer = csv.writer(handle, dialect="excel-tab")
        writer.writerow(table.column_names)
        for batch in table.to_batches():
            columns = [column.to_pylist() for column in batch.columns]
            writer.writerows([_cell_text(value) for value in row] for row in zip(*columns))


def convert(infile, outfile):
    _write_tabular(parquet.read_table(infile), outfile)


def __main__():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("infile")
    parser.add_argument("outfile")
    args = parser.parse_args()
    convert(args.infile, args.outfile)


if __name__ == "__main__":
    __main__()
