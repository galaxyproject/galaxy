#!/usr/bin/env python
"""
Converts Parquet files to tabular format.
All columns are converted to strings, with nested structures (lists/dicts) serialized as JSON.
"""

import json
import os
import sys

try:
    import pyarrow as pa
    import pyarrow.parquet
except ImportError:
    pyarrow = None
    pa = None


def _stringify_all_columns(table):
    """
    Convert all columns in a PyArrow table to string type.

    - Null values become empty strings
    - Nested types (lists, structs, maps) and Python list/dict values are serialized as JSON
    - Scalar values (integers, floats, booleans, strings) are converted using str()

    Args:
        table: A PyArrow Table object

    Returns:
        A new PyArrow Table with all columns converted to string type
    """
    new_columns = []
    for column in table.columns:
        values = column.to_pylist()
        stringified_values = []
        for value in values:
            if value is None:
                stringified_values.append("")
            elif isinstance(value, (list, dict)):
                json_str = json.dumps(value, separators=(",", ":"))
                stringified_values.append(json_str)
            else:
                stringified_values.append(str(value))
        new_columns.append(pa.array(stringified_values, type=pa.string()))
    return pa.Table.from_arrays(new_columns, names=table.schema.names)


def _write_tabular(table, outfile):
    """
    Write a PyArrow table as tabular file.

    Values are written as-is, except for JSON structures (lists/dicts starting
    with '{' or '[') which are wrapped in double quotes to protect internal
    delimiters from being interpreted as field separators.

    Args:
        table: A PyArrow Table with all columns as string type
        outfile: Path to the output tabular file
    """
    column_names = table.schema.names

    with open(outfile, "w", newline="") as f:
        f.write("\t".join(column_names) + "\n")

        for row_idx in range(table.num_rows):
            row_values = []
            for col_idx in range(table.num_columns):
                val = table.column(col_idx)[row_idx].as_py()
                if val and val[0] in "{[":
                    val = '"' + val + '"'
                row_values.append(val)
            f.write("\t".join(row_values) + "\n")


def __main__():
    infile = sys.argv[1]
    outfile = sys.argv[2]

    if not os.path.isfile(infile):
        sys.stderr.write(f"Input file {infile!r} not found\n")
        sys.exit(1)

    if pyarrow is None:
        raise ImportError("Cannot run conversion, pyarrow is not installed.")

    table = pyarrow.parquet.read_table(infile)
    table = _stringify_all_columns(table)
    _write_tabular(table, outfile)


if __name__ == "__main__":
    __main__()
