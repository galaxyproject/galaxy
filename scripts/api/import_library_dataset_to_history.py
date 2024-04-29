#!/usr/bin/env python

import os
import sys

from common import submit

try:
    assert sys.argv[3]
    data = {}
    data["from_ld_id"] = sys.argv[3]
except IndexError:
    print(f"usage: {os.path.basename(sys.argv[0])} key url library_file_id")
    print("    library_file_id is from /api/libraries/<library_id>/contents/<library_file_id>")
    sys.exit(1)

submit(sys.argv[1], sys.argv[2], data)
