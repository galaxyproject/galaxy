#!/usr/bin/env python

import sys

assert sys.version_info[:2] >= ( 2, 4 )

from eggs import get_full_platform, get_noplatform
print get_noplatform()
print get_full_platform()
