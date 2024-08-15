#!/usr/bin/env python
"""
python rpark_import_workflow_from_file.py 35a24ae2643785ff3d046c98ea362c7f http://localhost:8080/api/workflows/import 'spp_submodule.ga'
python rpark_import_workflow_from_file.py 35a24ae2643785ff3d046c98ea362c7f http://localhost:8080/api/workflows/import 'spp_submodule.ga'
"""

import json
import os
import sys

from common import submit


def openWorkflow(in_file):
    with open(in_file) as f:
        temp_data = json.load(f)
    return temp_data


try:
    assert sys.argv[2]
except IndexError:
    print(f"usage: {os.path.basename(sys.argv[0])} key url [name] ")
    sys.exit(1)
try:
    data = {}
    workflow_dict = openWorkflow(sys.argv[3])
    data["workflow"] = workflow_dict
except IndexError:
    pass

submit(sys.argv[1], sys.argv[2], data)
