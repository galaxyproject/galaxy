#!/usr/bin/env python

import sys


def __main__():
    input_name = sys.argv[1]
    output_name = sys.argv[2]
    skipped_lines = 0
    first_skipped_line = 0
    i = 0
    with open(input_name) as fh, open(output_name, "w") as out:
        for i, line in enumerate(fh):
            line = line.rstrip("\r\n")
            if line and not line.startswith("#"):
                try:
                    elems = line.split("\t")
                    start = str(int(elems[3]) - 1)
                    strand = elems[6]
                    if strand not in ["+", "-"]:
                        strand = "+"
                    # GFF format: chrom source, name, chromStart, chromEnd, score, strand
                    # Bed format: chrom, chromStart, chromEnd, name, score, strand
                    #
                    # Replace any spaces in the name with underscores so UCSC will not complain
                    name = elems[2].replace(" ", "_")
                    out.write(f"{elems[0]}\t{start}\t{elems[4]}\t{name}\t0\t{strand}\n")
                except Exception:
                    skipped_lines += 1
                    if not first_skipped_line:
                        first_skipped_line = i + 1
            else:
                skipped_lines += 1
                if not first_skipped_line:
                    first_skipped_line = i + 1
    info_msg = f"{i + 1 - skipped_lines} lines converted to BED.  "
    if skipped_lines > 0:
        info_msg += f"Skipped {skipped_lines} blank/comment/invalid lines starting with line #{first_skipped_line}."
    print(info_msg)


if __name__ == "__main__":
    __main__()
