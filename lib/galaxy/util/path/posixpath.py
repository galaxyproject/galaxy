"""Galaxy "safe" path functions forced to work with POSIX-style paths regardless of current platform"""

import posixpath
import sys

from . import _build_self

_build_self(sys.modules[__name__], posixpath)
