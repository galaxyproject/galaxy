#!/usr/bin/env python
"""
trim reads based on the quality scores
input: read file and quality score file
output: trimmed read file
"""

import os, sys, math, tempfile, re

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def append_to_outfile( outfile_name, seq_title, segments ):
    segments = segments.split( ',' )
    if len( segments ) > 1:
        outfile = open( outfile_name, 'a' )
        for i in range( len( segments ) ):
            outfile.write( "%s_%d\n%s\n" % ( seq_title, i, segments[i] ) )
        outfile.close()
    elif segments[0]:
        outfile = open( outfile_name, 'a' )
        outfile.write( "%s\n%s\n" % ( seq_title, segments[0] ) )
        outfile.close()

def trim_seq( seq, score, arg, trim_score, threshold ):
    seq_method = '454'
    trim_pos = 0
    # trim after a certain position
    if arg.isdigit():
        keep_homopolymers = False
        trim_pos = int( arg )    
        if trim_pos > 0 and trim_pos < len( seq ):
            seq = seq[0:trim_pos]
    else:
        keep_homopolymers = arg=='yes'
        
    new_trim_seq = ''
    max_segment = 0

    for i in range( len( seq ) ):
        if i >= len( score ):
            score.append(-1)   
        if int( score[i] ) >= trim_score:
            pass_nuc = seq[ i:( i + 1 ) ]
        else:
            if keep_homopolymers and ( (i == 0 ) or ( seq[ i:( i + 1 ) ].lower() == seq[ ( i - 1 ):i ].lower() ) ):
                pass_nuc = seq[ i:( i + 1 ) ]
            else:
                pass_nuc = ' '    
        new_trim_seq = '%s%s' % ( new_trim_seq, pass_nuc )
        # find the max substrings
        segments = new_trim_seq.split()
        max_segment = ''
        len_max_segment = 0
        if threshold == 0:
            for seg in segments:
                if len_max_segment < len( seg ):
                    max_segment = '%s,' % seg
                    len_max_segment = len( seg )
                elif len_max_segment == len( seg ):
                    max_segment = '%s%s,' % ( max_segment, seg )
        else:
            for seg in segments:
                if len( seg ) >= threshold:
                    max_segment = '%s%s,' % ( max_segment, seg )
    return max_segment[ 0:-1 ]

def __main__():
    
    try:
        threshold_trim = int( sys.argv[1].strip() )
    except:
        stop_err( "Minimal quality score must be numeric." )
    try:
        threshold_report = int( sys.argv[2].strip() )
    except:
        stop_err( "Minimal length of trimmed reads must be numeric." )
    outfile_seq_name = sys.argv[3].strip()
    infile_seq_name = sys.argv[4].strip()
    infile_score_name = sys.argv[5].strip()
    arg = sys.argv[6].strip()

    seq_infile_name = infile_seq_name
    score_infile_name = infile_score_name
    

    # Determine quailty score format: tabular or fasta format within the first 100 lines
    seq_method = None
    data_type = None
    for i, line in enumerate( file( score_infile_name ) ):
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
    
    if os.path.exists( seq_infile_name ) and os.path.exists( score_infile_name ):
        seq = None
        score = None
        score_found = False
        
        score_file = open( score_infile_name, 'r' )

        for i, line in enumerate( open( seq_infile_name ) ):
            line = line.rstrip( '\r\n' )
            if not line or line.startswith( '#' ):
                continue
            if line.startswith( '>' ):
                if seq:
                    scores = []
                    if data_type == 'fasta':
                        score = None
                        score_found = False
                        score_line = 'start'
                        while not score_found and score_line:
                            score_line = score_file.readline().rstrip( '\r\n' )
                            if not score_line or score_line.startswith( '#' ):
                                continue
                            if score_line.startswith( '>' ):
                                if score:
                                    scores = score.split()
                                    score_found = True    
                                score = None
                            else:
                                for val in score_line.split():
                                    try:
                                        int( val ) 
                                    except:
                                        score_file.close()
                                        stop_err( "Non-numerical value '%s' in score file." % val )
                                if not score:
                                    score = score_line
                                else:
                                    score = '%s %s' % ( score, score_line )                                        
                    elif data_type == 'tabular':
                        score = score_file.readline().rstrip('\r\n')
                        loc = score.split( '\t' )
                        for base in loc:
                            nuc_error = base.split()
                            try:
                                nuc_error[0] = int( nuc_error[0] )
                                nuc_error[1] = int( nuc_error[1] )
                                nuc_error[2] = int( nuc_error[2] )
                                nuc_error[3] = int( nuc_error[3] )
                                big = max( nuc_error )
                            except:
                                score_file.close()
                                stop_err( "Invalid characters in line %d: '%s'" % ( i, line ) )
                            scores.append( big )
                    if scores:
                        new_trim_seq_segments = trim_seq( seq, scores, arg, threshold_trim, threshold_report )
                        append_to_outfile( outfile_seq_name, seq_title, new_trim_seq_segments )  
                                
                seq_title = line
                seq = None
            else:
                if not seq:
                    seq = line
                else:
                    seq = "%s%s" % ( seq, line )
        if seq:
            scores = []
            if data_type == 'fasta':
                score = None
                while score_line:
                    score_line = score_file.readline().rstrip( '\r\n' )
                    if not score_line or score_line.startswith( '#' ) or score_line.startswith( '>' ):
                        continue
                    for val in score_line.split():
                        try:
                            int( val )
                        except:
                            score_file.close()
                            stop_err( "Non-numerical value '%s' in score file." % val )
                    if not score:
                        score = score_line
                    else:
                        score = "%s %s" % ( score, score_line ) 
                if score: 
                    scores = score.split()
            elif data_type == 'tabular':
                score = score_file.readline().rstrip('\r\n')
                loc = score.split( '\t' )
                for base in loc:
                    nuc_error = base.split()
                    try:
                        nuc_error[0] = int( nuc_error[0] )
                        nuc_error[1] = int( nuc_error[1] )
                        nuc_error[2] = int( nuc_error[2] )
                        nuc_error[3] = int( nuc_error[3] )
                        big = max( nuc_error )
                    except:
                        score_file.close()
                        stop_err( "Invalid characters in line %d: '%s'" % ( i, line ) )
                    scores.append( big )
            if scores:
                new_trim_seq_segments = trim_seq( seq, scores, arg, threshold_trim, threshold_report )
                append_to_outfile( outfile_seq_name, seq_title, new_trim_seq_segments )  
        score_file.close()
    else:
        stop_err( "Cannot locate sequence file '%s'or score file '%s'." % ( seq_infile_name, score_infile_name ) )    

if __name__ == "__main__": __main__()
