"""
If the current installed Python version is not supported, prints an error
message to stderr and returns 1
"""

from __future__ import print_function  # noqa: UP010

import sys


def check_python():
    if sys.version_info[:2] >= (3, 8):  # noqa: UP036
        # supported
        return
    else:
        version_string = ".".join(str(_) for _ in sys.version_info[:3])
        msg = (
            """ERROR: Your Python version is: %s
Galaxy is currently supported on Python >=3.8 .
To run Galaxy, please install a supported Python version.
If a supported version is already installed but is not your default,
https://docs.galaxyproject.org/en/latest/admin/python.html contains instructions
on how to force Galaxy to use a different version."""  # noqa: UP031
            % version_string
        )
        print(msg, file=sys.stderr)
        raise Exception(msg)


if __name__ == "__main__":
    try:
        check_python()
    except Exception:
        sys.exit(1)
