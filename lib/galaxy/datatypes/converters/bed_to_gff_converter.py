#!/usr/bin/env python
# This code exists in 2 places: ~/datatypes/converters and ~/tools/filters

import sys


def __main__():
    input_name = sys.argv[1]
    output_name = sys.argv[2]
    skipped_lines = 0
    first_skipped_line = 0
    i = 0
    with open(input_name) as fh, open(output_name, "w") as out:
        out.write("##gff-version 2\n")
        out.write("##bed_to_gff_converter.py\n\n")
        for i, line in enumerate(fh):
            complete_bed = False
            line = line.rstrip("\r\n")
            if line and not line.startswith("#") and not line.startswith("track") and not line.startswith("browser"):
                try:
                    elems = line.split("\t")
                    if len(elems) == 12:
                        complete_bed = True
                    chrom = elems[0]
                    if complete_bed:
                        feature = "mRNA"
                    else:
                        try:
                            feature = elems[3]
                        except Exception:
                            feature = f"feature{i + 1}"
                    start = int(elems[1]) + 1
                    end = int(elems[2])
                    try:
                        score = elems[4]
                    except Exception:
                        score = "0"
                    try:
                        strand = elems[5]
                    except Exception:
                        strand = "+"
                    try:
                        group = elems[3]
                    except Exception:
                        group = f"group{i + 1}"
                    if complete_bed:
                        out.write(
                            f"{chrom}\tbed2gff\t{feature}\t{start}\t{end}\t{score}\t{strand}\t.\t{feature} {group};\n"
                        )
                    else:
                        out.write(f"{chrom}\tbed2gff\t{feature}\t{start}\t{end}\t{score}\t{strand}\t.\t{group};\n")
                    if complete_bed:
                        # We have all the info necessary to annotate exons for genes and mRNAs
                        block_count = int(elems[9])
                        block_sizes = elems[10].split(",")
                        block_starts = elems[11].split(",")
                        for j in range(block_count):
                            exon_start = int(start) + int(block_starts[j])
                            exon_end = exon_start + int(block_sizes[j]) - 1
                            out.write(
                                f"{chrom}\tbed2gff\texon\t{exon_start}\t{exon_end}\t{score}\t{strand}\t.\texon {group};\n"
                            )
                except Exception:
                    skipped_lines += 1
                    if not first_skipped_line:
                        first_skipped_line = i + 1
            else:
                skipped_lines += 1
                if not first_skipped_line:
                    first_skipped_line = i + 1
    info_msg = f"{i + 1 - skipped_lines} lines converted to GFF version 2.  "
    if skipped_lines > 0:
        info_msg += f"Skipped {skipped_lines} blank/comment/invalid lines starting with line #{first_skipped_line}."
    print(info_msg)


if __name__ == "__main__":
    __main__()
