#!/usr/bin/env python

import os
import sys

from common import submit

try:
    data = {}
    data["name"] = sys.argv[3]
except IndexError:
    print("usage: %s key url name [description] [synopsys]" % os.path.basename(sys.argv[0]))
    sys.exit(1)
try:
    data["description"] = sys.argv[4]
    data["synopsis"] = sys.argv[5]
except IndexError:
    pass

submit(sys.argv[1], sys.argv[2], data)
