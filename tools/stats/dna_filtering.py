#!/usr/bin/env python

"""
This tool takes a tab-delimited text file as input and creates filters on columns based on certain properties. The tool will skip over invalid lines within the file, informing the user about the number of lines skipped.

usage: %prog [options]
    -i, --input=i: tabular input file
    -o, --output=o: filtered output file
    -c, --cond=c: conditions to filter on
    -n, --n_handling=n: how to handle N and X
    -l, --columns=l: columns 
    -t, --col_types=t: column types    

"""

#from __future__ import division
import os.path, re, string, string, sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

# Older py compatibility
try:
    set()
except:
    from sets import Set as set

#assert sys.version_info[:2] >= ( 2, 4 )

def get_operands( filter_condition ):
    # Note that the order of all_operators is important
    items_to_strip = [ '==', '!=', ' and ', ' or ' ]
    for item in items_to_strip:
        if filter_condition.find( item ) >= 0:
            filter_condition = filter_condition.replace( item, ' ' )
    operands = set( filter_condition.split( ' ' ) )
    return operands

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def __main__():
    #Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    input = options.input
    output = options.output
    cond = options.cond
    n_handling = options.n_handling
    columns = options.columns
    col_types = options.col_types

    try:
        in_columns = int( columns )
        assert col_types  #check to see that the column types variable isn't null
        in_column_types = col_types.split( ',' )
    except:
        stop_err( "Data does not appear to be tabular.  This tool can only be used with tab-delimited data." )

    # Unescape if input has been escaped
    cond_text = cond.replace( '__eq__', '==' ).replace( '__ne__', '!=' ).replace( '__sq__', "'" )
    orig_cond_text = cond_text
    # Expand to allow for DNA codes
    dot_letters = [ letter for letter in string.uppercase if letter not in \
                   [ 'A', 'C', 'G', 'T', 'U', 'B', 'D', 'H', 'K', 'M', 'N', 'R', 'S', 'V', 'W', 'X', 'Y' ] ]
    dot_letters.append( '.' )
    codes = {'A': [ 'A', 'D', 'H', 'M', 'R', 'V', 'W' ],
             'C': [ 'C', 'B', 'H', 'M', 'S', 'V', 'Y' ],
             'G': [ 'G', 'B', 'D', 'K', 'R', 'S', 'V' ],
             'T': [ 'T', 'U', 'B', 'D', 'H', 'K', 'W', 'Y' ],
             'U': [ 'T', 'U', 'B', 'D', 'H', 'K', 'W', 'Y' ],
             'K': [ 'G', 'T', 'U', 'B', 'D', 'H', 'K', 'R', 'S', 'V', 'W', 'Y' ],
             'M': [ 'A', 'C', 'B', 'D', 'H', 'M', 'R', 'S', 'V', 'W', 'Y' ],
             'R': [ 'A', 'G', 'B', 'D', 'H', 'K', 'M', 'R', 'S', 'V', 'W' ],
             'Y': [ 'C', 'T', 'U', 'B', 'D', 'H', 'K', 'M', 'S', 'V', 'W', 'Y' ],
             'S': [ 'C', 'G', 'B', 'D', 'H', 'K', 'M', 'R', 'S', 'V', 'Y' ],
             'W': [ 'A', 'T', 'U', 'B', 'D', 'H', 'K', 'M', 'R', 'V', 'W', 'Y' ],
             'B': [ 'C', 'G', 'T', 'U', 'B', 'D', 'H', 'K', 'M', 'R', 'S', 'V', 'W', 'Y' ],
             'V': [ 'A', 'C', 'G', 'B', 'D', 'H', 'K', 'M', 'R', 'S', 'V', 'W' ],
             'H': [ 'A', 'C', 'T', 'U', 'B', 'D', 'H', 'K', 'M', 'R', 'S', 'V', 'W', 'Y' ],
             'D': [ 'A', 'G', 'T', 'U', 'B', 'D', 'H', 'K', 'M', 'R', 'S', 'V', 'W', 'Y' ],
             '.': dot_letters,
             '-': [ '-' ]}
    # Add handling for N and X
    if n_handling == "all":
        codes[ 'N' ] = [ 'A', 'C', 'G', 'T', 'U', 'B', 'D', 'H', 'K', 'M', 'N', 'R', 'S', 'V', 'W', 'X', 'Y' ]
        codes[ 'X' ] = [ 'A', 'C', 'G', 'T', 'U', 'B', 'D', 'H', 'K', 'M', 'N', 'R', 'S', 'V', 'W', 'X', 'Y' ]
        for code in codes.keys():
            if code != '.' and code != '-':
                codes[code].append( 'N' )
                codes[code].append( 'X' )
    else:
        codes[ 'N' ] = dot_letters
        codes[ 'X' ] = dot_letters
        codes[ '.' ].extend( [ 'N', 'X' ] )
    # Expand conditions to allow for DNA codes
    try:
        match_replace = {}
        pat = re.compile( 'c\d+\s*[!=]=\s*[\w\d"\'+-.]+' )
        matches = pat.findall( cond_text )
        for match in matches:
            if match.find( 'chr' ) >= 0 or match.find( 'scaffold' ) >= 0 or match.find( '+' ) >= 0:
                if match.find( '==' ) >= 0:
                    match_parts = match.split( '==' )
                elif match.find( '!=' ) >= 0:
                    match_parts = match.split( '!=' )
                else:
                    raise Exception, "The operators '==' and '!=' were not found."
                left = match_parts[0].strip()
                right = match_parts[1].strip()
                new_match = "(%s)" % ( match )
            elif match.find( '==' ) > 0:
                match_parts = match.split( '==' )
                left = match_parts[0].strip()
                right = match_parts[1].strip()
                new_match = '(%s in codes[%s] and %s in codes[%s])' % ( left, right, right, left )
            elif match.find( '!=' ) > 0 :
                match_parts = match.split( '!=' )
                left = match_parts[0].strip()
                right = match_parts[1].strip()
                new_match = '(%s not in codes[%s] or %s not in codes[%s])' % ( left, right, right, left )
            else:
                raise Exception, "The operators '==' and '!=' were not found." 
            assert left.startswith( 'c' ), 'The column names should start with c (lowercase)'
            if right.find( "'" ) >= 0 or right.find( '"' ) >= 0:
                test = right.replace( "'", '' ).replace( '"', '' )
                assert test in string.uppercase or test.find( '+' ) >= 0 or test.find( '.' ) >= 0 or test.find( '-' ) >= 0\
                        or test.startswith( 'chr' ) or test.startswith( 'scaffold' ), \
                        'The value to search for should be a valid base, code, plus sign, chromosome (like "chr1") or scaffold (like "scaffold5"). ' \
                        'Use the general filter tool to filter on anything else first'
            else:
                assert right.startswith( 'c' ), 'The column names should start with c (lowercase)'
            match_replace[match] = new_match
        if len( match_replace.keys() ) == 0:
            raise Exception, 'There do not appear to be any valid conditions'
        for match in match_replace.keys():
            cond_text = cond_text.replace( match, match_replace[match] )
    except Exception, e:
        stop_err( "At least one of your conditions is invalid. Make sure to use only '!=' or '==', valid column numbers, and valid base values.\n" + str(e) )

    # Attempt to determine if the condition includes executable stuff and, if so, exit
    secured = dir()
    operands = get_operands( cond_text )
    for operand in operands:
        try:
            check = int( operand )
        except:
            if operand in secured:
                stop_err( "Illegal value '%s' in condition '%s'" % ( operand, cond_text ) )

    # Prepare the column variable names and wrappers for column data types
    cols, type_casts = [], []
    for col in range( 1, in_columns + 1 ):
        col_name = "c%d" % col
        cols.append( col_name )
        col_type = in_column_types[ col - 1 ]
        type_cast = "%s(%s)" % ( col_type, col_name )
        type_casts.append( type_cast )

    col_str = ', '.join( cols )    # 'c1, c2, c3, c4'
    type_cast_str = ', '.join( type_casts )  # 'str(c1), int(c2), int(c3), str(c4)'
    assign = "%s = line.split( '\\t' )" % col_str
    wrap = "%s = %s" % ( col_str, type_cast_str )
    skipped_lines = 0
    first_invalid_line = 0
    invalid_line = None
    lines_kept = 0
    total_lines = 0
    out = open( output, 'wt' )
    # Read and filter input file, skipping invalid lines
    code = '''
for i, line in enumerate( file( input ) ):
    total_lines += 1
    line = line.rstrip( '\\r\\n' )
    if not line or line.startswith( '#' ):
        skipped_lines += 1
        if not invalid_line:
            first_invalid_line = i + 1
            invalid_line = line
        continue
    try:
        %s = line.split( '\\t' )
        %s = %s
        if %s:
            lines_kept += 1
            print >> out, line
    except Exception, e:
        skipped_lines += 1
        if not invalid_line:
            first_invalid_line = i + 1
            invalid_line = line
''' % ( col_str, col_str, type_cast_str, cond_text )

    valid_filter = True
    try:
        exec code
    except Exception, e:
        out.close()
        if str( e ).startswith( 'invalid syntax' ):
            valid_filter = False
            stop_err( 'Filter condition "%s" likely invalid. See tool tips, syntax and examples.' % orig_cond_text + ' '+str(e))
        else:
            stop_err( str( e ) )

    if valid_filter:
        out.close()
        valid_lines = total_lines - skipped_lines
        print 'Filtering with %s, ' % orig_cond_text
        if valid_lines > 0:
            print 'kept %4.2f%% of %d lines.' % ( 100.0*lines_kept/valid_lines, total_lines )
        else:
            print 'Possible invalid filter condition "%s" or non-existent column referenced. See tool tips, syntax and examples.' % orig_cond_text
        if skipped_lines > 0:
            print 'Skipped %d invalid lines starting at line #%d: "%s"' % ( skipped_lines, first_invalid_line, invalid_line )
    
if __name__ == "__main__" : __main__()
