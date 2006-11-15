
# Attempt to load threadframe module, and only define Heartbeat class
# if available

try:

    import pkg_resources
    pkg_resources.require( "threadframe" )

except:
    
    import sys
    print >> sys.stderr, "No threadframe module, Heartbeat not available"
    Heartbeat = None
    
else:
    
    import threading
    import threadframe
    import time
    import traceback
    import os
    import sys
    
    def get_current_thread_object_dict():
        """
        Get a dictionary of all 'Thread' objects created via the threading
        module keyed by thread_id. Note that not all interpreter threads
        have a thread objects, only the main thread and any created via the
        'threading' module. Threads created via the low level 'thread' module
        will not be in the returned dictionary.
        
        HACK: This mucks with the internals of the threading module since that
              module does not expose any way to match 'Thread' objects with
              intepreter thread identifiers (though it should).
        """
        rval = dict()
        # Acquire the lock and then union the contents of 'active' and 'limbo'
        # threads into the return value. 
        threading._active_limbo_lock.acquire()
        rval.update( threading._active )
        rval.update( threading._limbo )
        threading._active_limbo_lock.release()
        return rval

    class Heartbeat( threading.Thread ):
        """
        Thread that periodically dumps the state of all threads to a file using
        the `threadframe` extension
        """
        def __init__( self, name="Heartbeat Thread", period=20, fname="heartbeat.log" ):
            threading.Thread.__init__( self, name=name )
            self.should_stop = False
            self.period = period
            self.fname = fname
            self.file = None
            # Save process id
            self.pid = os.getpid()
            # Event to wait on when sleeping, allows us to interrupt for shutdown
            self.wait_event = threading.Event()
        def run( self ):
            self.file = open( self.fname, "a" )
            print >> self.file, "Heartbeat for pid %d thread started at %s" % ( self.pid, time.asctime() )
            print >> self.file
            try:
                while not self.should_stop:
                    # Print separator with timestamp
                    print >> self.file, "Traceback dump for all threads at %s:" % time.asctime()
                    print >> self.file
                    # Print the thread states
                    threads = get_current_thread_object_dict()
                    for thread_id, frame in threadframe.dict().iteritems():
                        if thread_id in threads:
                            object = repr( threads[thread_id] )
                        else:
                            object = "<No Thread object>"
                        print >> self.file, "Thread %s, %s:" % ( thread_id, object )
                        print >> self.file
                        traceback.print_stack( frame, file=self.file )
                        print >> self.file
                    print >> self.file, "End dump"
                    print >> self.file
                    self.file.flush()
                    # Sleep for a bit
                    self.wait_event.wait( self.period )
            finally:
                print >> self.file, "Heartbeat for pid %d thread stopped at %s" % ( self.pid, time.asctime() )
                print >> self.file
                # Cleanup
                self.file.close()
        
        def shutdown( self ):
            self.should_stop = True
            self.wait_event.set()
            self.join()
        