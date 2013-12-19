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

from ast import parse, Module, walk

# Older py compatibility
try:
    set()
except:
    from sets import Set as set

AST_NODE_TYPE_WHITELIST = [
    'Expr',    'Load',
    'Str',     'Num',    'BoolOp',
    'Compare', 'And',    'Eq',
    'NotEq',   'Or',     'GtE',
    'LtE',     'Lt',     'Gt',
    'BinOp',   'Add',    'Div',
    'Sub',     'Mult',   'Mod',
    'Pow',     'LShift', 'GShift',
    'BitAnd',  'BitOr',  'BitXor',
    'UnaryOp', 'Invert', 'Not',
    'NotIn',   'In',     'Is',
    'IsNot',   'List',
    'Index',   'Subscript',
    # Further checks
    'Name',    'Call',    'Attribute',
]


BUILTIN_AND_MATH_FUNCTIONS = 'abs|all|any|bin|chr|cmp|complex|divmod|float|hex|int|len|long|max|min|oct|ord|pow|range|reversed|round|sorted|str|sum|type|unichr|unicode|log|exp|sqrt|ceil|floor'.split('|')
STRING_AND_LIST_METHODS = [ name for name in dir('') + dir([]) if not name.startswith('_') ]
VALID_FUNCTIONS = BUILTIN_AND_MATH_FUNCTIONS + STRING_AND_LIST_METHODS


def __check_name( ast_node ):
    name = ast_node.id
    if re.match(r'^c\d+$', name):
        return True
    elif name == "codes":
        return True
    else:
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

    if not check_expression( cond_text ):
        stop_err( "Illegal/invalid in condition '%s'" % ( cond_text ) )

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
