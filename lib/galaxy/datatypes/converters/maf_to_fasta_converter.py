#!/usr/bin/env python
# Dan Blankenberg

import sys

import bx.align.maf

from galaxy.datatypes.util import maf_utilities

assert sys.version_info[:2] >= (2, 6)


def __main__():
    output_name = sys.argv.pop(1)
    input_name = sys.argv.pop(1)
    count = 0
    with open(output_name, "w") as out, open(input_name) as infile:
        for count, block in enumerate(bx.align.maf.Reader(infile)):
            spec_counts = {}
            for c in block.components:
                spec, chrom = maf_utilities.src_split(c.src)
                if spec not in spec_counts:
                    spec_counts[spec] = 0
                else:
                    spec_counts[spec] += 1
                out.write(
                    "%s\n"
                    % maf_utilities.get_fasta_header(
                        c,
                        {"block_index": count, "species": spec, "sequence_index": spec_counts[spec]},
                        suffix="%s_%i_%i" % (spec, count, spec_counts[spec]),
                    )
                )
                out.write(f"{c.text}\n")
            out.write("\n")
    print("%i MAF blocks converted to FASTA." % (count))


if __name__ == "__main__":
    __main__()
