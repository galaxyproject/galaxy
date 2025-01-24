#!/usr/bin/env python

import os
import sys

from common import submit

try:
    data = {}
    data["folder_id"] = sys.argv[3]
    data["name"] = sys.argv[4]
    data["create_type"] = "folder"
except IndexError:
    print(f"usage: {os.path.basename(sys.argv[0])} key url folder_id name [description]")
    sys.exit(1)
try:
    data["description"] = sys.argv[5]
except IndexError:
    print("Unable to set description; using empty description in its place")
    data["description"] = ""

submit(sys.argv[1], sys.argv[2], data)
