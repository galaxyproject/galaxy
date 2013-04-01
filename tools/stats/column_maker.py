#!/usr/bin/env python
# This tool takes a tab-delimited textfile as input and creates another column in the file which is the result of
# a computation performed on every row in the original file.  The tool will skip over invalid lines within the file,
# informing the user about the number of lines skipped.

import sys, re
# These functions may be used in compute expression:
from math import log,exp,sqrt,ceil,floor


assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

inp_file = sys.argv[1]
out_file = sys.argv[2]
expr = sys.argv[3]
round_result = sys.argv[4]
try:
    in_columns = int( sys.argv[5] )
except:
    stop_err( "Missing or invalid 'columns' metadata value, click the pencil icon in the history item and select the Auto-detect option to correct it.  This tool can only be used with tab-delimited data." )
if in_columns < 2:
    # To be considered tabular, data must fulfill requirements of the sniff.is_column_based() method.
    stop_err( "Missing or invalid 'columns' metadata value, click the pencil icon in the history item and select the Auto-detect option to correct it.  This tool can only be used with tab-delimited data." )
try:
    in_column_types = sys.argv[6].split( ',' )
except:
    stop_err( "Missing or invalid 'column_types' metadata value, click the pencil icon in the history item and select the Auto-detect option to correct it.  This tool can only be used with tab-delimited data." )
if len( in_column_types ) != in_columns:
    stop_err( "The 'columns' metadata setting does not conform to the 'column_types' metadata setting, click the pencil icon in the history item and select the Auto-detect option to correct it.  This tool can only be used with tab-delimited data." )
    
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
    expr = expr.replace( key, value )

operators = 'is|not|or|and'
builtin_and_math_functions = 'abs|all|any|bin|chr|cmp|complex|divmod|float|hex|int|len|long|max|min|oct|ord|pow|range|reversed|round|sorted|str|sum|type|unichr|unicode|log|exp|sqrt|ceil|floor'
string_and_list_methods = [ name for name in dir('') + dir([]) if not name.startswith('_') ]
whitelist = "^([c0-9\+\-\*\/\(\)\.\'\"><=,:! ]|%s|%s|%s)*$" % (operators, builtin_and_math_functions, '|'.join(string_and_list_methods))
if not re.compile(whitelist).match(expr):
    stop_err("Invalid expression")

# Prepare the column variable names and wrappers for column data types
cols, type_casts = [], []
for col in range( 1, in_columns + 1 ):
    col_name = "c%d" % col
    cols.append( col_name )
    col_type = in_column_types[ col - 1 ].strip()
    if round_result == 'no' and col_type == 'int':
        col_type = 'float'
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
out = open( out_file, 'wt' )

# Read input file, skipping invalid lines, and perform computation that will result in a new column
code = '''
for i, line in enumerate( file( inp_file ) ):
    total_lines += 1
    line = line.rstrip( '\\r\\n' )
    if not line or line.startswith( '#' ):
        skipped_lines += 1
        if not invalid_line:
            first_invalid_line = i + 1
            invalid_line = line
        continue
    try:
        %s
        %s
        new_val = %s
        if round_result == "yes":
            new_val = int( round( new_val ) )
        new_line = line + '\\t' + str( new_val )
        print >> out, new_line
        lines_kept += 1
    except:
        skipped_lines += 1
        if not invalid_line:
            first_invalid_line = i + 1
            invalid_line = line
''' % ( assign, wrap, expr )

valid_expr = True
try:
    exec code
except Exception, e:
    out.close()
    if str( e ).startswith( 'invalid syntax' ):
        valid_expr = False
        stop_err( 'Expression "%s" likely invalid. See tool tips, syntax and examples.' % expr )
    else:
        stop_err( str( e ) )

if valid_expr:
    out.close()
    valid_lines = total_lines - skipped_lines
    print 'Creating column %d with expression %s' % ( in_columns + 1, expr )
    if valid_lines > 0:
        print 'kept %4.2f%% of %d lines.' % ( 100.0*lines_kept/valid_lines, total_lines )
    else:
        print 'Possible invalid expression "%s" or non-existent column referenced. See tool tips, syntax and examples.' % expr
    if skipped_lines > 0:
        print 'Skipped %d invalid lines starting at line #%d: "%s"' % ( skipped_lines, first_invalid_line, invalid_line )
