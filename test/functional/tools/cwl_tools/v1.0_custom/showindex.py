#!/usr/bin/env python

from __future__ import print_function

import sys

indexfile = sys.argv[1] + ".idx1"

index = open(indexfile, "r").read()

print(index)
