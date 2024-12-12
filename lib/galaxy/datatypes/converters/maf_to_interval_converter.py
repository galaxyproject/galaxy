#!/usr/bin/env python
# Dan Blankenberg

import sys

import bx.align.maf

from galaxy.datatypes.util import maf_utilities


def __main__():
    output_name = sys.argv.pop(1)
    input_name = sys.argv.pop(1)
    species = sys.argv.pop(1)
    count = 0
    with open(output_name, "w") as out:
        # write interval header line
        out.write("#chrom\tstart\tend\tstrand\n")
        try:
            with open(input_name) as fh:
                for block in bx.align.maf.Reader(fh):
                    for c in maf_utilities.iter_components_by_src_start(block, species):
                        if c is not None:
                            out.write(
                                f"{maf_utilities.src_split(c.src)[-1]}\t{c.get_forward_strand_start()}\t{c.get_forward_strand_end()}\t{c.strand}\n"
                            )
                            count += 1
        except Exception as e:
            print(f"There was a problem processing your input: {e}", file=sys.stderr)
    print(f"{count} MAF blocks converted to Genomic Intervals for species {species}.")


if __name__ == "__main__":
    __main__()
