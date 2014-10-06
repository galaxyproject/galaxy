#!/usr/bin/env python
# This tool takes a gff file as input and creates filters on attributes based on certain properties.
# The tool will skip over invalid lines within the file, informing the user about the number of lines skipped.
# TODO: much of this code is copied from the Filter1 tool (filtering.py in tools/stats/). The commonalities should be
# abstracted and leveraged in each filtering tool.

from __future__ import division
import sys
from galaxy import eggs
from galaxy.util.json import dumps, loads

# Older py compatibility
try:
    set()
except:
    from sets import Set as set

assert sys.version_info[:2] >= ( 2, 4 )

#
# Helper functions.
#

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

def check_for_executable( text, description='' ):
    # Attempt to determine if the condition includes executable stuff and, if so, exit.
    secured = dir()
    operands = get_operands( text )
    for operand in operands:
        try:
            check = int( operand )
        except:
            if operand in secured:
                stop_err( "Illegal value '%s' in %s '%s'" % ( operand, description, text ) )

#
# Process inputs.
#

in_fname = sys.argv[1]
out_fname = sys.argv[2]
cond_text = sys.argv[3]
attribute_types = loads( sys.argv[4] )

# Convert types from str to type objects.
for name, a_type in attribute_types.items():
    check_for_executable(a_type)
    attribute_types[ name ] = eval( a_type )

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

# Attempt to determine if the condition includes executable stuff and, if so, exit.
check_for_executable( cond_text, 'condition')

# Prepare the column variable names and wrappers for column data types. Only
# prepare columns up to largest column in condition.
attrs, type_casts = [], []
for name, attr_type in attribute_types.items():
    attrs.append( name )
    type_cast = "get_value('%(name)s', attribute_types['%(name)s'], attribute_values)" % ( {'name': name} )
    type_casts.append( type_cast )

attr_str = ', '.join( attrs )    # 'c1, c2, c3, c4'
type_cast_str = ', '.join( type_casts )  # 'str(c1), int(c2), int(c3), str(c4)'
wrap = "%s = %s" % ( attr_str, type_cast_str )

# Stats
skipped_lines = 0
first_invalid_line = 0
invalid_line = None
lines_kept = 0
total_lines = 0
out = open( out_fname, 'wt' )

# Helper function to safely get and type cast a value in a dict.
def get_value(name, a_type, values_dict):
    if name in values_dict:
        return (a_type)(values_dict[ name ])
    else:
        return None

# Read and filter input file, skipping invalid lines
code = '''
for i, line in enumerate( file( in_fname ) ):
    total_lines += 1
    line = line.rstrip( '\\r\\n' )
    if not line or line.startswith( '#' ):
        skipped_lines += 1
        if not invalid_line:
            first_invalid_line = i + 1
            invalid_line = line
        continue
    try:
        # Place attribute values into variables with attribute
        # name; type casting is done as well.
        elems = line.split( '\t' )
        attribute_values = {}
        for name_value_pair in elems[8].split(";"):
            pair = name_value_pair.strip().split(" ")
            if pair == '':
                continue
            name = pair[0].strip()
            if name == '':
                continue
            # Need to strip double quote from value and typecast.
            attribute_values[name] = pair[1].strip(" \\"")
        %s
        if %s:
            lines_kept += 1
            print >> out, line
    except Exception, e:
        print e
        skipped_lines += 1
        if not invalid_line:
            first_invalid_line = i + 1
            invalid_line = line
''' % ( wrap, cond_text )

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
    print 'Filtering with %s, ' % ( cond_text )
    if valid_lines > 0:
        print 'kept %4.2f%% of %d lines.' % ( 100.0*lines_kept/valid_lines, total_lines )
    else:
        print 'Possible invalid filter condition "%s" or non-existent column referenced. See tool tips, syntax and examples.' % cond_text
    if skipped_lines > 0:
        print 'Skipped %d invalid lines starting at line #%d: "%s"' % ( skipped_lines, first_invalid_line, invalid_line )
