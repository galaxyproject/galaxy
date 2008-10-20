
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
        def dump( self, signum, stack ):
            file = open( self.fname, "a" )
            print >> file, "Memdump for pid %d at %s" % ( os.getpid(), time.asctime() )
            print >> file
            try:
                h = self.heapy.heap()
                print >> file, "heap():"
                print >> file, h
                print >> file, "\nbyrcs:"
                print >> file, h.byrcs
                print >> file, "\nbyrcs[0].byid:"
                print >> file, h.byrcs[0].byid
                print >> file, "\nget_rp():"
                print >> file, h.get_rp()
                self.heapy.setref()
            except AssertionError:
                pass
            print >> file, "\nEnd dump\n"
            file.close()
