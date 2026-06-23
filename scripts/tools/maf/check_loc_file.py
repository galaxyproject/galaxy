# Dan Blankenberg
# This script checks maf_index.loc file for inconsistencies between what is listed as available and what is really available.
# Make sure that required dependencies (e.g. galaxy_root/lib) are included in your PYTHONPATH

import sys

import bx.align.maf

from galaxy.tools.util import maf_utilities

assert sys.version_info[:2] >= (2, 6)


def __main__():
    index_location_file = sys.argv[1]
    for i, line in enumerate(open(index_location_file)):
        try:
            if line.startswith("#"):
                continue
            display_name, uid, indexed_for_species, species_exist, maf_files = line.rstrip().split("\t")
            indexed_for_species = indexed_for_species.split(",")
            species_exist = species_exist.split(",")
            maf_files = maf_files.split(",")
            species_indexed_in_maf = []
            species_found_in_maf = []
            for maf_file in maf_files:
                indexed_maf = bx.align.maf.MAFIndexedAccess(maf_file, keep_open=True, parse_e_rows=False)
                for key in indexed_maf.indexes.indexes.keys():
                    spec = maf_utilities.src_split(key)[0]
                    if spec not in species_indexed_in_maf:
                        species_indexed_in_maf.append(spec)
                while True:  # reading entire maf set will take some time
                    block = indexed_maf.read_at_current_offset(indexed_maf.f)
                    if block is None:
                        break
                    for comp in block.components:
                        spec = maf_utilities.src_split(comp.src)[0]
                        if spec not in species_found_in_maf:
                            species_found_in_maf.append(spec)
            # indexed species
            for spec in indexed_for_species:
                if spec not in species_indexed_in_maf:
                    print(f"Line {i}, {uid} claims to be indexed for {spec}, but indexes do not exist.")
            for spec in species_indexed_in_maf:
                if spec not in indexed_for_species:
                    print(f"Line {i}, {uid} is indexed for {spec}, but is not listed in loc file.")
            # existing species
            for spec in species_exist:
                if spec not in species_found_in_maf:
                    print(f"Line {i}, {uid} claims to have blocks for {spec}, but was not found in MAF files.")
            for spec in species_found_in_maf:
                if spec not in species_exist:
                    print(f"Line {i}, {uid} contains {spec}, but is not listed in loc file.")
        except Exception as e:
            print(f"Line {i} is invalid: {e}")


if __name__ == "__main__":
    __main__()
