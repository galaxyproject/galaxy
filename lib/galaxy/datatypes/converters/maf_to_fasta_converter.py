#!/usr/bin/env python
# Dan Blankenberg

import sys

import bx.align.maf

from galaxy.datatypes.util import maf_utilities


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
                    "{}\n".format(
                        maf_utilities.get_fasta_header(
                            c,
                            {"block_index": count, "species": spec, "sequence_index": spec_counts[spec]},
                            suffix=f"{spec}_{count}_{spec_counts[spec]}",
                        )
                    )
                )
                out.write(f"{c.text}\n")
            out.write("\n")
    print(f"{count} MAF blocks converted to FASTA.")


if __name__ == "__main__":
    __main__()
