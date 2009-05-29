class Bunch( object ):
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

    def __setitem__(self, k, v):
        self.__dict__.__setitem__(k, v)
