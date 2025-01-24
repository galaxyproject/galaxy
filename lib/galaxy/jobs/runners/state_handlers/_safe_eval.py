from ast import (
    parse,
    walk,
)

AST_NODE_TYPE_ALLOWLIST = [
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
    "Constant",
    # Further checks
    "Name",
    "Call",
    "Attribute",
]


BUILTIN_AND_MATH_FUNCTIONS = "abs|all|any|bin|chr|cmp|complex|divmod|float|hex|int|len|long|max|min|oct|ord|pow|range|reversed|round|sorted|str|sum|type|unichr|unicode|log|exp|sqrt|ceil|floor".split(
    "|"
)
STRING_AND_LIST_METHODS = [name for name in dir("") + dir([]) if not name.startswith("_")]
VALID_FUNCTIONS = BUILTIN_AND_MATH_FUNCTIONS + STRING_AND_LIST_METHODS


def _check_name(ast_node, allowed_variables=None):
    if allowed_variables is None:
        allowed_variables = []
    name = ast_node.id
    return name in (VALID_FUNCTIONS + allowed_variables)


def _check_attribute(ast_node):
    attribute_name = ast_node.attr
    if attribute_name not in STRING_AND_LIST_METHODS:
        return False
    return True


def _check_call(ast_node):
    # If we are calling a function or method, it better be a math,
    # string or list function.
    ast_func = ast_node.func
    ast_func_class = ast_func.__class__.__name__
    if ast_func_class == "Name":
        if ast_func.id not in BUILTIN_AND_MATH_FUNCTIONS:
            return False
    elif ast_func_class == "Attribute":
        if not _check_attribute(ast_func):
            return False
    else:
        return False

    return True


def _check_expression(text, allowed_variables=None):
    """

    >>> allowed_variables = ["c1", "c2", "c3", "c4", "c5"]
    >>> _check_expression("c1", allowed_variables)
    True
    >>> _check_expression("eval('1+1')", allowed_variables)
    False
    >>> _check_expression("import sys", allowed_variables)
    False
    >>> _check_expression("[].__str__", allowed_variables)
    False
    >>> _check_expression("__builtins__", allowed_variables)
    False
    >>> _check_expression("'x' in globals", allowed_variables)
    False
    >>> _check_expression("'x' in [1,2,3]", allowed_variables)
    True
    >>> _check_expression("c3=='chr1' and c5>5", allowed_variables)
    True
    >>> _check_expression("c3=='chr1' and d5>5", allowed_variables)  # Invalid d5 reference
    False
    >>> _check_expression("c3=='chr1' and c5>5 or exec", allowed_variables)
    False
    >>> _check_expression("type(c1) != type(1)", allowed_variables)
    True
    >>> _check_expression("c1.split(',')[1] == '1'", allowed_variables)
    True
    >>> _check_expression("exec 1", allowed_variables)
    False
    >>> _check_expression("str(c2) in [\\\"a\\\",\\\"b\\\"]", allowed_variables)
    True
    """
    if allowed_variables is None:
        allowed_variables = []
    try:
        module = parse(text)
    except SyntaxError:
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
        if ast_node_class not in AST_NODE_TYPE_ALLOWLIST:
            return False

        # White-list more potentially dangerous types AST elements.
        if ast_node_class == "Name":
            # In order to prevent loading 'exec', 'eval', etc...
            # put string restriction on names allowed.
            if not _check_name(ast_node, allowed_variables):
                return False
        # Check only valid, white-listed functions are called.
        elif ast_node_class == "Call":
            if not _check_call(ast_node):
                return False
        # Check only valid, white-listed attributes are accessed
        elif ast_node_class == "Attribute":
            if not _check_attribute(ast_node):
                return False

    return True


def safe_eval(expression, variables):
    """

    >>> safe_eval("moo", {"moo": 5})
    5
    >>> exception_thrown = False
    >>> try: safe_eval("moo", {"cow": 5})
    ... except Exception as e: exception_thrown = True
    >>> exception_thrown
    True
    """
    if not _check_expression(expression, allowed_variables=list(variables.keys())):
        raise Exception(f"Invalid expression [{expression}], only a very simple subset of Python is allowed.")
    return eval(expression, globals(), variables)
