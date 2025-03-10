#!/usr/bin/env python
# Dan Blankenberg

import sys

import bx.intervals.io


def __main__():
    output_name = sys.argv[1]
    input_name = sys.argv[2]
    try:
        chromCol = int(sys.argv[3]) - 1
    except Exception:
        sys.exit(
            f"'{str(sys.argv[3])}' is an invalid chrom column, correct the column settings before attempting to convert the data format."
        )
    try:
        startCol = int(sys.argv[4]) - 1
    except Exception:
        sys.exit(
            f"'{str(sys.argv[4])}' is an invalid start column, correct the column settings before attempting to convert the data format."
        )
    try:
        endCol = int(sys.argv[5]) - 1
    except Exception:
        sys.exit(
            f"'{str(sys.argv[5])}' is an invalid end column, correct the column settings before attempting to convert the data format."
        )
    try:
        strandCol = int(sys.argv[6]) - 1
    except Exception:
        strandCol = -1
    try:
        nameCol = int(sys.argv[7]) - 1
    except Exception:
        nameCol = -1
    skipped_lines = 0
    first_skipped_line = 0
    count = 0
    with open(input_name) as fh, open(output_name, "w") as out:
        for count, region in enumerate(
            bx.intervals.io.NiceReaderWrapper(
                fh,
                chrom_col=chromCol,
                start_col=startCol,
                end_col=endCol,
                strand_col=strandCol,
                fix_strand=True,
                return_header=False,
                return_comments=False,
            )
        ):
            try:
                if nameCol >= 0:
                    name = region.fields[nameCol]
                else:
                    raise IndexError
            except Exception:
                name = f"region_{count}"
            try:
                out.write(f"{region.chrom}\t{region.start}\t{region.end}\t{name}\t0\t{region.strand}\n")
            except Exception:
                skipped_lines += 1
                if not first_skipped_line:
                    first_skipped_line = count + 1
    print(f"{count + 1 - skipped_lines} regions converted to BED.")
    if skipped_lines > 0:
        print(f"Skipped {skipped_lines} blank or invalid lines starting with line # {first_skipped_line}.")


if __name__ == "__main__":
    __main__()
