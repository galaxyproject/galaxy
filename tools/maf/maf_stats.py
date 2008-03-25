#!/usr/bin/env python2.4
#Dan Blankenberg
"""
Reads a list of intervals and a maf. Outputs a new set of intervals with statistics appended.
"""

import sys
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.intervals.io
from numpy import zeros
from galaxy.tools.util import maf_utilities

def __main__():
    maf_source_type = sys.argv.pop( 1 )
    input_maf_filename = sys.argv[1].strip()
    input_interval_filename = sys.argv[2].strip()
    output_filename = sys.argv[3].strip()
    dbkey = sys.argv[4].strip()
    try:
        chr_col  = int( sys.argv[5].strip() ) - 1
        start_col = int( sys.argv[6].strip() ) - 1
        end_col = int( sys.argv[7].strip() ) - 1
    except:
        print >>sys.stderr, "You appear to be missing metadata. You can specify your metadata by clicking on the pencil icon associated with your interval file."
        sys.exit()
    summary = sys.argv[8].strip()
    if summary.lower() == "true": summary = True
    else: summary = False

    mafIndexFile = "%s/maf_index.loc" % sys.argv[9]
    index = index_filename = None
    if maf_source_type == "user":
        #index maf for use here
        index, index_filename = maf_utilities.build_maf_index( input_maf_filename, species = [dbkey] )
        if index is None:
            print >>sys.stderr, "Your MAF file appears to be malformed."
            sys.exit()
    elif maf_source_type == "cached":
        #access existing indexes
        index = maf_utilities.maf_index_by_uid( input_maf_filename, mafIndexFile )
        if index is None:
            print >> sys.stderr, "The MAF source specified (%s) appears to be invalid." % ( input_maf_filename )
            sys.exit()
    else:
        print >>sys.stdout, 'Invalid source type specified: %s' % maf_source_type 
        sys.exit()
        
    out = open(output_filename, 'w')
    
    num_region = 0
    species_summary = {}
    total_length = 0
    #loop through interval file
    for num_region, region in enumerate( bx.intervals.io.NiceReaderWrapper( open( input_interval_filename, 'r' ), chrom_col = chr_col, start_col = start_col, end_col = end_col, fix_strand = True, return_header = False, return_comments = False ) ):
        src = "%s.%s" % ( dbkey, region.chrom )
        total_length += ( region.end - region.start )
        coverage = { dbkey: zeros( region.end - region.start, dtype = bool ) }
        
        for block in maf_utilities.get_chopped_blocks_for_region( index, src, region, force_strand='+' ):
            #make sure all species are known
            for c in block.components:
                spec = c.src.split( '.' )[0]
                if spec not in coverage: coverage[spec] = zeros( region.end - region.start, dtype = bool )
            ref = block.get_component_by_src( src )
            #skip gap locations due to insertions in secondary species relative to primary species
            start_offset = ref.start - region.start
            num_gaps = 0
            for i in range( len( ref.text.rstrip().rstrip( "-" ) ) ):
                if ref.text[i] in ["-"]:
                    num_gaps += 1
                    continue
                #Toggle base if covered
                for comp in block.components:
                    spec = comp.src.split( '.' )[0]
                    if comp.text and comp.text[i] not in ['-']:
                        coverage[spec][start_offset + i - num_gaps] = True
        if summary:
            #record summary
            for key in coverage.keys():
                if key not in species_summary: species_summary[key] = 0
                species_summary[key] = species_summary[key] + sum( coverage[key] )
        else:
            #print coverage for interval
            out.write( "%s\t%s\t%s\t%s\n" % ( "\t".join( region.fields ), dbkey, sum( coverage[dbkey] ), len(coverage[dbkey]) - sum( coverage[dbkey] ) ) )
            keys = coverage.keys()
            keys.remove( dbkey )
            keys.sort()
            for key in keys:
                out.write( "%s\t%s\t%s\t%s\n" % ( "\t".join( region.fields ), key, sum( coverage[key] ), len(coverage[key]) - sum( coverage[key] ) ) )
    if summary:
        out.write( "#species\tnucleotides\tcoverage\n" )
        for spec in species_summary:
            out.write( "%s\t%s\t%.4f\n" % ( spec, species_summary[spec], float( species_summary[spec] ) / total_length ) )
    out.close()
    print "%i regions were processed with a total length of %i." % ( num_region, total_length )
    maf_utilities.remove_temp_index_file( index_filename )

if __name__ == "__main__": __main__()
