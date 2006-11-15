#!/usr/bin/env python2.4
#Original script from /home/james/work/encode/feature_partitions/split_by_partitions.py

#Usage: python(2.4) split_by_partitions.py partition_index in_file out_file chrCol startCol endCol strandCol

from __future__ import division

import sys
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.bitset import *
from bx.bitset_builders import *


partition_index = sys.argv[1]
partition_offset = "/home/james/work/encode/feature_partitions/" #should parse perhaps from index filepath

warnings = []

# Load up the partitions
partitions = list()
try: 
    for line in open( partition_index ):
        name, score, filename = line.split()
        partitions.append( ( name, score, binned_bitsets_from_file( open( partition_offset+filename ) ) ) )
except:
    print >> sys.stderr, "Error loading partitioning dataset."
    sys.exit(0)

try:
    in_file = open(sys.argv[2])
except:
    print >> sys.stderr, "Bad input data."
    sys.exit(0)
    
try:
    out_file = open(sys.argv[3], "w")
except:
    print >> sys.stderr, "Bad output file."
    sys.exit(0)

try:
    chrCol = int (sys.argv[4])-1
except:
    print >> sys.stderr, "Bad chr column."
    sys.exit(0)
try:
    startCol = int (sys.argv[5])-1
except:
    print >> sys.stderr, "Bad start column."
    sys.exit(0)
try:
    endCol = int (sys.argv[6])-1
except:
    print >> sys.stderr, "Bad end column."
    sys.exit(0)
try:
    strandCol = int (sys.argv[7])-1
except:
    print >> sys.stderr, "Bad strand column."
    sys.exit(0)

line_count = 0
try:
    for line in in_file:
        line_count+=1
        #ignore comment lines
        if line[0:1] == "#":
            continue
        fields = line.rstrip().split( "\t" )
        try:
            chr, start, end = fields[chrCol], int( fields[startCol] ), int( fields[endCol] )
        except:
            print >> sys.stderr, "Not enough columns on line ", line_count
            continue
        label = "input_line_"+str(line_count) #if input file type was known to be bed, then could guess at label column
        
        if strandCol < 0 :
            strand = "+"
        else:
            try:
                strand = fields[strandCol]
            except:
                strand = "+"
        
        # Find which partition it overlaps
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
            warning = "warning: Interval (%s, %d, %d) does not overlap any partition" % ( chr, start, end )+", line["+str(line_count)+"]"
            warnings.append(warning)
        # Annotate with the name of the partition
        frac_overlap = overlap / (end-start)
        # BED6 plus?
        print >>out_file, "%s\t%d\t%d\t%s\t%s\t%s\t%s\t%0.4f" % ( chr, start, end, label, score, strand, name, frac_overlap )
except:
    print >> sys.stderr, "Unknown error while processing line",line_count
out_file.close()
in_file.close()

if len(warnings) > 5:
    print >> sys.stderr, "There were more than 5 warnings, this tool is useful on ENCODE regions only."
else:
    for warning in warnings:
        print >> sys.stderr, warning