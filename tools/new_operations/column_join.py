#!/usr/bin/env python

"""
This tool takes a tab-delimited text file as input and creates filters on columns based on certain properties. The tool will skip over invalid lines within the file, informing the user about the number of lines skipped.

usage: %prog -o output -1 input1 -2 input2 -c column1[,column2[,column3[,...]]] -g hinge1[,hinge2[,hinge3[,...]]] -f <fill_options_file> [other_input1 [other_input2 [other_input3 ...]]]
    -o, output=0: the output pileup
    -1, input1=1: the pileup file to start with
    -2, input2=2: the second pileup file to join
    -g, hinge=h: the columns to be used for matching
    -c, columns=c: the columns that should appear in the output
    -f, fill_options_file=f: the file specifying the fill value to use
    other_inputs: the other input files to join
"""

import optparse, os, re, struct, sys, tempfile

try:
    simple_json_exception = None
    from galaxy import eggs
    from galaxy.util.bunch import Bunch
    from galaxy.util import stringify_dictionary_keys
    import pkg_resources
    pkg_resources.require("simplejson")
    import simplejson
except Exception, e:
    simplejson_exception = e
    simplejson = None

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def split_nums( text ):
    """
    Splits a string into pieces of numbers and non-numbers, like 'abc23B3' --> [ 'abc', 23, 'B', 3 ]
    """
    split_t = []
    c = ''
    n = ''
    for ch in text:
        try:
            v = int( ch )
            n += ch
            if c:
                split_t.append( ''.join( c ) )
                c = ''
        except ValueError:
            c += ch
            if n:
                split_t.append( int( ''.join( n ) ) )
                n = ''
    if c:
        split_t.append( ''.join( c ) )
    if n:
        split_t.append( int( ''.join( n ) ) )
    return split_t

def hinge_compare( hinge1, hinge2 ):
    """
    Compares items like 'chr10' and 'chrM' or 'scaffold2' and scaffold10' so that
    first part handled as text but last part as number
    """
    split_hinge1 = hinge1.split( '\t' )
    split_hinge2 = hinge2.split( '\t' )
    # quick check if either hinge is empty
    if not ''.join( split_hinge2 ):
        if ''.join( split_hinge1 ):
            return 1
        elif not ''.join( split_hinge1 ):
            return 0
    else:
        if not ''.join( split_hinge1 ):
            return -1
    # go through all parts of the hinges and compare
    for i, sh1 in enumerate( split_hinge1 ):
        # if these hinge segments are the same, just move on to the next ones
        if sh1 == split_hinge2[ i ]:
            continue
        # check all parts of each hinge
        h1 = split_nums( sh1 )
        h2 = split_nums( split_hinge2[ i ] )
        for j, h in enumerate( h1 ):
            # if second hinge has no more parts, first is considered larger
            if j > 0 and len( h2 ) <= j:
                return 1
            # if these two parts are the same, move on to next
            if h == h2[ j ]:
                continue
            # do actual comparison, depending on whether letter or number
            if type( h ) == int:
                if type( h2[ j ] ) == int:
                    if h > h2[ j ]:
                        return 1
                    elif h < h2[ j ]:
                        return -1
                # numbers are less than letters
                elif type( h2[ j ] ) == str:
                    return -1
            elif type( h ) == str:
                if type( h2[ j ] ) == str:
                    if h > h2[ j ]:
                        return 1
                    elif h < h2[ j ]:
                        return -1
                # numbers are less than letters
                elif type( h2[ j ] ) == int:
                    return 1
    # if all else has failed, just do basic string comparison
    if hinge1 > hinge2:
        return 1
    elif hinge1 == hinge2:
        return 0
    elif hinge1 < hinge2:
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
                hinge_locs[ '\t'.join( hinge_parts ) ].append( fin.tell() - len( line ) )
            except KeyError:
                hinge_locs[ '\t'.join( hinge_parts ) ] = [ fin.tell() - len( line ) ]
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

