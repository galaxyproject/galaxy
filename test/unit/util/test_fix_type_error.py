from galaxy.util.pastescript.loadwsgi import fix_type_error

argtype = ""
EXP_STRING = (
    "a_func() got multiple values for%s argument 'kwarg'; got (1, 2, kwarg=...), wanted (argone, kwarg=True)" % argtype
)


def a_func(argone, kwarg=True):
    pass


def test_fix_type_error():
    args = [1, 2]
    kwargs = {"kwarg": False}
    try:
        a_func(*args, **kwargs)
    except TypeError:
        exc_info = fix_type_error(None, a_func, args, kwargs)
    assert exc_info[1].args[0] == EXP_STRING
