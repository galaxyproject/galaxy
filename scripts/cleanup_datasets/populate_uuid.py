#!/usr/bin/env python

"""
Populates blank uuid fields in datasets with randomly generated values

Going forward, these ids will be generated for all new datasets. This
script fixes datasets that were generated before the change.
"""
from __future__ import print_function

import sys
import uuid

from galaxy.model import mapping
from galaxy.model.orm.scripts import get_config

assert sys.version_info[:2] >= ( 2, 4 )


def usage(prog):
    print("usage: %s galaxy.ini" % prog)
    print("""
Populates blank uuid fields in datasets with randomly generated values.

Going forward, these ids will be generated for all new datasets. This
script fixes datasets that were generated before the change.
    """)


def main():
    if len(sys.argv) != 2 or sys.argv == "-h" or sys.argv == "--help":
        usage(sys.argv[0])
        sys.exit()
    ini_file = sys.argv.pop(1)
    config = get_config(ini_file)

    model = mapping.init( ini_file, config['db_url'], create_tables=False )

    for row in model.context.query( model.Dataset ):
        if row.uuid is None:
            row.uuid = uuid.uuid4()
            print("Setting dataset:", row.id, " UUID to ", row.uuid)
    model.context.flush()

    for row in model.context.query( model.Workflow ):
        if row.uuid is None:
            row.uuid = uuid.uuid4()
            print("Setting Workflow:", row.id, " UUID to ", row.uuid)
    model.context.flush()


if __name__ == "__main__":
    main()
