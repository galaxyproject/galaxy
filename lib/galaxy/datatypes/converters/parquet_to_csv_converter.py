#!/usr/bin/env python
"""Export Parquet as CSV."""

import argparse
import sys

try:
    import pyarrow as pa
    import pyarrow.csv as csv
    import pyarrow.parquet as parquet
except ImportError as exc:
    if __name__ == "__main__":
        sys.exit("Cannot run conversion: pyarrow is not installed. Install the converter's pyarrow requirement.")
    raise ImportError(
        "Cannot run conversion: pyarrow is not installed. Install the converter's pyarrow requirement."
    ) from exc


def convert(infile, outfile):
    # pyarrow re-exports write_csv at runtime but its stubs do not declare it.
    csv.write_csv(parquet.read_table(infile), outfile)  # type: ignore[attr-defined]


def __main__():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("infile")
    parser.add_argument("outfile")
    args = parser.parse_args()
    try:
        convert(args.infile, args.outfile)
    except FileNotFoundError as exc:
        parser.exit(1, f"Conversion failed: No such file: {exc.filename or args.infile}\n")
    except (OSError, ValueError, pa.ArrowException) as exc:
        parser.exit(1, f"Conversion failed: {exc}\n")


if __name__ == "__main__":
    __main__()
