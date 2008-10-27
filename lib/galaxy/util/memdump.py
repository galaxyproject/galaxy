
# Attempt to load guppy module, and only define Memdump class
# if available

try:

    import pkg_resources
    pkg_resources.require( "guppy" )

except:
    
    import sys
    print >> sys.stderr, "No guppy module, Memdump not available"
    Memdump = None
    
else:
    
    import os, sys, signal, time, guppy
    
    class Memdump( object ):
        def __init__( self, signum=signal.SIGUSR1, fname="memdump.log" ):
            self.fname = fname
            signal.signal( signum, self.dump )
            self.heapy = guppy.hpy()
            self.heap = None
        def dump( self, signum, stack ):
            file = open( self.fname, "a" )
            print >> file, "Memdump for pid %d at %s" % ( os.getpid(), time.asctime() )
            print >> file
            try:
                self.heap = self.heapy.heap()
                print >> file, "heap():"
                print >> file, self.heap
                print >> file, "\nbyrcs:"
                print >> file, self.heap.byrcs
                print >> file, "\nbyrcs[0].byid:"
                print >> file, self.heap.byrcs[0].byid
                print >> file, "\nget_rp():"
                print >> file, self.heap.get_rp()
                self.heapy.setref()
            except AssertionError:
                pass
            print >> file, "\nEnd dump\n"
            file.close()
        def setref( self ):
            self.heapy.setref()
        def get( self, update=False ):
            if update:
                self.heap = self.heapy.heap()
            return self.heap
