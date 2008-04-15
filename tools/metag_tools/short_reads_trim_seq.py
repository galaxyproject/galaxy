#! /usr/bin/python
"""
trim reads based on the quality scores
input: read file and quality score file
output: trimmed read file
"""

import os, sys, math, tempfile, zipfile, re

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def unzip( filename ):
    zip_file = zipfile.ZipFile( filename, 'r' )
    tmpfilename = tempfile.NamedTemporaryFile().name
    for name in zip_file.namelist():
        file( tmpfilename, 'a' ).write( zip_file.read( name ) )
    zip_file.close()
    return tmpfilename

def append_to_outfile( outfile_name, seq_title, segments ):
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
    seq_method = sys.argv[1].strip().lower()
    try:
        threshold_trim = int( sys.argv[2].strip() )
    except:
        stop_err( "Minimal quality score must be numeric." )
    try:
        threshold_report = int( sys.argv[3].strip() )
    except:
        stop_err( "Minimal length of trimmed reads must be numeric." )
    outfile_seq_name = sys.argv[4].strip()
    infile_seq_name = sys.argv[5].strip()
    infile_score_name = sys.argv[6].strip()
    arg = sys.argv[7].strip()

    infile_seq_is_zipped = False
    if zipfile.is_zipfile( infile_seq_name ):
        infile_seq_is_zipped = True
        seq_infile_name = unzip( infile_seq_name ) 
    else: seq_infile_name = infile_seq_name
    infile_score_is_zipped = False
    if zipfile.is_zipfile( infile_score_name ):
        infile_score_is_zipped = True 
        score_infile_name = unzip(infile_score_name)
    else: score_infile_name = infile_score_name
    
    if os.path.exists( seq_infile_name ) and os.path.exists( score_infile_name ):
        # read one sequence
        score_found = False
        seq = None
        score = None
        score_file = open( score_infile_name, 'r' )

        if seq_method == '454':
            for i, line in enumerate( open( seq_infile_name ) ):
                line = line.rstrip( '\r\n' )
                if not line or line.startswith( '#' ):
                    continue
                if line.startswith( '>' ):
                    if seq:
                        score_found = False
                        score = None
                        while not score_found:
                            score_line = score_file.readline().rstrip( '\r\n' )
                            if not score_line or score_line.startswith( '#' ):
                                continue
                            if score_line.startswith( '>' ):
                                if score:
                                    score = score.split()
                                    new_trim_seq_segments = trim_seq( seq, score, arg, threshold_trim, threshold_report )                                            
                                    # output trimmed sequence to a fasta file
                                    segments = new_trim_seq_segments.split( ',' )
                                    append_to_outfile( outfile_seq_name, seq_title, segments )
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
                    seq_title = line
                    seq = None
                else:
                    if not seq:
                        seq = line
                    else:
                        seq = "%s%s" % ( seq, line )
            if seq:
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
                    score = score.split()       
                    new_trim_seq_segments = trim_seq( seq, score, arg, threshold_trim, threshold_report )                                            
                    # output trimmed sequence to a fasta file
                    segments = new_trim_seq_segments.split( ',' )
                    append_to_outfile( outfile_seq_name, seq_title, segments )

        elif seq_method == 'solexa':
            for i, line in enumerate( open( seq_infile_name ) ):
                line = line.rstrip( '\r\n' )
                if not line or line.startswith( '#' ):
                    continue
                seq_title = '>%d' % i
                
                # the last column of a solexa file is the sequence column
                # TODO: this will be slow since the replace method creates a new copy of the string.
                # Is there a better way to do this?
                seq = line.split()[-1]
                seq = seq.replace( '.', 'N' )
                seq = seq.replace( '-', 'N' )
                
                if not seq.isalpha():
                    score_file.close()
                    stop_err( "Invalid characters in line %d: '%s'" % ( i, line ) )
                                        
                score = score_file.readline()
                loc = score.split( '\t' )
                scores = []
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
                new_trim_seq_segments = trim_seq( seq, scores, arg, threshold_trim, threshold_report )
                # output trimmed sequence to a fasta file
                segments = new_trim_seq_segments.split( ',' )
                append_to_outfile( outfile_seq_name, seq_title, segments )    
        score_file.close()
    else:
        stop_err( "Cannot locate sequence file '%s'or score file '%s'." % ( seq_infile_name, score_infile_name ) )    

    # Need to delete temporary files created when we unzipped the input file archives                    
    if infile_seq_is_zipped and os.path.exists( seq_infile_name ):
        os.remove( seq_infile_name )
    if infile_score_is_zipped and os.path.exists( score_infile_name ):
        os.remove( score_infile_name )
    
if __name__ == "__main__": __main__()