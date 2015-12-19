"""
Here for compat. with objectstore.
"""


class ObjectNotFound(Exception):
    """ Accessed object was not found """
    pass


class ObjectInvalid(Exception):
    """ Accessed object store ID is invalid """
    pass
