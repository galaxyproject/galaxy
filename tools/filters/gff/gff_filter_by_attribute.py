#!/usr/bin/env python
# This tool takes a gff file as input and creates filters on attributes based on certain properties.
# The tool will skip over invalid lines within the file, informing the user about the number of lines skipped.
# TODO: much of this code is copied from the Filter1 tool (filtering.py in tools/stats/). The commonalities should be 
# abstracted and leveraged in each filtering tool.

from __future__ import division
import sys, re, os.path

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
attribute_type = sys.argv[3]
attribute_name = sys.argv[4]
cond_text = sys.argv[5]

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
    
# Condition text is 'attribute meets condition.'
cond_text = attribute_name + cond_text
    
# Attempt to determine if the condition includes executable stuff and, if so, exit
secured = dir()
operands = get_operands(cond_text)
for operand in operands:
    try:
        check = int( operand )
    except:
        if operand in secured:
            stop_err( "Illegal value '%s' in condition '%s'" % ( operand, cond_text ) )
            
# Set up assignment.
assignment = "%s = attributes.get('%s', None)" % ( attribute_name, attribute_name )
            
# Set up type casting based on attribute type.
type_cast = "%s = %s(%s)" % ( attribute_name, attribute_type, attribute_name)

# Stats 
skipped_lines = 0
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
        if not invalid_line:
            first_invalid_line = i + 1
            invalid_line = line
        continue
    try:
        # GTF format: chrom source, name, chromStart, chromEnd, score, strand, frame, attributes.
        # Attributes format: name1 "value1" ; name2 "value2" ; ...
        elems = line.split( '\t' )
        attributes_list = elems[8].split(";")
        attributes = {}
        for name_value_pair in attributes_list:
            pair = name_value_pair.strip().split(" ")
            if pair == '':
                continue
            name = pair[0].strip()
            if name == '':
                continue
            # Need to strip double quote from values
            value = pair[1].strip(" \\"")
            attributes[name] = value
        %s
        if %s:
            %s
            if %s:
                lines_kept += 1
                print >> out, line
    except Exception, e:
        skipped_lines += 1
        if not invalid_line:
            first_invalid_line = i + 1
            invalid_line = line
''' % ( assignment, attribute_name, type_cast, cond_text )


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
