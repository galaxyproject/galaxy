#!/usr/bin/env python
# This tool takes a gff file as input and creates filters on attributes based on certain properties.
# The tool will skip over invalid lines within the file, informing the user about the number of lines skipped.
# TODO: much of this code is copied from the Filter1 tool (filtering.py in tools/stats/). The commonalities should be
# abstracted and leveraged in each filtering tool.
from __future__ import (
    division,
    print_function,
)

import sys
from ast import (
    Module,
    parse,
    walk,
)
from json import loads

AST_NODE_TYPE_WHITELIST = [
    "Expr",
    "Load",
    "Str",
    "Num",
    "BoolOp",
    "Compare",
    "And",
    "Eq",
    "NotEq",
    "Or",
    "GtE",
    "LtE",
    "Lt",
    "Gt",
    "BinOp",
    "Add",
    "Div",
    "Sub",
    "Mult",
    "Mod",
    "Pow",
    "LShift",
    "GShift",
    "BitAnd",
    "BitOr",
    "BitXor",
    "UnaryOp",
    "Invert",
    "Not",
    "NotIn",
    "In",
    "Is",
    "IsNot",
    "List",
    "Index",
    "Subscript",
    "Name",
]


BUILTIN_AND_MATH_FUNCTIONS = "abs|all|any|bin|chr|cmp|complex|divmod|float|hex|int|len|long|max|min|oct|ord|pow|range|reversed|round|sorted|str|sum|type|unichr|unicode|log|exp|sqrt|ceil|floor".split(
    "|"
)
STRING_AND_LIST_METHODS = [name for name in dir("") + dir([]) if not name.startswith("_")]
VALID_FUNCTIONS = BUILTIN_AND_MATH_FUNCTIONS + STRING_AND_LIST_METHODS
# Name blacklist isn't strictly needed - but provides extra peace of mind.
NAME_BLACKLIST = ["exec", "eval", "globals", "locals", "__import__", "__builtins__"]


def __check_name(ast_node):
    name = ast_node.id
    return name not in NAME_BLACKLIST


def check_simple_name(text):
    """

    >>> check_simple_name("col_name")
    True
    >>> check_simple_name("c1=='chr1' and c3-c2>=2000 and c6=='+'")
    False
    >>> check_simple_name("eval('1+1')")
    False
    >>> check_simple_name("import sys")
    False
    >>> check_simple_name("[].__str__")
    False
    >>> check_simple_name("__builtins__")
    False
    >>> check_simple_name("'x' in globals")
    False
    >>> check_simple_name("'x' in [1,2,3]")
    False
    >>> check_simple_name("c3=='chr1' and c5>5")
    False
    >>> check_simple_name("c3=='chr1' and d5>5")
    False
    >>> check_simple_name("c3=='chr1' and c5>5 or exec")
    False
    >>> check_simple_name("type(c1) != type(1)")
    False
    >>> check_simple_name("c1.split(',')[1] == '1'")
    False
    >>> check_simple_name("exec 1")
    False
    >>> check_simple_name("str(c2) in [\\\"a\\\",\\\"b\\\"]")
    False
    >>> check_simple_name("__import__('os').system('touch /tmp/OOPS')")
    False
    """
    try:
        module = parse(text)
    except SyntaxError:
        return False

    if not isinstance(module, Module):
        return False
    statements = module.body
    if not len(statements) == 1:
        return False
    expression = statements[0]
    if expression.__class__.__name__ != "Expr":
        return False

    for ast_node in walk(expression):
        ast_node_class = ast_node.__class__.__name__
        if ast_node_class not in ["Expr", "Name", "Load"]:
            return False

        if ast_node_class == "Name" and not __check_name(ast_node):
            return False

    return True


def check_expression(text):
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
        module = parse(text)
    except SyntaxError:
        return False

    if not isinstance(module, Module):
        return False
    statements = module.body
    if not len(statements) == 1:
        return False
    expression = statements[0]
    if expression.__class__.__name__ != "Expr":
        return False

    for ast_node in walk(expression):
        ast_node_class = ast_node.__class__.__name__

        # Toss out everything that is not a "simple" expression,
        # imports, error handling, etc...
        if ast_node_class not in AST_NODE_TYPE_WHITELIST:
            return False

        if ast_node_class == "Name" and not __check_name(ast_node):
            return False

    return True


#
# Helper functions.
#
def get_operands(filter_condition):
    # Note that the order of all_operators is important
    items_to_strip = [
        "+",
        "-",
        "**",
        "*",
        "//",
        "/",
        "%",
        "<<",
        ">>",
        "&",
        "|",
        "^",
        "~",
        "<=",
        "<",
        ">=",
        ">",
        "==",
        "!=",
        "<>",
        " and ",
        " or ",
        " not ",
        " is ",
        " is not ",
        " in ",
        " not in ",
    ]
    for item in items_to_strip:
        if filter_condition.find(item) >= 0:
            filter_condition = filter_condition.replace(item, " ")
    operands = set(filter_condition.split(" "))
    return operands


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def check_for_executable(text, description=""):
    # Attempt to determine if the condition includes executable stuff and, if so, exit.
    secured = dir()
    operands = get_operands(text)
    for operand in operands:
        try:
            int(operand)
        except ValueError:
            if operand in secured:
                stop_err("Illegal value '%s' in %s '%s'" % (operand, description, text))


