#!/usr/bin/env python
#By: Guruprasad Ananda
"""
Fetch closest up/downstream interval from features corresponding to every interval in primary

usage: %prog primary_file features_file out_file direction
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
    -2, --cols2=N,N,N,N: Columns for start, end, strand in second file
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

assert sys.version_info[:2] >= ( 2, 4 )

def get_closest_feature (node, direction, threshold_up, threshold_down, report_func_up, report_func_down):
    #direction=1 for +ve strand upstream and -ve strand downstream cases; and it is 0 for +ve strand downstream and -ve strand upstream cases
    #threhold_Up is equal to the interval start for +ve strand, and interval end for -ve strand
    #threhold_down is equal to the interval end for +ve strand, and interval start for -ve strand
    if direction == 1: 
        if node.maxend < threshold_up:
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
        elif node.minend < threshold_up:
            if node.end < threshold_up:
                report_func_up(node)
            if node.left and node.right:
                if node.right.minend < threshold_up:
                    get_closest_feature(node.right, direction, threshold_up, threshold_down, report_func_up, report_func_down)
                if node.left.minend < threshold_up:
                    get_closest_feature(node.left, direction, threshold_up, threshold_down, report_func_up, report_func_down)
            elif node.left:
                if node.left.minend < threshold_up:
                    get_closest_feature(node.left, direction, threshold_up, threshold_down, report_func_up, report_func_down)
            elif node.right:
                if node.right.minend < threshold_up:
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
            rightTree.insert( item, features.linenum, item.fields )
            
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
                    get_closest_feature (root, 0, None, end, None, lambda node: result_down.append( node ))
                
                if result_up:
                    outfields = list(interval)
                    if len(result_up) > 1: #The results_up list has a list of intervals upstream to the given interval. 
                        ends = []
                        for n in result_up:
                            ends.append(n.end)
                        res_ind = ends.index(max(ends)) #fetch the index of the closest interval i.e. the interval with the max end from the results_up list
                    else:
                        res_ind = 0
                    if not(either):
                        map(outfields.append, result_up[res_ind].other)
                        yield outfields
                
                if result_down:    
                    outfields = list(interval)
                    if not(either):
                        map(outfields.append, result_down[-1].other) #The last element of result_down will be the closest element to the given interval
                        yield outfields
                
                if either:
                    if result_up and result_down:
                        if abs(start - int(result_up[res_ind].end)) <= abs(end - int(result_down[-1].start)):
                            map(outfields.append, result_up[res_ind].other)
                        else:
                            map(outfields.append, result_down[-1].other) #The last element of result_down will be the closest element to the given interval
                    elif result_up:
                        map(outfields.append, result_up[res_ind].other)
                    else:
                        map(outfields.append, result_down[-1].other) #The last element of result_down will be the closest element to the given interval
                    yield outfields
                    
                        
def main():
    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        chr_col_2, start_col_2, end_col_2, strand_col_2 = parse_cols_arg( options.cols2 )      
        in_fname, in2_fname, out_fname, direction = args
    except:
        doc_optparse.exception()

    g1 = NiceReaderWrapper( fileinput.FileInput( in_fname ),
                            chrom_col=chr_col_1,
                            start_col=start_col_1,
                            end_col=end_col_1,
                            strand_col=strand_col_1,
                            fix_strand=True )
    g2 = NiceReaderWrapper( fileinput.FileInput( in2_fname ),
                            chrom_col=chr_col_2,
                            start_col=start_col_2,
                            end_col=end_col_2,
                            strand_col=strand_col_2,
                            fix_strand=True )
    out_file = open( out_fname, "w" )
    try:
        for line in proximal_region_finder([g1,g2], direction):
            if type( line ) is list:
                out_file.write( "%s\n" % "\t".join( line ) )
            else:
                out_file.write( "%s\n" % line )
    except ParseError, exc:
        fail( "Invalid file format: %s" % str( exc ) )

    print "Direction: %s" %(direction)
    if g1.skipped > 0:
        print skipped( g1, filedesc=" of 1st dataset" )
    if g2.skipped > 0:
        print skipped( g2, filedesc=" of 2nd dataset" )

if __name__ == "__main__":
    main()
