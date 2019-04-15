"""
If the current installed Python version is not supported, prints an error
message to stderr and returns 1
"""
from __future__ import print_function

import sys

version_string = '.'.join(str(_) for _ in sys.version_info[:3])

msg = """ERROR: Your Python version is: %s
Galaxy is currently supported on Python 2.7 and >=3.5 . To run Galaxy, please
install a supported Python version. If a supported version is already
installed but is not your default, https://galaxyproject.org/admin/python/
contains instructions on how to force Galaxy to use a different version.""" % version_string


def check_python():
    if sys.version_info[:2] == (2, 7) or sys.version_info[:2] >= (3, 5):
        # supported
        return
    else:
        print(msg, file=sys.stderr)
        raise Exception(msg)


if __name__ == '__main__':
    try:
        check_python()
    except Exception:
        sys.exit(1)
