#!/usr/bin/env python
"""Convert plain tabular or quoted TSV to Parquet with explicit header handling."""

import argparse
import csv
import math
import re
import sys
from decimal import (
    Decimal,
    InvalidOperation,
)

import pyarrow as pa
import pyarrow.parquet as parquet

INTEGER = re.compile(r"[+-]?(?:0|[1-9][0-9]*)\Z")
NUMBER = re.compile(r"[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")


def _column_array(lexemes):
    """Infer a whole column before coercion; mixed columns retain their text."""
    values = [value if value != "" else None for value in lexemes]
    non_null = [value for value in values if value is not None]
    if non_null and all(INTEGER.fullmatch(value) for value in non_null):
        integers = [Decimal(value) for value in non_null]
        if all(-(2**63) <= value < 2**63 for value in integers):
            return pa.array([int(value) if value is not None else None for value in values], type=pa.int64())
    elif non_null and all(NUMBER.fullmatch(value) for value in non_null):
        floats = [float(value) for value in non_null]
        # Include exponent notation in the precision guard and reject underflow.
        if all(_safe_float(value, number) for value, number in zip(non_null, floats)):
            return pa.array([float(value) if value is not None else None for value in values], type=pa.float64())
    return pa.array(values, type=pa.string())


def _safe_float(text, number):
    if not math.isfinite(number):
        return False
    try:
        exact = Decimal(text)
    except InvalidOperation:
        return False
    if number == 0 and exact != 0:
        return False
    return exact != exact.to_integral_value() or exact.copy_abs() <= 2**53


def read_table(infile, input_format="tabular", header_mode="auto"):
    if input_format not in ("tabular", "tsv") or header_mode not in ("auto", "first", "none"):
        raise ValueError("Unsupported input format or header mode")
    has_header = header_mode == "first" or (header_mode == "auto" and input_format == "tsv")
    with open(infile, encoding="utf-8", newline="") as handle:
        if input_format == "tsv":
            csv.field_size_limit(sys.maxsize)
            rows = list(csv.reader(handle, dialect="excel-tab", strict=True))
        else:
            # Galaxy's generic tabular datatype does not interpret CSV quoting.
            rows = [
                line.rstrip("\r\n").split("\t") for line in handle if not line.startswith("#") and line.rstrip("\r\n")
            ]
    if not rows or not rows[0]:
        raise ValueError("Input has no columns")
    width = len(rows[0])
    names = rows.pop(0) if has_header else [f"column{i + 1}" for i in range(width)]
    if any(not name for name in names) or len(set(names)) != width:
        raise ValueError("Column names must be nonempty and unique")
    for index, row in enumerate(rows, start=2 if has_header else 1):
        if len(row) != width:
            raise ValueError(f"Row {index} has {len(row)} columns; expected {width}")
    arrays = [_column_array([row[index] for row in rows]) for index in range(width)]
    return pa.Table.from_arrays(arrays, names=names)


def convert(infile, outfile, input_format="tabular", header_mode="auto"):
    parquet.write_table(read_table(infile, input_format=input_format, header_mode=header_mode), outfile)


def __main__():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("infile")
    parser.add_argument("outfile")
    parser.add_argument("--input-format", choices=("tabular", "tsv"), default="tabular")
    parser.add_argument("--header-mode", choices=("auto", "first", "none"), default="auto")
    args = parser.parse_args()
    convert(args.infile, args.outfile, input_format=args.input_format, header_mode=args.header_mode)


if __name__ == "__main__":
    __main__()
