#!/usr/bin/env python
"""
Import workflows from the command line.
Example calls:
python workflow_import.py <api_key> <galaxy_url> '/path/to/workflow/file [--add_to_menu]'
"""
from __future__ import print_function

import os
import sys

from common import submit


def main():
    api_key = sys.argv[1]
    api_base_url = sys.argv[2]
    api_url = "%s/api/workflows" % api_base_url
    try:
        data = {}
        data['installed_repository_file'] = sys.argv[3]
        if len(sys.argv) > 4 and sys.argv[4] == "--add_to_menu":
            data['add_to_menu'] = True
    except IndexError:
        print('usage: %s key galaxy_url workflow_file' % os.path.basename(sys.argv[0]))
        sys.exit(1)
    # print display( api_key, api_base_url + "/api/workflows" )
    submit( api_key, api_url, data, return_formatted=False )


if __name__ == '__main__':
    main()
