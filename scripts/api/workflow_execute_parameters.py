#!/usr/bin/env python
"""
# ---------------------------------------------- #
# PARKLAB, Author: RPARK
# ---------------------------------------------- #

Execute workflows from the command line.
Example calls:
python workflow_execute.py <api_key> <galaxy_url>/api/workflows <workflow_id> 'hist_id=<history_id>' '38=hda=<file_id>' 'param=tool=name=value'
python workflow_execute_parameters.py <api_key> http://localhost:8080/api/workflows 1cd8e2f6b131e891 'Test API' '69=ld=a799d38679e985db' '70=ld=33b43b4e7093c91f' 'param=peakcalling_spp=aligner=bowtie' 'param=bowtie_wrapper=suppressHeader=True' 'param=peakcalling_spp=window_size=1000'
"""

import os
import sys

from common import submit


def main():
    try:
        print("workflow_execute:py:")
        data = {}
        data["workflow_id"] = sys.argv[3]
        data["history"] = sys.argv[4]
        data["ds_map"] = {}

        # Trying to pass in parameter for my own dictionary
        data["parameters"] = {}

        # DBTODO If only one input is given, don't require a step
        # mapping, just use it for everything?
        for v in sys.argv[5:]:
            print("Multiple arguments ")
            print(v)

            try:
                step, src, ds_id = v.split("=")
                data["ds_map"][step] = {"src": src, "id": ds_id}

            except ValueError:
                print("VALUE ERROR:")
                wtype, wtool, wparam, wvalue = v.split("=")
                try:
                    data["parameters"][wtool] = {"param": wparam, "value": wvalue}
                except ValueError:
                    print("TOOL ID ERROR:")

    except IndexError:
        print(f"usage: {os.path.basename(sys.argv[0])} key url workflow_id history step=src=dataset_id")
        sys.exit(1)
    submit(sys.argv[1], sys.argv[2], data)


if __name__ == "__main__":
    main()
