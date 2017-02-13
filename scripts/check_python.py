"""
If the current installed python version is not 2.7, prints an error
message to stderr and returns 1
"""
from __future__ import print_function

import sys

msg = """ERROR: Your Python version is: %s
Galaxy is currently supported on Python 2.7 only.  To run Galaxy,
please download and install a supported version from python.org.  If a
supported version is installed but is not your default, getgalaxy.org
contains instructions on how to force Galaxy to use a different version.""" % sys.version[:3]


def check_python():
    try:
        assert sys.version_info[:2] == ( 2, 7 )
    except AssertionError:
        print(msg, file=sys.stderr)
        raise


if __name__ == '__main__':
    rval = 0
    try:
        check_python()
    except Exception:
        rval = 1
    sys.exit( rval )
