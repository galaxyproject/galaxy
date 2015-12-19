import threading


class Sleeper( object ):
    """
    Provides a 'sleep' method that sleeps for a number of seconds *unless*
    the notify method is called (from a different thread).
    """
    def __init__( self ):
        self.condition = threading.Condition()

    def sleep( self, seconds ):
        # Should this be in a try/finally block? -John
        self.condition.acquire()
        self.condition.wait( seconds )
        self.condition.release()

    def wake( self ):
        # Should this be in a try/finally block? -John
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()
