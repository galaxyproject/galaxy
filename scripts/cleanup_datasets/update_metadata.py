#!/usr/bin/env python
# Dan Blankenberg
"""
Updates metadata in the database to match rev 1891.

Remember to backup your database before running.
"""
from __future__ import print_function

import os
import sys

from six.moves import configparser

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'lib')))

import galaxy.app
import galaxy.datatypes.tabular

assert sys.version_info[:2] >= ( 2, 4 )


def usage(prog):
    print("usage: %s galaxy.ini" % prog)
    print("""
Updates the metadata in the database to match rev 1981.

Remember to backup your database before running.
    """)


def main():
    if len(sys.argv) != 2 or sys.argv[1] == "-h" or sys.argv[1] == "--help":
        usage(sys.argv[0])
        sys.exit()
    ini_file = sys.argv.pop(1)
    conf_parser = configparser.ConfigParser({'here': os.getcwd()})
    conf_parser.read(ini_file)
    configuration = {}
    for key, value in conf_parser.items("app:main"):
        configuration[key] = value
    app = galaxy.app.UniverseApplication( global_conf=ini_file, **configuration )

    # Search out tabular datatypes (and subclasses) and initialize metadata
    print("Seeking out tabular based files and initializing metadata")
    for row in app.model.Dataset.table.select().execute():
        data = app.model.Dataset.get(row.id)
        if issubclass(type(data.datatype), type(app.datatypes_registry.get_datatype_by_extension('tabular'))):
            print(row.id, data.extension)
            # Call meta_data for all tabular files
            # special case interval type where we do not want to overwrite chr, start, end, etc assignments
            if issubclass(type(data.datatype), type(app.datatypes_registry.get_datatype_by_extension('interval'))):
                galaxy.datatypes.tabular.Tabular().set_meta(data)
            else:
                data.set_meta()
            app.model.context.add( data )
            app.model.context.flush()

    app.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
