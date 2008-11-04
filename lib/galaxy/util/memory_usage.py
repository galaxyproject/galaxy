import os, platform, logging
from galaxy.datatypes.data import nice_size

log = logging.getLogger( __name__ )

_proc_status = '/proc/%d/status' % os.getpid()

_scale = { 'kB': 1024.0, 'mB': 1024.0*1024.0, 'KB': 1024.0, 'MB': 1024.0*1024.0 }

def _VmB( VmKey ):
    '''Private.
    '''
    global _proc_status, _scale
     # get pseudo file  /proc/<pid>/status
    try:
        t = open( _proc_status )
        v = t.read()
        t.close()
    except:
        log.debug("memory_usage is currently supported only on Linux, your platform is %s %s" % ( platform.system(), platform.release() ) )
        return 0.0  # non-Linux?
     # get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
    i = v.index( VmKey )
    v = v[ i: ].split( None, 3 )  # whitespace
    if len( v ) < 3:
        return 0.0  # invalid format?
     # convert Vm value to bytes
    return float( v[ 1 ] ) * _scale[ v[ 2 ] ]
def memory( since=0.0, pretty=False ):
    '''Return memory usage in bytes.
    '''
    size = _VmB( 'VmSize:' ) - since
    if pretty:
        return nice_size( size )
    else:
        return size
def resident( since=0.0 ):
    '''Return resident memory usage in bytes.
    '''
    return _VmB( 'VmRSS:' ) - since
def stacksize( since=0.0 ):
    '''Return stack size in bytes.
    '''
    return _VmB( 'VmStk:' ) - since
