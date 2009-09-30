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
   -I, --mafIndex=I: Path of precomputed source MAF file index, if not using cached version
   -i, --interval_file=i:       Input interval file
   -o, --output_file=o:      Output MAF file
   -p, --species=p: Species to include in output
   -P, --split_blocks_by_species=P: Split blocks by species
   -r, --remove_all_gap_columns=r: Remove all Gap columns
   -l, --indexLocation=l: Override default maf_index.loc file
   -z, --mafIndexFile=z: Directory of local maf index file ( maf_index.loc or maf_pairwise.loc )
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
        maf_utilities.tool_fail( "You must specify a proper build in order to extract alignments. You can specify your genome build by clicking on the pencil icon associated with your interval file." )
    
    species = maf_utilities.parse_species_option( options.species )
    
    if options.chromCol: chromCol = int( options.chromCol ) - 1
    else: 
        maf_utilities.tool_fail( "Chromosome column not set, click the pencil icon in the history item to set the metadata attributes." )
    
    if options.startCol: startCol = int( options.startCol ) - 1
    else: 
        maf_utilities.tool_fail( "Start column not set, click the pencil icon in the history item to set the metadata attributes." )
    
    if options.endCol: endCol = int( options.endCol ) - 1
    else: 
        maf_utilities.tool_fail( "End column not set, click the pencil icon in the history item to set the metadata attributes." )
    
    if options.strandCol: strandCol = int( options.strandCol ) - 1
    else: 
        strandCol = -1
    
    if options.interval_file: interval_file = options.interval_file
    else: 
        maf_utilities.tool_fail( "Input interval file has not been specified." )
    
    if options.output_file: output_file = options.output_file
    else: 
        maf_utilities.tool_fail( "Output file has not been specified." )
    
    split_blocks_by_species = remove_all_gap_columns = False
    if options.split_blocks_by_species and options.split_blocks_by_species == 'split_blocks_by_species':
        split_blocks_by_species = True
        if options.remove_all_gap_columns and options.remove_all_gap_columns == 'remove_all_gap_columns':
            remove_all_gap_columns = True
    else:
        remove_all_gap_columns = True
    #Finish parsing command line
    
    #Open indexed access to MAFs
    if options.mafType:
        if options.indexLocation:
            index = maf_utilities.maf_index_by_uid( options.mafType, options.indexLocation )
        else:
            index = maf_utilities.maf_index_by_uid( options.mafType, options.mafIndexFile )
        if index is None:
            maf_utilities.tool_fail( "The MAF source specified (%s) appears to be invalid." % ( options.mafType ) )
    elif options.mafFile:
        index, index_filename = maf_utilities.open_or_build_maf_index( options.mafFile, options.mafIndex, species = [dbkey] )
        if index is None:
            maf_utilities.tool_fail( "Your MAF file appears to be malformed." )
    else:
        maf_utilities.tool_fail( "Desired source MAF type has not been specified." )
    
    #Create MAF writter
    out = bx.align.maf.Writer( open(output_file, "w") )
    
    #Iterate over input regions 
    num_blocks = 0
    num_regions = None
    for num_regions, region in enumerate( bx.intervals.io.NiceReaderWrapper( open( interval_file, 'r' ), chrom_col = chromCol, start_col = startCol, end_col = endCol, strand_col = strandCol, fix_strand = True, return_header = False, return_comments = False ) ):
        src = maf_utilities.src_merge( dbkey, region.chrom )
        for block in index.get_as_iterator( src, region.start, region.end ):
            if split_blocks_by_species:
                blocks = [ new_block for new_block in maf_utilities.iter_blocks_split_by_species( block ) if maf_utilities.component_overlaps_region( new_block.get_component_by_src_start( dbkey ), region ) ]
            else:
                blocks = [ block ]
            for block in blocks:
                block = maf_utilities.chop_block_by_region( block, src, region )
                if block is not None:
                    if species is not None:
                        block = block.limit_to_species( species )
                    block = maf_utilities.orient_block_by_region( block, src, region )
                    if remove_all_gap_columns:
                        block.remove_all_gap_columns()
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
