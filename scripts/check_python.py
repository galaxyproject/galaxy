import os, sys

msg = """ERROR: Your Python version is: %s
Galaxy is currently supported on Python 2.4, 2.5 and 2.6.  To run Galaxy,
please download and install a supported version from python.org.  If a
supported version is installed but is not your default, getgalaxy.org
contains instructions on how to force Galaxy to use a different version.""" % sys.version[:3]

def check_virtualenv():
    try:
        assert sys.real_prefix
        return 'python -E'
    except:
        return 'python -ES'

def check_python():
    try:
        assert sys.version_info[:2] >= ( 2, 4 ) and sys.version_info[:2] <= ( 2, 6 )
    except AssertionError:
        print >>sys.stderr, msg
        raise

if __name__ == '__main__':
    try:
        check_python()
        print check_virtualenv()
        sys.exit( 0 )
    except StandardError:
        sys.exit( 1 )
