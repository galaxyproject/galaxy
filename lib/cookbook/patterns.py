class Bunch:
    """
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52308

    Often we want to just collect a bunch of stuff together, naming each item of 
    the bunch; a dictionary's OK for that, but a small do-nothing class is even handier, and prettier to use.
    """
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def __iter__(self):
        return iter(self.__dict__)

    def items(self):
        return self.__dict__.items()

    def __str__(self):
        return '%s' % self.__dict__

    def __nonzero__(self):
        return bool(self.__dict__)

# class Bunch( dict ):
#     """
#     Bunch based on a dict
#     """
#     def __getattr__( self, key ):
#         if key not in self: raise AttributeError, key
#         return self[key]
#     def __setattr__( self, key, value ):
#         self[key] = value

class Null:
    """
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/68205

    A class for implementing Null objects.

    This class ignores all parameters passed when constructing or 
    calling instances and traps all attribute and method requests. 
    Instances of it always (and reliably) do 'nothing'.
    """

    # object constructing
    def __init__(self, *args, **kwargs):
        "Ignore parameters."
        return None

    # object calling
    def __call__(self, *args, **kwargs):
        "Ignore method calls."
        return self

    # attribute handling
    def __getattr__(self, mname):
        "Ignore attribute requests."
        return self

    def __setattr__(self, name, value):
        "Ignore attribute setting."
        return self

    def __delattr__(self, name):
        "Ignore deleting attributes."
        return self

    # misc.
    def __repr__(self):
        "Return a string representation."
        return "<Null>"

    def __str__(self):
        "Convert to a string and return it."
        return "Null"

class Borg:
    """
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66531

    The Singleton design pattern (DP) has a catchy name, but the wrong focus 
    -- on identity rather than on state. The Borg design pattern has all instances 
    share state.
    """
    __shared_state = {}
    def __init__(self):
        self.__dict__ = self.__shared_state
    # and whatever else you want in your class -- that's all!


if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__], verbose=False)
