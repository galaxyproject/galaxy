#!/usr/bin/env python
#Original script from /home/james/work/encode/feature_partitions/split_by_partitions.py

#Usage: python(2.4) split_by_partitions.py partition_index in_file out_file chrCol startCol endCol strandCol

from __future__ import division

import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.bitset import *
from bx.bitset_builders import *

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def main():
    GALAXY_DATA_INDEX_DIR = sys.argv[1]
    partition_index = '%s/encode_feature_partitions/partition_list.txt' % GALAXY_DATA_INDEX_DIR
    partition_offset = "%s/encode_feature_partitions/" % GALAXY_DATA_INDEX_DIR
    
    warnings = []
    
    # Load up the partitions
    partitions = list()
    try: 
        for line in open( partition_index ):
            name, score, filename = line.split()
            partitions.append( ( name, score, binned_bitsets_from_file( open( partition_offset+filename ) ) ) )
    except:
        stop_err( "Error loading partitioning dataset." )
    
    try:
        in_file = open( sys.argv[2] )
    except:
        stop_err( "Bad input data." )
        
    try:
        out_file = open( sys.argv[3], "w" )
    except:
        stop_err( "Bad output file." )
    
    try:
        chrCol = int( sys.argv[4] ) - 1
    except:
        stop_err( "Bad chr column: %s" % ( str( sys.argv[4] ) ) )
    try:
        startCol = int( sys.argv[5] ) - 1
    except:
        stop_err( "Bad start column: %s" % ( str( sys.argv[5] ) ) )
    try:
        endCol = int( sys.argv[6] ) - 1
    except:
        stop_err( "Bad end column: %s" % ( str( sys.argv[6] ) ) )
    try:
        strandCol = int( sys.argv[7] )-1
    except:
        strandCol = -1
    
    line_count = 0
    skipped_lines = 0
    first_invalid_line = None
    invalid_line = ''
    try:
        for line in in_file:
            line_count += 1
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split( '\t' )
                try:
                    chr, start, end = fields[chrCol], int( fields[startCol] ), int( fields[endCol] )
                except:
                    skipped_lines += 1
                    if first_invalid_line is None:
                        first_invalid_line = line_count
                        invalid_line = line
                    continue
                label = "input_line_" + str( line_count ) #if input file type was known to be bed, then could guess at label column
                
                if strandCol < 0:
                    strand = "+"
                else:
                    try:
                        strand = fields[strandCol]
                    except:
                        strand = "+"
                
                # Find which partition it overlaps
                overlap = 0
                for name, score, bb in partitions:
                    # Is there at least 1bp overlap?
                    if chr in bb:
                        overlap = bb[chr].count_range( start, end-start )
                        if overlap > 0:
                            break
                else:
                    # No overlap with any partition? For now throw this since the 
                    # partitions tile the encode regions completely, indicate an interval
                    # that does not even overlap an encode region
                    warning = "warning: Interval (%s, %d, %d) does not overlap any partition" % ( chr, start, end ) + ", line[" + str( line_count ) + "]. "
                    warnings.append( warning )
                    name = "no_overlap"
                    score = 0
                # Annotate with the name of the partition
                frac_overlap = overlap / ( end-start )
                # BED6 plus?
                print >>out_file, "%s\t%d\t%d\t%s\t%s\t%s\t%s\t%0.4f" % ( chr, start, end, label, score, strand, name, frac_overlap )
    except:
        out_file.close()
        in_file.close()
        stop_err( "Unknown error while processing line # %d: %s" % ( line_count, line ) )
    out_file.close()
    in_file.close()

    if warnings:
        warn_msg = "This tool is useful on ENCODE regions only, %d warnings, 1st is: " % len( warnings )
        warn_msg += warnings[0]
        print warn_msg
    if skipped_lines:
        print "Skipped %d invalid lines starting at line # %d: %s" % ( skipped_lines, first_invalid_line, invalid_line )

if __name__ == "__main__": main()
