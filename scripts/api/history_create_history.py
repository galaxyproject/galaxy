#!/usr/bin/env python

import os
import sys

from common import submit

try:
    assert sys.argv[2]
except IndexError:
    print(f"usage: {os.path.basename(sys.argv[0])} key url [name] ")
    sys.exit(1)
try:
    data = {}
    data["name"] = sys.argv[3]
except IndexError:
    pass

submit(sys.argv[1], sys.argv[2], data)
