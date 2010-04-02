#!/usr/bin/env python

import os, sys, math, tempfile, zipfile, re
from rpy import *

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

def __main__():
    infile_score_name = sys.argv[1].strip()
    outfile_R_name = sys.argv[2].strip()
    
    try:
        score_threshold = int( sys.argv[3].strip() )
    except:
        stop_err( 'Threshold for quality score must be numerical.' )

    infile_is_zipped = False
    if zipfile.is_zipfile( infile_score_name ):
        infile_is_zipped = True
        infile_name = unzip( infile_score_name )
    else:
        infile_name = infile_score_name

    # detect whether it's tabular or fasta format
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
 
    cont_high_quality = []
    invalid_lines = 0
    invalid_scores = 0                       
    if seq_method == 'solexa':
        for i, line in enumerate( open( infile_name ) ):
            line = line.rstrip( '\r\n' )
            if not line or line.startswith( '#' ):
                continue
            locs = line.split( '\t' )
            for j, base in enumerate( locs ):
                nuc_errors = base.split()
                try:
                    nuc_errors[0] = int( nuc_errors[0] )
                    nuc_errors[1] = int( nuc_errors[1] )
                    nuc_errors[2] = int( nuc_errors[2] )
                    nuc_errors[3] = int( nuc_errors[3] )
                    big = max( nuc_errors )
                except:
                    invalid_scores += 1
                    big = 0
                if j == 0:
                    cont_high_quality.append(1)
                else:
                    if big >= score_threshold:
                        cont_high_quality[ len( cont_high_quality ) - 1 ] += 1
                    else:
                        cont_high_quality.append(1)
    else: # seq_method == '454'
        tmp_score = ''
        for i, line in enumerate( open( infile_name ) ):
            line = line.rstrip( '\r\n' )
            if not line or line.startswith( '#' ):
                continue
            if line.startswith( '>' ):
                if len( tmp_score ) > 0:
                    locs = tmp_score.split()
                    for j, base in enumerate( locs ):
                        try:
                            base = int( base )
                        except:
                            invalid_scores += 1
                            base = 0
                        if j == 0:
                            cont_high_quality.append(1)
                        else:
                            if base >= score_threshold:
                                cont_high_quality[ len( cont_high_quality ) - 1 ] += 1
                            else:
                                cont_high_quality.append(1)
                tmp_score = ''
            else:
                tmp_score = "%s %s" % ( tmp_score, line )
        if len( tmp_score ) > 0:
            locs = tmp_score.split()
            for j, base in enumerate( locs ):
                try:
                    base = int( base )
                except:
                    invalid_scores += 1
                    base = 0
                if j == 0:
                    cont_high_quality.append(1)
                else:
                    if base >= score_threshold:
                        cont_high_quality[ len( cont_high_quality ) - 1 ] += 1
                    else:
                        cont_high_quality.append(1)

    # generate pdf figures
    cont_high_quality = array ( cont_high_quality )
    outfile_R_pdf = outfile_R_name 
    r.pdf( outfile_R_pdf )
    title = "Histogram of continuous high quality scores"
    xlim_range = [ 1, max( cont_high_quality ) ]
    nclass = max( cont_high_quality )
    if nclass > 100:
        nclass = 100
    r.hist( cont_high_quality, probability=True, xlab="Continuous High Quality Score length (bp)", ylab="Frequency (%)", xlim=xlim_range, main=title, nclass=nclass)
    r.dev_off()    

    if infile_is_zipped and os.path.exists( infile_name ):
        # Need to delete temporary file created when we unzipped the infile archive
        os.remove( infile_name )

    if invalid_lines > 0: 
        print 'Skipped %d invalid lines. ' % invalid_lines
    if invalid_scores > 0:
        print 'Skipped %d invalid scores. ' % invalid_scores

    r.quit( save="no" )

if __name__=="__main__":__main__()