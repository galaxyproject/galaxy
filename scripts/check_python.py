import os, sys

def check_python():
    try:
        assert sys.version_info[:2] >= ( 2, 4 ) and sys.version_info[:2] <= ( 2, 5 )
    except AssertionError:
        print >>sys.stderr, "ERROR: Your Python version is:", sys.version.split( ' ', 1 )[0]
        print >>sys.stderr, "Galaxy is currently only supported on Python 2.4 and Python 2.5."
        if sys.version_info[:2] < ( 2, 4 ):
            print >>sys.stderr, "To run Galaxy, please download and install Python 2.5 from http://python.org"
        else:
            print >>sys.stderr, "To track the progress of Python 2.6 support, please see:"
            print >>sys.stderr, "  http://bitbucket.org/galaxy/galaxy-central/issue/76/support-python-26"
        print >>sys.stderr, "For hints on how to direct Galaxy to use a different python installation, see:"
        print >>sys.stderr, "  http://bitbucket.org/galaxy/galaxy-central/wiki/GetGalaxy"
        raise

if __name__ == '__main__':
    try:
        check_python()
    except:
        sys.exit( 1 )
