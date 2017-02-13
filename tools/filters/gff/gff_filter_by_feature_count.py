#!/usr/bin/env python
"""
Filter a gff file using a criterion based on feature counts for a transcript.

Usage:
%prog input_name output_name feature_name condition
"""
from __future__ import print_function

import sys

from ast import Module, parse, walk

from bx.intervals.io import GenomicInterval

from galaxy.datatypes.util.gff_util import GFFReaderWrapper

AST_NODE_TYPE_WHITELIST = [
    'Expr', 'Load', 'Str', 'Num', 'BoolOp', 'Compare', 'And', 'Eq', 'NotEq',
    'Or', 'GtE', 'LtE', 'Lt', 'Gt', 'BinOp', 'Add', 'Div', 'Sub', 'Mult', 'Mod',
    'Pow', 'LShift', 'GShift', 'BitAnd', 'BitOr', 'BitXor', 'UnaryOp', 'Invert',
    'Not', 'NotIn', 'In', 'Is', 'IsNot', 'List', 'Index', 'Subscript',
    'Name',
]


BUILTIN_AND_MATH_FUNCTIONS = 'abs|all|any|bin|chr|cmp|complex|divmod|float|hex|int|len|long|max|min|oct|ord|pow|range|reversed|round|sorted|str|sum|type|unichr|unicode|log|exp|sqrt|ceil|floor'.split('|')
STRING_AND_LIST_METHODS = [ name for name in dir('') + dir([]) if not name.startswith('_') ]
VALID_FUNCTIONS = BUILTIN_AND_MATH_FUNCTIONS + STRING_AND_LIST_METHODS
# Name blacklist isn't strictly needed - but provides extra peace of mind.
NAME_BLACKLIST = ["exec", "eval", "globals", "locals", "__import__", "__builtins__"]


def __check_name( ast_node ):
    name = ast_node.id
    return name not in NAME_BLACKLIST


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
    >>> check_expression("c3=='chr1' and d5>5")
    True
    >>> check_expression("c3=='chr1' and c5>5 or exec")
    False
    >>> check_expression("type(c1) != type(1)")
    False
    >>> check_expression("c1.split(',')[1] == '1'")
    False
    >>> check_expression("exec 1")
    False
    >>> check_expression("str(c2) in [\\\"a\\\",\\\"b\\\"]")
    False
    >>> check_expression("__import__('os').system('touch /tmp/OOPS')")
    False
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

        if ast_node_class == "Name" and not __check_name(ast_node):
            return False

    return True


# Valid operators, ordered so that complex operators (e.g. '>=') are
# recognized before simple operators (e.g. '>')
ops = [
    '>=',
    '<=',
    '<',
    '>',
    '==',
    '!='
]

# Escape sequences for valid operators.
mapped_ops = {
    '__ge__': ops[0],
    '__le__': ops[1],
    '__lt__': ops[2],
    '__gt__': ops[3],
    '__eq__': ops[4],
    '__ne__': ops[5],
}


def __main__():
    # Get args.
    input_name = sys.argv[1]
    output_name = sys.argv[2]
    feature_name = sys.argv[3]
    condition = sys.argv[4]

    # Unescape operations in condition str.
    for key, value in mapped_ops.items():
        condition = condition.replace( key, value )

    # Error checking: condition should be of the form <operator><number>
    for op in ops:
        if op in condition:
            empty, number_str = condition.split( op )
            try:
                number = float( number_str )
            except:
                number = None
            if empty != "" or not number:
                print("Invalid condition: %s, cannot filter." % condition, file=sys.stderr)
                return
            break

    # Do filtering.
    kept_features = 0
    skipped_lines = 0
    first_skipped_line = 0
    out = open( output_name, 'w' )
    for i, feature in enumerate( GFFReaderWrapper( open( input_name ) ) ):
        if not isinstance( feature, GenomicInterval ):
            continue
        count = 0
        for interval in feature.intervals:
            if interval.feature == feature_name:
                count += 1
        eval_text = '%s %s' % ( count, condition )
        if not check_expression(eval_text):
            print("Invalid condition: %s, cannot filter." % condition, file=sys.stderr)
            sys.exit(1)

        if eval(eval_text):
            # Keep feature.
            for interval in feature.intervals:
                out.write( "\t".join(interval.fields) + '\n' )
            kept_features += 1

    # Needed because i is 0-based but want to display stats using 1-based.
    i += 1

    # Clean up.
    out.close()
    info_msg = "%i of %i features kept (%.2f%%) using condition %s.  " % \
        ( kept_features, i, float(kept_features) / i * 100.0, feature_name + condition )
    if skipped_lines > 0:
        info_msg += "Skipped %d blank/comment/invalid lines starting with line #%d." % ( skipped_lines, first_skipped_line )
    print(info_msg)


if __name__ == "__main__":
    __main__()
