#!/usr/bin/env python
"""
Input: parquet
Output: tabular
"""

import json
import os
import sys

try:
    import pyarrow as pa
    import pyarrow.csv
    import pyarrow.parquet
except ImportError:
    pyarrow = None
    pa = None


def _stringify_nested_columns(table):
    new_columns = []
    for column in table.columns:
        if pa.types.is_nested(column.type):
            values = column.to_pylist()
            values = [json.dumps(value, ensure_ascii=True) if value is not None else None for value in values]
            new_columns.append(pa.array(values, type=pa.string()))
        else:
            new_columns.append(column)
    return pa.Table.from_arrays(new_columns, names=table.schema.names)


def __main__():
    infile = sys.argv[1]
    outfile = sys.argv[2]

    if not os.path.isfile(infile):
        sys.stderr.write(f"Input file {infile!r} not found\n")
        sys.exit(1)

    if pyarrow is None:
        raise Exception("Cannot run conversion, pyarrow is not installed.")
    table = pyarrow.parquet.read_table(infile)
    table = _stringify_nested_columns(table)
    pyarrow.csv.write_csv(table, outfile, write_options=pyarrow.csv.WriteOptions(delimiter="\t"))


if __name__ == "__main__":
    __main__()
