#!/usr/bin/env python
#Dan Blankenberg
"""
Takes a Multiple Alignment FASTA file and concatenates 
sequences for each species, resulting in one sequence 
alignment per species.
"""

import sys, tempfile
from galaxy import eggs
from galaxy.tools.util.maf_utilities import iter_fasta_alignment
from galaxy.util.odict import odict

def __main__():
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    species = odict()
    cur_size = 0
    for components in iter_fasta_alignment( input_filename ):
        species_not_written = species.keys()
        for component in components:
            if component.species not in species:
                species[component.species] = tempfile.TemporaryFile()
                species[component.species].write( "-" * cur_size )
            species[component.species].write( component.text )
            try:
                species_not_written.remove( component.species )
            except ValueError:
                #this is a new species
                pass
        for spec in species_not_written:
            species[spec].write( "-" * len( components[0].text ) )
        cur_size += len( components[0].text )
    out = open( output_filename, 'wb' )
    for spec, f in species.iteritems():
        f.seek( 0 )
        out.write( ">%s\n%s\n" % ( spec, f.read() ) )
    out.close()

if __name__ == "__main__" : __main__()