#
# Process inputs.
#
in_fname = sys.argv[1]
out_fname = sys.argv[2]
cond_text = sys.argv[3]
attribute_types = loads(sys.argv[4])

# Convert types from str to type objects.
for name, a_type in attribute_types.items():
    check_for_executable(a_type)
    if not check_simple_name(a_type):
        stop_err("Problem with attribute type [%s]" % a_type)
    attribute_types[name] = eval(a_type)

# Possible (eg workflows) that user's filter contains standard
# GFF attributes which are not present in the actual file -
# and thus not in the metadata passed in by Galaxy.
# To avoid a nasty error here, add the official terms from
# the GFF3 specification (if not already defined).
# (These all start with a capital letter, which is important):
for name in [
    "ID",
    "Name",
    "Alias",
    "Parent",
    "Target",
    "Gap",
    "Derives_from",
    "Note",
    "Dbxref",
    "Ontology_term",
    "Is_circular",
]:
    attribute_types[name] = str

# Unescape if input has been escaped
mapped_str = {
    "__lt__": "<",
    "__le__": "<=",
    "__eq__": "==",
    "__ne__": "!=",
    "__gt__": ">",
    "__ge__": ">=",
    "__sq__": "'",
    "__dq__": '"',
}
for key, value in mapped_str.items():
    cond_text = cond_text.replace(key, value)

# Attempt to determine if the condition includes executable stuff and, if so, exit.
check_for_executable(cond_text, "condition")

if not check_expression(cond_text):
    stop_err("Illegal/invalid in condition '%s'" % (cond_text))

# Prepare the column variable names and wrappers for column data types. Only
# prepare columns up to largest column in condition.
attrs, type_casts = [], []
for name in attribute_types.keys():
    attrs.append(name)
    type_cast = "get_value('%(name)s', attribute_types['%(name)s'], attribute_values)" % ({"name": name})
    type_casts.append(type_cast)

attr_str = ", ".join(attrs)  # 'c1, c2, c3, c4'
type_cast_str = ", ".join(type_casts)  # 'str(c1), int(c2), int(c3), str(c4)'
wrap = "%s = %s" % (attr_str, type_cast_str)

# Stats
skipped_lines = 0
first_invalid_line = 0
invalid_line = None
lines_kept = 0
total_lines = 0
out = open(out_fname, "wt")


# Helper function to safely get and type cast a value in a dict.
def get_value(name, a_type, values_dict):
    if name in values_dict:
        return (a_type)(values_dict[name])
    else:
        return None


# Read and filter input file, skipping invalid lines
code = """
for i, line in enumerate( open( in_fname ) ):
    total_lines += 1
    line = line.rstrip( '\\r\\n' )
    if not line or line.startswith( '#' ):
        # Ignore blank lines or comments
        continue
    try:
        # Place attribute values into variables with attribute
        # name; type casting is done as well.
        elems = line.split( '\t' )
        attribute_values = {}
        for name_value_pair in elems[8].split(";"):
            # Split on first equals (GFF3) or space (legacy)
            name_value_pair = name_value_pair.strip()
            i = name_value_pair.replace(" ", "=").find("=")
            if i == -1:
                continue
            name = name_value_pair[:i].strip()
            if name == '':
                continue
            # Need to strip double quote from value and typecast.
            attribute_values[name] = name_value_pair[i+1:].strip(" \\"")
        %s
        if %s:
            lines_kept += 1
            print( line, file=out )
    except Exception as e:
        print( e )
        skipped_lines += 1
        if not invalid_line:
            first_invalid_line = i + 1
            invalid_line = line
""" % (
    wrap,
    cond_text,
)

valid_filter = True
try:
    exec(code)
except Exception as e:
    out.close()
    if str(e).startswith("invalid syntax"):
        valid_filter = False
        stop_err('Filter condition "%s" likely invalid. See tool tips, syntax and examples.' % cond_text)
    else:
        stop_err(str(e))

if valid_filter:
    out.close()
    valid_lines = total_lines - skipped_lines
    print("Filtering with %s, " % (cond_text))
    if valid_lines > 0:
        print("kept %4.2f%% of %d lines." % (100.0 * lines_kept / valid_lines, total_lines))
    else:
        print(
            'Possible invalid filter condition "%s" or non-existent column referenced. See tool tips, syntax and examples.'
            % cond_text
        )
    if skipped_lines > 0:
        print('Skipped %d invalid lines starting at line #%d: "%s"' % (skipped_lines, first_invalid_line, invalid_line))
