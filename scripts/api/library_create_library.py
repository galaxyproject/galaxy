#!/usr/bin/env python

import os
import sys

from common import submit

try:
    data = {}
    data["name"] = sys.argv[3]
except IndexError:
    print(f"usage: {os.path.basename(sys.argv[0])} key url name [description] [synopsys]")
    sys.exit(1)
try:
    data["description"] = sys.argv[4]
    data["synopsis"] = sys.argv[5]
except IndexError:
    pass

submit(sys.argv[1], sys.argv[2], data)
