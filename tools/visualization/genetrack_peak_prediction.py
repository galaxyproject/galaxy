#!/usr/bin/env python

"""
Wraps genetrack.scripts.peakpred so the tool can be executed from Galaxy.

usage: %prog input output level sigma mode exclusion strand
"""

import sys
from galaxy import eggs
import pkg_resources
pkg_resources.require( "GeneTrack" )

from genetrack.scripts import peakpred
from genetrack import logger

if __name__ == "__main__":

    parser = peakpred.option_parser()

    options, args = parser.parse_args()

    logger.disable(options.verbosity)

    from genetrack import conf

    # trigger test mode
    if options.test:
        options.inpname = conf.testdata('test-hdflib-input.gtrack')
        options.outname = conf.testdata('predictions.bed')

    # missing input file name
    if not options.inpname and not options.outname:
        parser.print_help()
    else:
        print 'Sigma = %s' % options.sigma
        print 'Minimum peak = %s' % options.level
        print 'Peak-to-peak = %s' % options.exclude

        peakpred.predict(options.inpname, options.outname, options)
