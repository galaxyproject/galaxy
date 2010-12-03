#!/usr/bin/env python
#By: Guruprasad Ananda
"""
Fetch closest up/downstream interval from features corresponding to every interval in primary

usage: %prog primary_file features_file out_file direction
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
    -2, --cols2=N,N,N,N: Columns for start, end, strand in second file
    -G, --gff1: input 1 is GFF format, meaning start and end coordinates are 1-based, closed interval
    -H, --gff2: input 2 is GFF format, meaning start and end coordinates are 1-based, closed interval
"""
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
import sys, traceback, fileinput
from warnings import warn
from bx.cookbook import doc_optparse
from galaxy.tools.util.galaxyops import *
from bx.intervals.io import *
from bx.intervals.operations import quicksect
from galaxy.datatypes.util.gff_util import *

assert sys.version_info[:2] >= ( 2, 4 )

def get_closest_feature (node, direction, threshold_up, threshold_down, report_func_up, report_func_down):
    #direction=1 for +ve strand upstream and -ve strand downstream cases; and it is 0 for +ve strand downstream and -ve strand upstream cases
    #threhold_Up is equal to the interval start for +ve strand, and interval end for -ve strand
    #threhold_down is equal to the interval end for +ve strand, and interval start for -ve strand
    if direction == 1: 
        if node.maxend <= threshold_up:
            if node.end == node.maxend:
                report_func_up(node)
            elif node.right and node.left:
                if node.right.maxend == node.maxend:
                    get_closest_feature(node.right, direction, threshold_up, threshold_down, report_func_up, report_func_down)
                elif node.left.maxend == node.maxend:
                    get_closest_feature(node.left, direction, threshold_up, threshold_down, report_func_up, report_func_down)
            elif node.right and node.right.maxend == node.maxend:
                get_closest_feature(node.right, direction, threshold_up, threshold_down, report_func_up, report_func_down)
            elif node.left and node.left.maxend == node.maxend:
                get_closest_feature(node.left, direction, threshold_up, threshold_down, report_func_up, report_func_down)
        elif node.minend <= threshold_up:
            if node.end <= threshold_up:
                report_func_up(node)
            if node.left and node.right:
                if node.right.minend <= threshold_up:
                    get_closest_feature(node.right, direction, threshold_up, threshold_down, report_func_up, report_func_down)
                if node.left.minend <= threshold_up:
                    get_closest_feature(node.left, direction, threshold_up, threshold_down, report_func_up, report_func_down)
            elif node.left:
                if node.left.minend <= threshold_up:
                    get_closest_feature(node.left, direction, threshold_up, threshold_down, report_func_up, report_func_down)
            elif node.right:
                if node.right.minend <= threshold_up:
                    get_closest_feature(node.right, direction, threshold_up, threshold_down, report_func_up, report_func_down)
    elif direction == 0:
        if node.start > threshold_down:
            report_func_down(node)
            if node.left:
                get_closest_feature(node.left, direction, threshold_up, threshold_down, report_func_up, report_func_down)
        else:
            if node.right:
                get_closest_feature(node.right, direction, threshold_up, threshold_down, report_func_up, report_func_down)

