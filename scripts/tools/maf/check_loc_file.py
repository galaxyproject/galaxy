# Dan Blankenberg
# This script checks maf_index.loc file for inconsistencies between what is listed as available and what is really available.
# Make sure that required dependencies (e.g. galaxy_root/lib) are included in your PYTHONPATH
import bx.align.maf
from galaxy.tools.util import maf_utilities
import sys

assert sys.version_info[:2] >= ( 2, 4 )


def __main__():
    index_location_file = sys.argv[ 1 ]
    for i, line in enumerate( open( index_location_file ) ):
        try:
            if line.startswith( '#' ):
                continue
            display_name, uid, indexed_for_species, species_exist, maf_files = line.rstrip().split('\t')
            indexed_for_species = indexed_for_species.split( ',' )
            species_exist = species_exist.split( ',' )
            maf_files = maf_files.split( ',' )
            species_indexed_in_maf = []
            species_found_in_maf = []
            for maf_file in maf_files:
                indexed_maf = bx.align.maf.MAFIndexedAccess( maf_file, keep_open=True, parse_e_rows=False )
                for key in indexed_maf.indexes.indexes.keys():
                    spec = maf_utilities.src_split( key )[0]
                    if spec not in species_indexed_in_maf:
                        species_indexed_in_maf.append( spec )
                while True:  # reading entire maf set will take some time
                    block = indexed_maf.read_at_current_offset( indexed_maf.f )
                    if block is None:
                        break
                    for comp in block.components:
                        spec = maf_utilities.src_split( comp.src )[0]
                        if spec not in species_found_in_maf:
                            species_found_in_maf.append( spec )
            # indexed species
            for spec in indexed_for_species:
                if spec not in species_indexed_in_maf:
                    print "Line %i, %s claims to be indexed for %s, but indexes do not exist." % ( i, uid, spec )
            for spec in species_indexed_in_maf:
                if spec not in indexed_for_species:
                    print "Line %i, %s is indexed for %s, but is not listed in loc file." % ( i, uid, spec )
            # existing species
            for spec in species_exist:
                if spec not in species_found_in_maf:
                    print "Line %i, %s claims to have blocks for %s, but was not found in MAF files." % ( i, uid, spec )
            for spec in species_found_in_maf:
                if spec not in species_exist:
                    print "Line %i, %s contains %s, but is not listed in loc file." % ( i, uid, spec )
        except Exception as e:
            print "Line %i is invalid: %s" % ( i, e )


if __name__ == "__main__":
    __main__()
