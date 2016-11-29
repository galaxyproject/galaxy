#!/usr/bin/env python
# This tool takes a tab-delimited text file as input and creates filters on columns based on certain properties.
# The tool will skip over invalid lines within the file, informing the user about the number of lines skipped.
from __future__ import division, print_function

import re
import sys
from ast import Module, parse, walk

AST_NODE_TYPE_WHITELIST = [
    'Expr', 'Load', 'Str', 'Num', 'BoolOp', 'Compare', 'And', 'Eq', 'NotEq',
    'Or', 'GtE', 'LtE', 'Lt', 'Gt', 'BinOp', 'Add', 'Div', 'Sub', 'Mult', 'Mod',
    'Pow', 'LShift', 'GShift', 'BitAnd', 'BitOr', 'BitXor', 'UnaryOp', 'Invert',
    'Not', 'NotIn', 'In', 'Is', 'IsNot', 'List', 'Index', 'Subscript',
    # Further checks
    'Name', 'Call', 'Attribute',
]


BUILTIN_AND_MATH_FUNCTIONS = 'abs|all|any|bin|chr|cmp|complex|divmod|float|hex|int|len|long|max|min|oct|ord|pow|range|reversed|round|sorted|str|sum|type|unichr|unicode|log|exp|sqrt|ceil|floor'.split('|')
STRING_AND_LIST_METHODS = [ name for name in dir('') + dir([]) if not name.startswith('_') ]
VALID_FUNCTIONS = BUILTIN_AND_MATH_FUNCTIONS + STRING_AND_LIST_METHODS


def __check_name( ast_node ):
    name = ast_node.id
    if re.match(r'^c\d+$', name):
        return True
    return name in VALID_FUNCTIONS


def __check_attribute( ast_node ):
    attribute_name = ast_node.attr
    if attribute_name not in STRING_AND_LIST_METHODS:
        return False
    return True


def __check_call( ast_node ):
    # If we are calling a function or method, it better be a math,
    # string or list function.
    ast_func = ast_node.func
    ast_func_class = ast_func.__class__.__name__
    if ast_func_class == 'Name':
        if ast_func.id not in BUILTIN_AND_MATH_FUNCTIONS:
            return False
    elif ast_func_class == 'Attribute':
        if not __check_attribute( ast_func ):
            return False
    else:
        return False

    return True


def check_expression( text ):
    """

    >>> check_expression("c1=='chr1' and c3-c2>=2000 and c6=='+'")
    True
    >>> check_expression("eval('1+1')")
    False
    >>> check_expression("import sys")
    False
    >>> check_expression("[].__str__")
    False
    >>> check_expression("__builtins__")
    False
    >>> check_expression("'x' in globals")
    False
    >>> check_expression("'x' in [1,2,3]")
    True
    >>> check_expression("c3=='chr1' and c5>5")
    True
    >>> check_expression("c3=='chr1' and d5>5")  # Invalid d5 reference
    False
    >>> check_expression("c3=='chr1' and c5>5 or exec")
    False
    >>> check_expression("type(c1) != type(1)")
    True
    >>> check_expression("c1.split(',')[1] == '1'")
    True
    >>> check_expression("exec 1")
    False
    >>> check_expression("str(c2) in [\\\"a\\\",\\\"b\\\"]")
    True
    """
    try:
        module = parse( text )
    except SyntaxError:
        return False

    if not isinstance(module, Module):
        return False
    statements = module.body
    if not len( statements ) == 1:
        return False
    expression = statements[0]
    if expression.__class__.__name__ != 'Expr':
        return False

    for ast_node in walk( expression ):
        ast_node_class = ast_node.__class__.__name__

        # Toss out everything that is not a "simple" expression,
        # imports, error handling, etc...
        if ast_node_class not in AST_NODE_TYPE_WHITELIST:
            return False

        # White-list more potentially dangerous types AST elements.
        if ast_node_class == 'Name':
            # In order to prevent loading 'exec', 'eval', etc...
            # put string restriction on names allowed.
            if not __check_name( ast_node ):
                return False
        # Check only valid, white-listed functions are called.
        elif ast_node_class == 'Call':
            if not __check_call( ast_node ):
                return False
        # Check only valid, white-listed attributes are accessed
        elif ast_node_class == 'Attribute':
            if not __check_attribute( ast_node ):
                return False

    return True


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
    assert sys.argv[5]  # check to see that the column types variable isn't null
    in_column_types = sys.argv[5].split( ',' )
except:
    stop_err( "Data does not appear to be tabular.  This tool can only be used with tab-delimited data." )
num_header_lines = int( sys.argv[6] )

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
    '__ob__': '[',
    '__cb__': ']',
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

if not check_expression(cond_text):
    stop_err( "Illegal/invalid in condition '%s'" % ( cond_text ) )

# Work out which columns are used in the filter (save using 1 based counting)
used_cols = sorted(set(int(match.group()[1:])
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
        # If we don't use this column, don't cast it.
        # Otherwise we get errors on things like optional integer columns.
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
for i, line in enumerate( open( in_fname ) ):
    total_lines += 1
    line = line.rstrip( '\\r\\n' )

    if i < num_header_lines:
        lines_kept += 1
        print( line, file=out )
        continue

    if not line or line.startswith( '#' ):
        skipped_lines += 1
        continue
    try:
        %s
        %s
        if %s:
            lines_kept += 1
            print( line, file=out )
    except:
        invalid_lines += 1
        if not invalid_line:
            first_invalid_line = i + 1
            invalid_line = line
''' % ( assign, wrap, cond_text )
valid_filter = True
try:
    exec(code)
except Exception as e:
    out.close()
    if str( e ).startswith( 'invalid syntax' ):
        valid_filter = False
        stop_err( 'Filter condition "%s" likely invalid. See tool tips, syntax and examples.' % cond_text )
    else:
        stop_err( str( e ) )

if valid_filter:
    out.close()
    valid_lines = total_lines - skipped_lines
    print('Filtering with %s, ' % cond_text)
    if valid_lines > 0:
        print('kept %4.2f%% of %d valid lines (%d total lines).' % ( 100.0 * lines_kept / valid_lines, valid_lines, total_lines ))
    else:
        print('Possible invalid filter condition "%s" or non-existent column referenced. See tool tips, syntax and examples.' % cond_text)
    if invalid_lines:
        print('Skipped %d invalid line(s) starting at line #%d: "%s"' % ( invalid_lines, first_invalid_line, invalid_line ))
    if skipped_lines:
        print('Skipped %i comment (starting with #) or blank line(s)' % skipped_lines)
