#!/usr/bin/env python2.4
#Dan Blankenberg
"""
Updates metadata in the database to match rev 1891.

Remember to backup your database before running.
"""

import sys, os, ConfigParser
import galaxy.app
from galaxy.util.bunch import Bunch
import galaxy.datatypes.tabular


def main():
    ini_file = sys.argv.pop(1)
    conf_parser = ConfigParser.ConfigParser({'here':os.getcwd()})
    conf_parser.read(ini_file)
    configuration = {}
    for key, value in conf_parser.items("app:main"): configuration[key] = value
    app = galaxy.app.UniverseApplication( global_conf = ini_file, **configuration )
    
    #Step through Database, turning metadata bunches into dictionaries.
    #print "Changing metadata bunches to dictionaries."
    #for row in app.model.Dataset.table.select().execute():
    #    if isinstance (row.metadata, Bunch):
    #        print row.id
    #        app.model.Dataset.table.update(app.model.Dataset.table.c.id == row.id).execute( _metadata = row.metadata.__dict__ )
    
    #Make sure all metadata is jsonified
    #print "Rewriting all metadata to database, setting metadata dbkey, to ensure JSONified storage."
    #for row in app.model.Dataset.table.select().execute():
    #    print row.id
    #    data = app.model.Dataset.get(row.id)
    #    dbkey = data.old_dbkey
    #    if not dbkey or data.metadata.dbkey not in ["?", ["?"], None, []]:
    #        dbkey = data.metadata.dbkey
    #    if not dbkey: dbkey = "?"
    #    #change dbkey then flush, then change to real value and flush, ensures that metadata is rewritten to database
    #    data.dbkey="~"
    #    data.flush()
    #    data.dbkey=dbkey
    #    data.flush()
    
    
    #Search out tabular datatypes and make sure that number of columns is set.
    #print "Seeking out tabular based files and setting number of columns."
    #for row in app.model.Dataset.table.select().execute():
    #    data = app.model.Dataset.get(row.id)
    #    if issubclass(type(data.datatype), type(app.datatypes_registry.get_datatype_by_extension('tabular'))):
    #        print row.id
    #        galaxy.datatypes.tabular.Tabular().set_meta( data ) #Call tabular set metadata method for all Classes, this will set number of columns.
    #        data.flush()
            
    #Search out maf datatypes and make sure that available species is set.
    print "Seeking out maf files and setting available species."
    for row in app.model.Dataset.table.select(app.model.Dataset.table.c.extension == 'maf').execute():
        print row.id
        sys.stdout.flush()
        data = app.model.Dataset.get(row.id)
        if data.missing_meta:
            data.set_meta() #Call maf set metadata method, setting available species
            data.flush()
    
    app.shutdown()
    sys.exit(0)

if __name__ == "__main__":
    main()