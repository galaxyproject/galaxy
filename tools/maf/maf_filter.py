# Dan Blankenberg
# Filters a MAF file according to the provided code file, which is generated in maf_filter.xml <configfiles>
# Also allows filtering by number of columns in a block, and limiting output species
from __future__ import print_function

import os
import shutil
import sys

import bx.align.maf

from galaxy.tools.util import maf_utilities


def main():
    # Read command line arguments
    try:
        script_file = sys.argv.pop(1)
        maf_file = sys.argv.pop(1)
        out_file = sys.argv.pop(1)
        additional_files_path = sys.argv.pop(1)
        species = maf_utilities.parse_species_option(sys.argv.pop(1))
        min_size = int(sys.argv.pop(1))
        max_size = int(sys.argv.pop(1))
        if max_size < 1:
            max_size = sys.maxsize
        min_species_per_block = int(sys.argv.pop(1))
        exclude_incomplete_blocks = int(sys.argv.pop(1))
        if species:
            num_species = len(species)
        else:
            num_species = len(sys.argv.pop(1).split(","))
    except Exception:
        print(
            "One or more arguments is missing.\nUsage: maf_filter.py maf_filter_file input_maf output_maf path_to_save_debug species_to_keep",
            file=sys.stderr,
        )
        sys.exit()

    # Open input and output MAF files
    try:
        maf_reader = bx.align.maf.Reader(open(maf_file))
        maf_writer = bx.align.maf.Writer(open(out_file, "w"))
    except Exception:
        print("Your MAF file appears to be malformed.", file=sys.stderr)
        sys.exit()

    # Save script file for debuging/verification info later
    os.mkdir(additional_files_path)
    shutil.copy(script_file, os.path.join(additional_files_path, "debug.txt"))

    # Loop through blocks, running filter on each
    # 'maf_block' and 'ret_val' are used/shared in the provided code file
    # 'ret_val' should be set to True if the block is to be kept
    i = 0
    blocks_kept = 0
    for i, maf_block in enumerate(maf_reader):  # noqa: B007
        if min_size <= maf_block.text_size <= max_size:
            local = {"maf_block": maf_block, "ret_val": False}
            exec(compile(open(script_file).read(), script_file, "exec"), {}, local)
            if local["ret_val"]:
                # Species limiting must be done after filters as filters could be run on non-requested output species
                if species:
                    maf_block = maf_block.limit_to_species(species)
                if len(maf_block.components) >= min_species_per_block and (
                    not exclude_incomplete_blocks or len(maf_block.components) >= num_species
                ):
                    maf_writer.write(maf_block)
                    blocks_kept += 1
    maf_writer.close()
    maf_reader.close()
    if i == 0:
        print("Your file contains no valid maf_blocks.")
    else:
        print("Kept %s of %s blocks (%.2f%%)." % (blocks_kept, i + 1, float(blocks_kept) / float(i + 1) * 100.0))


if __name__ == "__main__":
    main()
