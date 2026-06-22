#!/usr/bin/env python
"""
Converts tabular files to Parquet format.
Parse tabular files with a header row and convert to Parquet format using PyArrow.
"""

import os
import sys

try:
    import pyarrow as pa
    import pyarrow.parquet
except ImportError:
    pa = None  # type: ignore[assignment]
    pyarrow = None  # type: ignore[assignment]


def __main__():
    infile = sys.argv[1]
    outfile = sys.argv[2]

    if not os.path.isfile(infile):
        sys.stderr.write(f"Input file {infile!r} not found\n")
        sys.exit(1)
    if pyarrow is None:
        raise ImportError("Cannot run conversion, pyarrow is not installed.")

    with open(infile, encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        sys.stderr.write(f"Input file {infile!r} is empty\n")
        sys.exit(1)

    header = lines[0].rstrip("\r\n").split("\t")

    rows = []
    for line in lines[1:]:
        line = line.rstrip("\r\n")
        if line:
            row = line.split("\t")
            rows.append(row)

    column_data: dict[str, list] = {col: [] for col in header}
    for row in rows:
        for i, col in enumerate(header):
            value = row[i] if i < len(row) else ""
            if value == "" or value.lower() == "na":
                column_data[col].append(None)
            else:
                if "." in value or "e" in value.lower():
                    try:
                        column_data[col].append(float(value))
                    except ValueError:
                        column_data[col].append(value)
                else:
                    try:
                        column_data[col].append(int(value))
                    except ValueError:
                        column_data[col].append(value)

    arrays = {}
    for col in header:
        values = column_data[col]
        non_null_values = [v for v in values if v is not None]
        if not non_null_values:
            arrays[col] = pa.array(values, type=pa.string())
        elif all(isinstance(v, int) for v in non_null_values):
            arrays[col] = pa.array(values, type=pa.int64())
        elif all(isinstance(v, (int, float)) for v in non_null_values):
            arrays[col] = pa.array(values, type=pa.float64())
        else:
            arrays[col] = pa.array(values, type=pa.string())

    table = pa.Table.from_arrays(list(arrays.values()), names=list(arrays.keys()))
    pyarrow.parquet.write_table(table, outfile)


if __name__ == "__main__":
    __main__()
