#!/usr/bin/env python

"""
Populates blank uuid fields in datasets with randomly generated values

Going forward, these ids will be generated for all new datasets. This
script fixes datasets that were generated before the change.
"""

import sys, os, ConfigParser
import galaxy.app
from galaxy.util.bunch import Bunch
import galaxy.datatypes.tabular
from galaxy.model.orm.scripts import get_config
from galaxy import eggs
from galaxy.model import mapping
import uuid

eggs.require( "SQLAlchemy" )

from sqlalchemy import *

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    ini_file = sys.argv.pop(1)
    config = get_config(ini_file)

    model = mapping.init( ini_file, config['db_url'], create_tables = False )

    for row in model.context.query( model.Dataset ):
        if row.uuid is None:
            row.uuid = uuid.uuid4()
            print "Setting dataset:", row.id, " UUID to ", row.uuid
    model.context.flush()
    
    for row in model.context.query( model.Workflow ):
        if row.uuid is None:
            row.uuid = uuid.uuid4()
            print "Setting Workflow:", row.id, " UUID to ", row.uuid
    model.context.flush()


if __name__ == "__main__":
    main()
