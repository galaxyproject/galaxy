import os, sys

msg = """ERROR: Your Python version is: %s
Galaxy is currently supported on Python 2.5, 2.6 and 2.7.  To run Galaxy,
please download and install a supported version from python.org.  If a
supported version is installed but is not your default, getgalaxy.org
contains instructions on how to force Galaxy to use a different version.""" % sys.version[:3]

def check_python():
    try:
        assert sys.version_info[:2] >= ( 2, 5 ) and sys.version_info[:2] <= ( 2, 7 )
    except AssertionError:
        print >>sys.stderr, msg
        raise

if __name__ == '__main__':
    rval = 0
    try:
        check_python()
    except StandardError:
        rval = 1
    sys.exit( rval )
