"""
If the current installed Python version is not supported, prints an error
message to stderr and returns 1
"""

from __future__ import print_function

import sys

MIN_VERSION_TUPLE = (3, 9)


def check_python():
    if sys.version_info[:2] >= MIN_VERSION_TUPLE:
        # supported
        return
    else:
        version_string = ".".join(str(_) for _ in sys.version_info[:3])
        min_version_string = ".".join(str(_) for _ in MIN_VERSION_TUPLE)
        msg = """ERROR: Your Python version is: {}
Galaxy is currently supported on Python >={} .
To run Galaxy, please install a supported Python version.
If a supported version is already installed but is not your default,
https://docs.galaxyproject.org/en/latest/admin/python.html contains instructions
on how to force Galaxy to use a different version.""".format(
            version_string,
            min_version_string,
        )
        print(msg, file=sys.stderr)
        raise Exception(msg)


if __name__ == "__main__":
    try:
        check_python()
    except Exception:
        sys.exit(1)
