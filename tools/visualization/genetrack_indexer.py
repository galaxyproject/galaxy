#!/usr/bin/env python

"""
Wraps genetrack.scripts.tabs2genetrack so the tool can be executed from Galaxy.

usage: %prog input output shift
"""

import sys, shutil, os
from galaxy import eggs
import pkg_resources
pkg_resources.require( "GeneTrack" )

from genetrack.scripts import tabs2genetrack
from genetrack import logger

if __name__ == "__main__":

    parser = tabs2genetrack.option_parser()

    options, args = parser.parse_args()

    # uppercase the format
    options.format = options.format.upper()

    if options.format not in ('BED', 'GFF'):
        sys.stdout = sys.stderr
        parser.print_help()
        sys.exit(-1)

    logger.disable(options.verbosity)

    # missing file names
    if not (options.inpname and options.outname and options.format):
        parser.print_help()
        sys.exit(-1)
    else:
        tabs2genetrack.transform(inpname=options.inpname, outname=options.outname,\
            format=options.format, shift=options.shift, index=options.index, options=options)

    #HACK ALERT
    #output created in job working directory has a different name than the final destination.
    #GeneTrack uses dataset_name.hdf for indexes
    #This will fix the different name problem, but this is not a secure solution
    #This is Exceptionally Fragile as any change to the way that temporary output names are created could break 
    #GeneTrack should allow explicit definition of the index file, not filename.hdf
    if options.workdir and os.path.isdir( options.workdir ):
        for filename in os.listdir( options.workdir ):
            if filename.endswith( '.dat.hdf' ) and filename.startswith( 'galaxy_dataset_' ):
                shutil.move( os.path.join( options.workdir, filename ), os.path.join( options.workdir, filename[ len( 'galaxy_' ): ] ) )
