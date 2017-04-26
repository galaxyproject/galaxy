#!/usr/bin/env python
"""
Updates dataset.size column.
Remember to backup your database before running.
"""
from __future__ import print_function

import os
import sys

from six.moves import configparser

import galaxy.app

assert sys.version_info[:2] >= ( 2, 4 )


def usage(prog):
    print("usage: %s galaxy.ini" % prog)
    print("""
Updates the dataset.size column. Users are advised to backup the database before
running.
    """)


def main():
    if len(sys.argv) != 1 or sys.argv[1] == "-h" or sys.argv[1] == "--help":
        usage(sys.argv[0])
        sys.exit()
    ini_file = sys.argv.pop(1)
    conf_parser = configparser.ConfigParser( {'here': os.getcwd()} )
    conf_parser.read( ini_file )
    configuration = {}
    for key, value in conf_parser.items( "app:main" ):
        configuration[key] = value
    app = galaxy.app.UniverseApplication( global_conf=ini_file, **configuration )

    # Step through Datasets, determining size on disk for each.
    print("Determining the size of each dataset...")
    for row in app.model.Dataset.table.select().execute():
        purged = app.model.Dataset.get( row.id ).purged
        file_size = app.model.Dataset.get( row.id ).file_size
        if file_size is None and not purged:
            size_on_disk = app.model.Dataset.get( row.id ).get_size()
            print("Updating Dataset.%d with file_size: %d" % ( row.id, size_on_disk ))
            app.model.Dataset.table.update( app.model.Dataset.table.c.id == row.id ).execute( file_size=size_on_disk )
    app.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
