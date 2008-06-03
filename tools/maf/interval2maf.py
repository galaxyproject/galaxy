#!/usr/bin/env python

"""
Reads a list of intervals and a maf. Produces a new maf containing the
blocks or parts of blocks in the original that overlapped the intervals.

If a MAF file, not UID, is provided the MAF file is indexed before being processed.

NOTE: If two intervals overlap the same block it will be written twice.

usage: %prog maf_file [options]
   -d, --dbkey=d: Database key, ie hg17
   -c, --chromCol=c: Column of Chr
   -s, --startCol=s: Column of Start
   -e, --endCol=e: Column of End
   -S, --strandCol=S: Column of Strand
   -t, --mafType=t: Type of MAF source to use
   -m, --mafFile=m: Path of source MAF file, if not using cached version
   -i, --interval_file=i:       Input interval file
   -o, --output_file=o:      Output MAF file
   -p, --species=p: Species to include in output
   -l, --indexLocation=l: Override default maf_index.loc file
   -y, --mafIndexFile=y: Directory of local maf index file ( maf_index.loc or maf_pairwise.loc )
   -z, --mafTmpFileDir=z: Directory to be used when creating temporary files
"""

#Dan Blankenberg
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse
import bx.align.maf
import bx.intervals.io
from galaxy.tools.util import maf_utilities
import sys

assert sys.version_info[:2] >= ( 2, 4 )

def __main__():
    index = index_filename = None
    mincols = 0
    
    #Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    
    if options.dbkey: dbkey = options.dbkey
    else: dbkey = None
    if dbkey in [None, "?"]:
        print >>sys.stderr, "You must specify a proper build in order to extract alignments. You can specify your genome build by clicking on the pencil icon associated with your interval file."
        sys.exit()
    
    species = None
    if options.species:
        species = options.species.split( ',' )
        if "None" in species: species = None
    
    if options.chromCol: chromCol = int( options.chromCol ) - 1
    else: 
        print >>sys.stderr, "Chromosome column has not been specified."
        sys.exit()
    
    if options.startCol: startCol = int( options.startCol ) - 1
    else: 
        print >>sys.stderr, "Start column has not been specified."
        sys.exit()
    
    if options.endCol: endCol = int( options.endCol ) - 1
    else: 
        print >>sys.stderr, "End column has not been specified."
        sys.exit()
    
    if options.strandCol: strandCol = int( options.strandCol ) - 1
    else: 
        print >>sys.stderr, "Strand column has not been specified."
        sys.exit()
    
    if options.interval_file: interval_file = options.interval_file
    else: 
        print >>sys.stderr, "Input interval file has not been specified."
        sys.exit()
    
    if options.output_file: output_file = options.output_file
    else: 
        print >>sys.stderr, "Output file has not been specified."
        sys.exit()
    #Finish parsing command line
    
    #Open indexed access to MAFs
    if options.mafType:
        if options.indexLocation:
            index = maf_utilities.maf_index_by_uid( options.mafType, options.indexLocation )
        else:
            index = maf_utilities.maf_index_by_uid( options.mafType, options.mafIndexFile )
        if index is None:
            print >> sys.stderr, "The MAF source specified (%s) appears to be invalid." % ( options.mafType )
            sys.exit()
    elif options.mafFile:
        index, index_filename = maf_utilities.build_maf_index( options.mafFile, species=[dbkey], directory=options.mafTmpFileDir )
        if index is None:
            print >> sys.stderr, "Your MAF file appears to be malformed."
            sys.exit()
    else:
        print >>sys.stderr, "Desired source MAF type has not been specified."
        sys.exit()
    
    #Create MAF writter
    out = bx.align.maf.Writer( open(output_file, "w") )
    
    #Iterate over input regions 
    num_blocks = 0
    num_regions = None
    for num_regions, region in enumerate( bx.intervals.io.NiceReaderWrapper( open( interval_file, 'r' ), chrom_col = chromCol, start_col = startCol, end_col = endCol, strand_col = strandCol, fix_strand = True, return_header = False, return_comments = False ) ):
        src = "%s.%s" % ( dbkey, region.chrom )
        for block in maf_utilities.get_chopped_blocks_for_region( index, src, region, species, mincols ):
            out.write( block )
            num_blocks += 1
    
    #Close output MAF
    out.close()
    
    #remove index file if created during run
    maf_utilities.remove_temp_index_file( index_filename )
    
    if num_blocks:
        print "%i MAF blocks extracted for %i regions." % ( num_blocks, ( num_regions + 1 ) )
    elif num_regions is not None:
        print "No MAF blocks could be extracted for %i regions." % ( num_regions + 1 )
    else:
        print "No valid regions have been provided."
    
if __name__ == "__main__": __main__()
