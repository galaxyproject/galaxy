#!/usr/bin/env python
# This tool takes a tab-delimited text file as input and creates filters on columns based on certain properties.
# The tool will skip over invalid lines within the file, informing the user about the number of lines skipped.

from __future__ import division
import sys, re, os.path
from galaxy import eggs

# Older py compatibility
try:
    set()
except:
    from sets import Set as set

assert sys.version_info[:2] >= ( 2, 4 )

def get_operands( filter_condition ):
    # Note that the order of all_operators is important
    items_to_strip = ['+', '-', '**', '*', '//', '/', '%', '<<', '>>', '&', '|', '^', '~', '<=', '<', '>=', '>', '==', '!=', '<>', ' and ', ' or ', ' not ', ' is ', ' is not ', ' in ', ' not in ']
    for item in items_to_strip:
        if filter_condition.find( item ) >= 0:
            filter_condition = filter_condition.replace( item, ' ' )
    operands = set( filter_condition.split( ' ' ) )
    return operands

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

in_fname = sys.argv[1]
out_fname = sys.argv[2]
cond_text = sys.argv[3]
try:
    in_columns = int( sys.argv[4] )
    assert sys.argv[5]  #check to see that the column types variable isn't null
    in_column_types = sys.argv[5].split( ',' )
except:
    stop_err( "Data does not appear to be tabular.  This tool can only be used with tab-delimited data." )

# Unescape if input has been escaped
mapped_str = {
    '__lt__': '<',
    '__le__': '<=',
    '__eq__': '==',
    '__ne__': '!=',
    '__gt__': '>',
    '__ge__': '>=',
    '__sq__': '\'',
    '__dq__': '"',
}
for key, value in mapped_str.items():
    cond_text = cond_text.replace( key, value )
    
# Attempt to determine if the condition includes executable stuff and, if so, exit
secured = dir()
operands = get_operands(cond_text)
for operand in operands:
    try:
        check = int( operand )
    except:
        if operand in secured:
            stop_err( "Illegal value '%s' in condition '%s'" % ( operand, cond_text ) )

# Work out which columns are used in the filter (save using 1 based counting)
used_cols = sorted(set(int(match.group()[1:]) \
                   for match in re.finditer('c(\d)+', cond_text))) 
largest_col_index = max(used_cols)

# Prepare the column variable names and wrappers for column data types. Only 
# cast columns used in the filter.
cols, type_casts = [], []
for col in range( 1, largest_col_index + 1 ):
    col_name = "c%d" % col
    cols.append( col_name )
    col_type = in_column_types[ col - 1 ]
    if col in used_cols:
        type_cast = "%s(%s)" % ( col_type, col_name )
    else:
        #If we don't use this column, don't cast it.
        #Otherwise we get errors on things like optional integer columns.
        type_cast = col_name
    type_casts.append( type_cast )
 
col_str = ', '.join( cols )    # 'c1, c2, c3, c4'
type_cast_str = ', '.join( type_casts )  # 'str(c1), int(c2), int(c3), str(c4)'
assign = "%s, = line.split( '\\t' )[:%i]" % ( col_str, largest_col_index )
wrap = "%s = %s" % ( col_str, type_cast_str )
skipped_lines = 0
invalid_lines = 0
first_invalid_line = 0
invalid_line = None
lines_kept = 0
total_lines = 0
out = open( out_fname, 'wt' )
    
# Read and filter input file, skipping invalid lines
code = '''
for i, line in enumerate( file( in_fname ) ):
    total_lines += 1
    line = line.rstrip( '\\r\\n' )
    if not line or line.startswith( '#' ):
        skipped_lines += 1
        continue
    try:
        %s
        %s
        if %s:
            lines_kept += 1
            print >> out, line
    except:
        invalid_lines += 1
        if not invalid_line:
            first_invalid_line = i + 1
            invalid_line = line
''' % ( assign, wrap, cond_text )

valid_filter = True
try:
    exec code
except Exception, e:
    out.close()
    if str( e ).startswith( 'invalid syntax' ):
        valid_filter = False
        stop_err( 'Filter condition "%s" likely invalid. See tool tips, syntax and examples.' % cond_text )
    else:
        stop_err( str( e ) )

if valid_filter:
    out.close()
    valid_lines = total_lines - skipped_lines
    print 'Filtering with %s, ' % cond_text
    if valid_lines > 0:
        print 'kept %4.2f%% of %d valid lines (%d total lines).' % ( 100.0*lines_kept/valid_lines, valid_lines, total_lines )
    else:
        print 'Possible invalid filter condition "%s" or non-existent column referenced. See tool tips, syntax and examples.' % cond_text
    if invalid_lines:
        print 'Skipped %d invalid line(s) starting at line #%d: "%s"' % ( invalid_lines, first_invalid_line, invalid_line )
    if skipped_lines:
        print 'Skipped %i comment (starting with #) or blank line(s)' % skipped_lines
