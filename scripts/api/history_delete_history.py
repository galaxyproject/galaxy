#!/usr/bin/env python

import os
import sys

from common import delete

try:
    assert sys.argv[2]
except IndexError:
    print(f"usage: {os.path.basename(sys.argv[0])} key url [purge (true/false)] ")
    sys.exit(1)
try:
    data = {}
    data["purge"] = sys.argv[3]
except IndexError:
    pass

delete(sys.argv[1], sys.argv[2], data)