def proximal_region_finder(readers, region, comments=True):
    """
    Returns an iterator that yields elements of the form [ <original_interval>, <closest_feature> ]. 
    Intervals are GenomicInterval objects. 
    """
    primary = readers[0]
    features = readers[1]
    either = False
    if region == 'Upstream':
        up, down = True, False
    elif region == 'Downstream':
        up, down = False, True
    else:
        up, down = True, True
        if region == 'Either':
            either = True
        
    # Read features into memory:
    rightTree = quicksect.IntervalTree()
    for item in features:
        if type( item ) is GenomicInterval:
            rightTree.insert( item, features.linenum, item )
            
    for interval in primary:
        if type( interval ) is Header:
            yield interval
        if type( interval ) is Comment and comments:
            yield interval
        elif type( interval ) == GenomicInterval:
            chrom = interval.chrom
            start = int(interval.start)
            end = int(interval.end)
            strand = interval.strand
            if chrom not in rightTree.chroms:
                continue
            else:
                root = rightTree.chroms[chrom]    #root node for the chrom tree
                result_up = []
                result_down = []
                if (strand == '+' and up) or (strand == '-' and down): 
                    #upstream +ve strand and downstream -ve strand cases
                    get_closest_feature (root, 1, start, None, lambda node: result_up.append( node ), None)
                    
                if (strand == '+' and down) or (strand == '-' and up):
                    #downstream +ve strand and upstream -ve strand case
                    get_closest_feature (root, 0, None, end-1, None, lambda node: result_down.append( node ))
                
                if result_up:
                    if len(result_up) > 1: #The results_up list has a list of intervals upstream to the given interval. 
                        ends = []
                        for n in result_up:
                            ends.append(n.end)
                        res_ind = ends.index(max(ends)) #fetch the index of the closest interval i.e. the interval with the max end from the results_up list
                    else:
                        res_ind = 0
                    if not(either):
                        yield [ interval, result_up[res_ind].other ]
                
                if result_down:    
                    if not(either):
                        #The last element of result_down will be the closest element to the given interval
                        yield [ interval, result_down[-1].other ] 
                
                if either and (result_up or result_down):
                    iter_val = []
                    if result_up and result_down:
                        if abs(start - int(result_up[res_ind].end)) <= abs(end - int(result_down[-1].start)):
                            iter_val = [ interval, result_up[res_ind].other ]
                        else:
                            #The last element of result_down will be the closest element to the given interval
                            iter_val = [ interval, result_down[-1].other ]
                    elif result_up:
                        iter_val = [ interval, result_up[res_ind].other ]
                    elif result_down:
                        #The last element of result_down will be the closest element to the given interval
                        iter_val = [ interval, result_down[-1].other ]
                    yield iter_val
                        
def main():
    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        chr_col_2, start_col_2, end_col_2, strand_col_2 = parse_cols_arg( options.cols2 )
        in1_gff_format = bool( options.gff1 )
        in2_gff_format = bool( options.gff2 )
        in_fname, in2_fname, out_fname, direction = args
    except:
        doc_optparse.exception()
        
    # Set readers to handle either GFF or default format.
    if in1_gff_format:
        in1_reader_wrapper = GFFIntervalToBEDReaderWrapper
    else:
        in1_reader_wrapper = NiceReaderWrapper
    if in2_gff_format:
        in2_reader_wrapper = GFFIntervalToBEDReaderWrapper
    else:
        in2_reader_wrapper = NiceReaderWrapper

    g1 = in1_reader_wrapper( fileinput.FileInput( in_fname ),
                            chrom_col=chr_col_1,
                            start_col=start_col_1,
                            end_col=end_col_1,
                            strand_col=strand_col_1,
                            fix_strand=True )
    g2 = in2_reader_wrapper( fileinput.FileInput( in2_fname ),
                            chrom_col=chr_col_2,
                            start_col=start_col_2,
                            end_col=end_col_2,
                            strand_col=strand_col_2,
                            fix_strand=True )

    # Find flanking features.
    out_file = open( out_fname, "w" )
    try:
        for result in proximal_region_finder([g1,g2], direction):
            if type( result ) is list:
                line, closest_feature = result
                # Need to join outputs differently depending on file types.
                if in1_gff_format:
                    # Output is GFF with added attribute 'closest feature.'

                    # Invervals are in BED coordinates; need to convert to GFF.
                    line = convert_bed_coords_to_gff( line )
                    closest_feature = convert_bed_coords_to_gff( closest_feature )
                    
                    # Replace double quotes with single quotes in closest feature's attributes.
                    out_file.write( "%s closest_feature \"%s\" \n" % 
                                    ( "\t".join( line.fields ), \
                                      "\t".join( closest_feature.fields ).replace( "\"", "\\\"" )
                                     ) )
                else:
                    # Output is BED + closest feature fields.
                    output_line_fields = []
                    output_line_fields.extend( line.fields )
                    output_line_fields.extend( closest_feature.fields )
                    out_file.write( "%s\n" % ( "\t".join( output_line_fields ) ) )
            else:
                out_file.write( "%s\n" % result )
    except ParseError, exc:
        fail( "Invalid file format: %s" % str( exc ) )

    print "Direction: %s" %(direction)
    if g1.skipped > 0:
        print skipped( g1, filedesc=" of 1st dataset" )
    if g2.skipped > 0:
        print skipped( g2, filedesc=" of 2nd dataset" )

if __name__ == "__main__":
    main()
