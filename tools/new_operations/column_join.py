#!/usr/bin/env python

"""
This tool takes a tab-delimited text file as input and creates filters on columns based on certain properties. The tool will skip over invalid lines within the file, informing the user about the number of lines skipped.

usage: %prog output input1 input2 column1[,column2[,column3[,...]]] hinge1[,hinge2[,hinge3[,...]]] [other_input1 [other_input2 [other_input3 ...]]]
    output: the output pileup
    input1: the pileup file to start with
    input2: the second pileup file to join
    hinge: the columns to be used for matching
    columns: the columns that should appear in the output
    other_inputs: the other input files to join

"""

import os, re, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def hinge_compare( hinge1, hinge2 ):
    """
    Compares items like 'chr10' and 'chrM' or 'scaffold2' and scaffold10' so that
    first part handled as text but last part as number
    """
    pat = re.compile( '(?P<text>\D*)(?P<number>\d+)?' )
    split_hinge1 = hinge1.split( '\t' )
    split_hinge2 = hinge2.split( '\t' )
    for i in range( len( split_hinge1 ) ):
        if split_hinge1[ i ] == split_hinge2[ i ]:
            continue
        try:
            if int( split_hinge1[ i ] ) > int( split_hinge2[ i ] ):
                return 1
            else:
                return -1
        except ValueError:
            try:
                if float( split_hinge1[ i ] ) > float( split_hinge2[ i ] ):
                    return 1
                else:
                    return -1
            except ValueError:
                return ref_compare( split_hinge1[ i ], split_hinge2[ i ])
    return 0

def ref_compare( ref1, ref2 ):
    """
    Compares items like 'chr10' and 'chrM' or 'scaffold2' and scaffold10' so that
    first part handled as text but last part as number
    """
    pat = re.compile( '(?P<text>\D*)(?P<number>\d+)?' )
    r1 = pat.match( ref1 )
    r2 = pat.match( ref2 )
    if not r2:
        return 1
    elif not r1:
        return -1
    text1, num1 = r1.groupdict()[ 'text' ].strip(), r1.groupdict()[ 'number' ]
    text2, num2 = r2.groupdict()[ 'text' ].strip(), r2.groupdict()[ 'number' ]
    if text2 == '' and ( num2 == '' or num2 is None ):
        return 1
    elif text1 == '' and ( num1 == '' or num1 is None ):
        return -1
    if text1 > text2:
        return 1
    elif text1 == text2:
        if not ( num1 is None or num2 is None ):
            num1 = int( num1 )
            num2 = int( num2 )
        if num1 > num2:
            return 1
        elif num1 == num2:
            return 0
        elif num1 < num2:
            return -1
    elif text1 < text2:
        return -1

def hinge_sort( infile, outfile, hinge ):
    """Given input file name, sorts logically (text vs. numeric) into provided output file name."""
    hinge_locs = {}
    bad_lines = []
    fin = open( infile, 'rb' )
    line = fin.readline()
    while line.strip():
        try:
            hinge_parts = line.split( '\t' )[ :hinge ]
            try:
                hinge_locs[ '\t'.join( hinge_parts ) ].append( fin.tell() - len( line.strip() ) - 1 )
            except KeyError:
                hinge_locs[ '\t'.join( hinge_parts ) ] = [ fin.tell() - len( line.strip() ) - 1 ]
        except ValueError:
            bad_line.append( line )
        line = fin.readline()
    fin.close()
    fin = open( infile, 'rb' )
    fout = open( outfile, 'wb' )
    hinge_locs_sorted = hinge_locs.keys()
    hinge_locs_sorted.sort( hinge_compare )
    for hinge_loc in hinge_locs_sorted:
        locs = hinge_locs[ hinge_loc ]
        for loc in locs:
            fin.seek( loc )
            fout.write( fin.readline() )
    fout.close()
    fin.close()

def min_chr_pos( chr_pos ):
    """Given line and hinge, identifies the 'smallest' one, from left to right"""
    if len( chr_pos ) == 0 and ''.join( chr_pos ):
        return ''
    min_loc = len( chr_pos )
    min_hinge = []
    loc = 0
    for c_pos in chr_pos:
        if c_pos.strip():
            split_c = c_pos.split( '\t' )
            
            
            ref, pos = c_pos.split( '\t' )[:2]
            pos = int( pos )
            if not min_hinge:
                min_hinge = split_c
                min_loc = loc
            else:
                ref_comp = ref_compare( ref, min_ref_pos[0] )
                if ref_comp < 0:
                    min_ref_pos = [ ref, pos ]
                    min_loc = loc
                elif ref_comp == 0 and pos < min_ref_pos[1]:
                    min_ref_pos[1] = pos
                    min_loc = loc
        loc += 1
    return '%s\t%s' % tuple( min_ref_pos ), min_loc

def __main__():
    output = sys.argv[1]
    input1 = sys.argv[2]
    input2 = sys.argv[3]
    hinge = int( sys.argv[4] )
    cols = [ int( c ) for c in sys.argv[5].split( ',' ) ]
    inputs = sys.argv[6:]
    assert len( cols ) > 2, 'You need to select at least one column in addition to the first two'
    # make sure all files are sorted in same way, ascending
    tmp_input_files = []
    input_files = [ input1, input2 ]
    input_files.extend( inputs ) 
    for in_file in input_files:
        tmp_file = tempfile.NamedTemporaryFile()
        tmp_file_name = tmp_file.name
        tmp_file.close()
        hinge_sort( in_file, tmp_file_name, hinge )
        tmp_file = open( tmp_file_name, 'rb' )
        tmp_input_files.append( tmp_file )
    # cycle through files, getting smallest line of all files one at a time
    # also have to keep track of vertical position of extra columns
    fout = file( output, 'w' )
    old_current = ''
    first_line = True
    current_lines = [ f.readline() for f in tmp_input_files ]
    last_lines = ''.join( current_lines ).strip()
    last_loc = -1
    i = 0
    while last_lines:
        # get the "minimum" hinge, which should come first, and the file location in list
        hinges = [ '\t'.join( line.split( '\t' )[ :hinge ] ) for line in current_lines ]
        hinge_dict = {}
        for i in range( len( hinges ) ):
            if not hinge_dict.has_key( hinges[ i ] ):
                hinge_dict[ hinges[ i ] ] = i
        hinges.sort( hinge_compare )
        hinges = [ h for h in hinges if h ]
        current, loc = hinges[0], hinge_dict[ hinges[0] ]
        # first output empty columns for vertical alignment (account for "missing" files)
        if current != old_current:
            last_loc = -1
        if loc - last_loc > 1:
            current_data = [ '' for col in range( ( loc - last_loc - 1 ) * len( [ col for col in cols if col > hinge ] ) ) ]
        else:
            current_data = []
        # now output actual data
        split_line = current_lines[ loc ].strip().split( '\t' )
        if ''.join( split_line ):
            for col in cols:
                if col > hinge:
                    current_data.append( split_line[ col - 1 ] )
            current_lines[ loc ] = tmp_input_files[ loc ].readline()
            if current == old_current:
                if current_data:
                    fout.write( '\t%s' % '\t'.join( current_data ) )
            else:
                if not first_line:
                    fout.write( '\n' )
                fout.write( '%s\t%s' % ( current, '\t'.join( current_data ) ) )
                first_line = False
        old_current = current
        last_lines = ''.join( current_lines ).strip()
        last_loc = loc
    fout.write( '\n' )
    for f in tmp_input_files:
        os.unlink( f.name )
    fout.close()

if __name__ == "__main__" : __main__()
