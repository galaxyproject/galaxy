#!/usr/bin/env python
"""
boxplot:
- box: first quartile and third quartile
- line inside the box: median
- outlier: 1.5 IQR higher than the third quartile or 1.5 IQR lower than the first quartile
           IQR = third quartile - first quartile
- The smallest/largest value that is not an outlier is connected to the box by with a horizontal line.
"""

import os, sys, math, tempfile, re
from rpy import *

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def merge_to_20_datapoints( score ):
    number_of_points = 20
    read_length = len( score )
    step = int( math.floor( ( read_length - 1 ) * 1.0 / number_of_points ) )
    scores = []
    point = 1
    point_sum = 0
    step_average = 0
    score_points = 0
    
    for i in xrange( 1, read_length ):
        if i < ( point * step ):
            point_sum += int( score[i] )
            step_average += 1
        else:
            point_avg = point_sum * 1.0 / step_average
            scores.append( point_avg )
            point += 1
            point_sum = 0
            step_average = 0                       
    if step_average > 0:
        point_avg = point_sum * 1.0 / step_average
        scores.append( point_avg )
    if len( scores ) > number_of_points:
        last_avg = 0
        for j in xrange( number_of_points - 1, len( scores ) ):
            last_avg += scores[j]
        last_avg = last_avg / ( len(scores) - number_of_points + 1 )
    else:    
        last_avg = scores[-1]
    score_points = []
    for k in range( number_of_points - 1 ):
        score_points.append( scores[k] )
    score_points.append( last_avg )
    return score_points

def __main__():

    invalid_lines = 0

    infile_score_name = sys.argv[1].strip()
    outfile_R_name = sys.argv[2].strip()

    infile_name = infile_score_name

    # Determine tabular or fasta format within the first 100 lines
    seq_method = None
    data_type = None
    for i, line in enumerate( file( infile_name ) ):
        line = line.rstrip( '\r\n' )
        if not line or line.startswith( '#' ):
            continue
        if data_type == None:
            if line.startswith( '>' ):
                data_type = 'fasta'
                continue
            elif len( line.split( '\t' ) ) > 0:
                fields = line.split()
                for score in fields:
                    try:
                        int( score )
                        data_type = 'tabular'
                        seq_method = 'solexa'
                        break
                    except:
                        break
        elif data_type == 'fasta':
            fields = line.split()
            for score in fields:
                try: 
                    int( score )
                    seq_method = '454'
                    break
                except:
                    break
        if i == 100:
            break

    if data_type is None:
        stop_err( 'This tool can only use fasta data or tabular data.' ) 
    if seq_method is None:
        stop_err( 'Invalid data for fasta format.')

    # Determine fixed length or variable length within the first 100 lines
    read_length = 0
    variable_length = False
    if seq_method == 'solexa':
        for i, line in enumerate( file( infile_name ) ):
            line = line.rstrip( '\r\n' )
            if not line or line.startswith( '#' ):
                continue
            scores = line.split('\t')
            if read_length == 0:
                read_length = len( scores )
            if read_length != len( scores ):
                variable_length = True
                break
            if i == 100:
                break
    elif seq_method == '454':
        score = ''
        for i, line in enumerate( file( infile_name ) ):
            line = line.rstrip( '\r\n' )
            if not line or line.startswith( '#' ):
                continue
            if line.startswith( '>' ):
                if len( score ) > 0:
                    score = score.split()
                    if read_length == 0:
                        read_length = len( score )
                    if read_length != len( score ):
                        variable_length = True
                        break
                score = ''
            else:
                score = score + ' ' + line
            if i == 100:
                break

    if variable_length:
        number_of_points = 20
    else:
        number_of_points = read_length
    read_length_threshold = 100 # minimal read length for 454 file
    score_points = []   
    score_matrix = []
    invalid_scores = 0   

    if seq_method == 'solexa':
        for i, line in enumerate( open( infile_name ) ):
            line = line.rstrip( '\r\n' )
            if not line or line.startswith( '#' ):
                continue
            tmp_array = []
            scores = line.split( '\t' )
            for bases in scores:
                nuc_errors = bases.split()
                try:
                    nuc_errors[0] = int( nuc_errors[0] )
                    nuc_errors[1] = int( nuc_errors[1] )
                    nuc_errors[2] = int( nuc_errors[2] )
                    nuc_errors[3] = int( nuc_errors[3] )
                    big = max( nuc_errors )
                except:
                    #print 'Invalid numbers in the file. Skipped.'
                    invalid_scores += 1
                    big = 0
                tmp_array.append( big )                        
            score_points.append( tmp_array )
    elif seq_method == '454':
        # skip the last fasta sequence
        score = ''
        for i, line in enumerate( open( infile_name ) ):
            line = line.rstrip( '\r\n' )
            if not line or line.startswith( '#' ):
                continue
            if line.startswith( '>' ):
                if len( score ) > 0:
                    score = ['0'] + score.split()
                    read_length = len( score )
                    tmp_array = []
                    if not variable_length:
                        score.pop(0)
                        score_points.append( score )
                        tmp_array = score
                    elif read_length > read_length_threshold:
                        score_points_tmp = merge_to_20_datapoints( score )
                        score_points.append( score_points_tmp )
                        tmp_array = score_points_tmp
                score = ''
            else:
                score = "%s %s" % ( score, line )
        if len( score ) > 0:
            score = ['0'] + score.split()
            read_length = len( score )
            if not variable_length:
                score.pop(0)
                score_points.append( score )
            elif read_length > read_length_threshold:
                score_points_tmp = merge_to_20_datapoints( score )
                score_points.append( score_points_tmp )
                tmp_array = score_points_tmp

    # reverse the matrix, for R
    for i in range( number_of_points - 1 ):
        tmp_array = []
        for j in range( len( score_points ) ):
            try:
                tmp_array.append( int( score_points[j][i] ) )
            except:
                invalid_lines += 1
        score_matrix.append( tmp_array )

    # generate pdf figures
    #outfile_R_pdf = outfile_R_name 
    #r.pdf( outfile_R_pdf )
    outfile_R_png = outfile_R_name
    r.bitmap( outfile_R_png )
    
    title = "boxplot of quality scores"
    empty_score_matrix_columns = 0
    for i, subset in enumerate( score_matrix ):
        if not subset:
            empty_score_matrix_columns += 1
            score_matrix[i] = [0]
            
    if not variable_length:
        r.boxplot( score_matrix, xlab="location in read length", main=title )
    else:
        r.boxplot( score_matrix, xlab="position within read (% of total length)", xaxt="n", main=title )
        x_old_range = []
        x_new_range = []
        step = read_length_threshold / number_of_points 
        for i in xrange( 0, read_length_threshold, step ):
            x_old_range.append( ( i / step ) )
            x_new_range.append( i )
        r.axis( 1, x_old_range, x_new_range )
    r.dev_off()

    if invalid_scores > 0:
        print 'Skipped %d invalid scores. ' % invalid_scores
    if invalid_lines > 0:
        print 'Skipped %d invalid lines. ' % invalid_lines
    if empty_score_matrix_columns > 0:
        print '%d missing scores in score_matrix. ' % empty_score_matrix_columns

    r.quit(save = "no")

if __name__=="__main__":__main__()
