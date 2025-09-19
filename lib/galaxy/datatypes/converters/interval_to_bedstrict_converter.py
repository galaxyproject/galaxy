#!/usr/bin/env python
# Dan Blankenberg

import sys

import bx.intervals.io


def force_bed_field_count(fields, region_count: int, force_num_columns: int):
    if force_num_columns >= 4 and len(fields) < 4:
        fields.append(f"region_{region_count}")
    if force_num_columns >= 5 and len(fields) < 5:
        fields.append("0")
    if force_num_columns >= 6 and len(fields) < 6:
        fields.append("+")
    if force_num_columns >= 7 and len(fields) < 7:
        fields.append(fields[1])
    if force_num_columns >= 8 and len(fields) < 8:
        fields.append(fields[2])
    if force_num_columns >= 9 and len(fields) < 9:
        fields.append("0")
    if force_num_columns >= 10 and len(fields) < 10:
        fields.append("0")
    if force_num_columns >= 11 and len(fields) < 11:
        fields.append(",")
    if force_num_columns >= 12 and len(fields) < 12:
        fields.append(",")
    return fields[:force_num_columns]


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
    try:
        extension = sys.argv[8]
    except IndexError:
        extension = "interval"  # default extension
    try:
        force_num_columns = int(sys.argv[9])
    except Exception:
        force_num_columns = None

    skipped_lines = 0
    first_skipped_line = None
    count = 0
    # does file already conform to bed strict?
    # if so, we want to keep extended columns, otherwise we'll create a generic 6 column bed file
    strict_bed = True
    if (
        extension in ["bed", "bedstrict", "bed6", "bed12"]
        and (chromCol, startCol, endCol) == (0, 1, 2)
        and (nameCol < 0 or nameCol == 3)
        and (strandCol < 0 or strandCol == 5)
    ):
        with open(input_name) as fh, open(output_name, "w") as out:
            for count, line in enumerate(fh):
                line = line.rstrip("\n\r")
                if line == "" or line.startswith("#"):
                    skipped_lines += 1
                    if first_skipped_line is None:
                        first_skipped_line = count + 1
                    continue
                fields = line.split("\t")
                try:
                    assert len(fields) >= 3, "A BED file requires at least 3 columns"  # we can't fix this
                    if len(fields) > 12:
                        strict_bed = False
                        break
                    # name (fields[3]) can be anything, no verification needed
                    if len(fields) > 4:
                        float(
                            fields[4]
                        )  # score - A score between 0 and 1000. If the track line useScore attribute is set to 1 for this annotation data set, the score value will determine the level of gray in which this feature is displayed (higher numbers = darker gray).
                        if len(fields) > 5:
                            assert fields[5] in [
                                "+",
                                "-",
                            ], "Invalid strand"  # strand - Defines the strand - either '+' or '-'.
                            if len(fields) > 6:
                                int(
                                    fields[6]
                                )  # thickStart - The starting position at which the feature is drawn thickly (for example, the start codon in gene displays).
                                if len(fields) > 7:
                                    int(
                                        fields[7]
                                    )  # thickEnd - The ending position at which the feature is drawn thickly (for example, the stop codon in gene displays).
                                    if len(fields) > 8:
                                        if (
                                            fields[8] != "0"
                                        ):  # itemRgb - An RGB value of the form R,G,B (e.g. 255,0,0). If the track line itemRgb attribute is set to "On", this RBG value will determine the display color of the data contained in this BED line. NOTE: It is recommended that a simple color scheme (eight colors or less) be used with this attribute to avoid overwhelming the color resources of the Genome Browser and your Internet browser.
                                            fields2 = fields[8].split(",")
                                            assert len(fields2) == 3, "RGB value must be 0 or have length of 3"
                                            for field in fields2:
                                                int(field)  # rgb values are integers
                                        if len(fields) > 9:
                                            int(fields[9])  # blockCount - The number of blocks (exons) in the BED line.
                                            if len(fields) > 10:
                                                if (
                                                    fields[10] != ","
                                                ):  # blockSizes - A comma-separated list of the block sizes. The number of items in this list should correspond to blockCount.
                                                    fields2 = (
                                                        fields[10].rstrip(",").split(",")
                                                    )  # remove trailing comma and split on comma
                                                    for field in fields2:
                                                        int(field)
                                                if len(fields) > 11:
                                                    if (
                                                        fields[11] != ","
                                                    ):  # blockStarts - A comma-separated list of block starts. All of the blockStart positions should be calculated relative to chromStart. The number of items in this list should correspond to blockCount.
                                                        fields2 = (
                                                            fields[11].rstrip(",").split(",")
                                                        )  # remove trailing comma and split on comma
                                                        for field in fields2:
                                                            int(field)
                except Exception:
                    strict_bed = False
                    break
                if force_num_columns is not None and len(fields) != force_num_columns:
                    line = "\t".join(force_bed_field_count(fields, count, force_num_columns))
                out.write(f"{line}\n")
    else:
        strict_bed = False

    if not strict_bed:
        skipped_lines = 0
        first_skipped_line = None
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
                    fields = [str(item) for item in (region.chrom, region.start, region.end, name, 0, region.strand)]
                    if force_num_columns is not None and len(fields) != force_num_columns:
                        fields = force_bed_field_count(fields, count, force_num_columns)
                    out.write("{}\n".format("\t".join(fields)))
                except Exception:
                    skipped_lines += 1
                    if first_skipped_line is None:
                        first_skipped_line = count + 1
    print(f"{count + 1 - skipped_lines} regions converted to BED.")
    if skipped_lines > 0:
        print(f"Skipped {skipped_lines} blank or invalid lines starting with line # {first_skipped_line}.")


if __name__ == "__main__":
    __main__()
