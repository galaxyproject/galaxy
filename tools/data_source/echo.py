#!/usr/bin/env python

"""
Script that just echos the command line.
"""

import sys

assert sys.version_info[:2] >= ( 2, 4 )

print '-' * 20, "<br>"
for elem in sys.argv:
    print elem, "<br>"
print '-' * 20, "<br>"