#!/usr/bin/env python
"""
Execute workflows from the command line.
Example calls:
python workflow_execute.py <api_key> <galaxy_url>/api/workflows f2db41e1fa331b3e 'Test API History' '38=ldda=0qr350234d2d192f'
python workflow_execute.py <api_key> <galaxy_url>/api/workflows f2db41e1fa331b3e 'hist_id=a912e9e5d84530d4' '38=hda=03501d7626bd192f'
"""

import os
import sys

from common import submit


def main():
    try:
        data = {}
        data["workflow_id"] = sys.argv[3]
        data["history"] = sys.argv[4]
        data["ds_map"] = {}
        # DBTODO If only one input is given, don't require a step
        # mapping, just use it for everything?
        for v in sys.argv[5:]:
            step, src, ds_id = v.split("=")
            data["ds_map"][step] = {"src": src, "id": ds_id}
    except IndexError:
        print(f"usage: {os.path.basename(sys.argv[0])} key url workflow_id history step=src=dataset_id")
        sys.exit(1)
    submit(sys.argv[1], sys.argv[2], data)


if __name__ == "__main__":
    main()
