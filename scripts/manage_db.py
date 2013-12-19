""" This script parses Galaxy or Tool Shed config file for database connection
and then delegates to sqlalchemy_migrate shell main function in
migrate.versioning.shell. """
import sys
import os.path

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] )  # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs

eggs.require( "decorator" )
eggs.require( "Tempita" )
eggs.require( "SQLAlchemy" )
eggs.require( "sqlalchemy_migrate" )

from migrate.versioning.shell import main

from galaxy.model.orm.scripts import get_config


def invoke_migrate_main():
    config = get_config( sys.argv )
    db_url = config['db_url']
    repo = config['repo']

    main( repository=repo, url=db_url )

if __name__ == "__main__":
    invoke_migrate_main()