def __main__():
    parser = optparse.OptionParser()
    parser.add_option( '-o', '--output', dest='output', help='The name of the output file' )
    parser.add_option( '-1', '--input1', dest='input1', help='The name of the first input file' )
    parser.add_option( '-2', '--input2', dest='input2', help='The name of the second input file' )
    parser.add_option( '-g', '--hinge', dest='hinge', help='The "hinge" to use (the value to compare)' )
    parser.add_option( '-c', '--columns', dest='columns', help='The columns to include in the output file' )
    parser.add_option( '-f', '--fill_options_file', dest='fill_options_file', default=None, help='The file specifying the fill value to use' )
    (options, args) = parser.parse_args()
    hinge = int( options.hinge )
    cols = [ int( c ) for c in str( options.columns ).split( ',' ) if int( c ) > hinge ]
    inputs = [ options.input1, options.input2 ]
    if options.fill_options_file == 'None':
        inputs.extend( args )
    elif len( args ) > 0:
        inputs.extend( args )
    fill_options = None
    if options.fill_options_file != 'None' and options.fill_options_file is not None:
        try:
            if simplejson is None:
                raise simplejson_exception
            fill_options = Bunch( **stringify_dictionary_keys( simplejson.load( open( options.fill_options_file ) ) ) )
        except Exception, e:
            print 'Warning: Ignoring fill options due to simplejson error (%s).' % e
    if fill_options is None:
        fill_options = Bunch()
    if 'file1_columns' not in fill_options:
        fill_options.file1_columns = None
    if fill_options and fill_options.file1_columns:
        fill_empty = {}
        for col in cols:
            fill_empty[ col ] = fill_options.file1_columns[ col - 1 ]
    else:
        fill_empty = None
    assert len( cols ) > 0, 'You need to select at least one column in addition to the hinge'
    delimiter = '\t'
    # make sure all files are sorted in same way, ascending
    tmp_input_files = []
    input_files = inputs[:]
    for in_file in input_files:
        tmp_file = tempfile.NamedTemporaryFile()
        tmp_file_name = tmp_file.name
        tmp_file.close()
        hinge_sort( in_file, tmp_file_name, hinge )
        tmp_file = open( tmp_file_name, 'rb' )
        tmp_input_files.append( tmp_file )
    # cycle through files, getting smallest line of all files one at a time
    # also have to keep track of vertical position of extra columns
    fout = file( options.output, 'w' )
    old_current = ''
    first_line = True
    current_lines = [ f.readline().rstrip( '\r\n' ) for f in tmp_input_files ]
    last_lines = ''.join( current_lines )
    last_loc = -1
    while last_lines:
        # get the "minimum" hinge, which should come first, and the file location in list
        hinges = [ delimiter.join( line.split( delimiter )[ :hinge ] ) for line in current_lines ]
        hinge_dict = {}
        for i in range( len( hinges ) ):
            if not hinge_dict.has_key( hinges[ i ] ):
                hinge_dict[ hinges[ i ] ] = i
        hinges.sort( hinge_compare )
        hinges = [ h for h in hinges if h ]
        current, loc = hinges[0], hinge_dict[ hinges[0] ]
        # first output empty columns for vertical alignment (account for "missing" files)
        # write output for leading and trailing empty columns
        # columns missing from actual file handled further below
        current_data = []
        if current != old_current:
            # fill trailing empty columns with appropriate fill value
            if not first_line:
                if last_loc < len( inputs ) - 1:
                    if not fill_empty:
                        filler = [ '' for col in range( ( len( inputs ) - last_loc - 1 ) * len( cols ) ) ]
                    else:
                        filler = [ fill_empty[ cols[ col % len( cols ) ] ] for col in range( ( len( inputs ) - last_loc - 1 ) * len( cols ) ) ]
                    fout.write( '%s%s' % ( delimiter, delimiter.join( filler ) ) )
                # insert line break before current line
                fout.write( '\n' )
            # fill leading empty columns with appropriate fill value
            if loc > 0:
                if not fill_empty:
                    current_data = [ '' for col in range( loc * len( cols ) ) ]
                else:
                    current_data = [ fill_empty[ cols[ col % len( cols ) ] ] for col in range( loc * len( cols ) ) ]
        else:
            if loc - last_loc > 1:
                if not fill_empty:
                    current_data = [ '' for col in range( ( loc - last_loc - 1 ) * len( cols ) ) ]
                else:
                    current_data = [ fill_empty[ cols[ col % len( cols ) ] ] for col in range( ( loc - last_loc - 1 ) * len( cols ) ) ]
        # now output actual data
        split_line = current_lines[ loc ].split( delimiter )
        # fill empties within actual line if appropriate
        if fill_empty:
            new_split_line = split_line[:]
            split_line = []
            for i, item in enumerate( new_split_line ):
                col = i + 1
                if not item:
                    try:
                        split_line.append( fill_empty[ i + 1 ] )
                    except KeyError:
                        split_line.append( item )
                else:
                    split_line.append( item )
        # add actual data to be output below
        if ''.join( split_line ):
            for col in cols:
                if col > hinge:
                    # if this column doesn't exist, add the appropriate filler or empty column
                    try:
                        new_item = split_line[ col - 1 ]
                    except IndexError:
                        if fill_empty:
                            new_item = fill_empty[ col ]
                        else:
                            new_item = ''
                    current_data.append( new_item )
            # grab next line for selected file
            current_lines[ loc ] = tmp_input_files[ loc ].readline().rstrip( '\r\n' )
            # write relevant data to file
            if current == old_current and current_data:
                fout.write( '%s%s' % ( delimiter, delimiter.join( current_data ) ) )
            elif current_data:
                fout.write( '%s%s%s' % ( current, delimiter, delimiter.join( current_data ) ) )
            last_lines = ''.join( current_lines )
        else:
            last_lines = None
        last_loc = loc
        old_current = current
        first_line = False
    # fill trailing empty columns for final line
    if last_loc < len( inputs ) - 1:
        if not fill_empty:
            filler = [ '' for col in range( ( len( inputs ) - last_loc - 1 ) * len( cols ) ) ]
        else:
            filler = [ fill_empty[ cols[ col % len( cols ) ] ] for col in range( ( len( inputs ) - last_loc - 1 ) * len( cols ) ) ]
        fout.write( '%s%s' % ( delimiter, delimiter.join( filler ) ) )
    fout.write( '\n' )
    fout.close()
    for f in tmp_input_files:
        os.unlink( f.name )

if __name__ == "__main__" : __main__()
