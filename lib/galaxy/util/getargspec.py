import inspect


def getfullargspec(func):
    try:
        return inspect.getfullargspec(func)
    except AttributeError:
        # on python 2
        return inspect.getargspec(func)
