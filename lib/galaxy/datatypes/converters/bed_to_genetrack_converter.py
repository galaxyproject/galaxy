#!/usr/bin/env python

#FIXME: THIS IS 1:1 COPY OF THE SAME FUNCTIONED TOOL - ALLOW REGULAR TOOLS TO MASCARADE AS CONVERTERS

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
    import os
    os.environ[ 'LC_ALL' ] = 'C' 
    #os.system( 'export' )
    
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
