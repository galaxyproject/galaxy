# This script allows easy access to Galaxy's database layer via the
# Galaxy models. For example:
# % python -i scripts/db_shell.py
# >>> new_user = User("admin@gmail.com")
# >>> new_user.set_password
# >>> sa_session.add(new_user)
# >>> sa_session.commit()
# >>> sa_session.query(User).all()
#
# You can also use this script as a library, for instance see https://gist.github.com/1979583
# TODO: This script overlaps a lot with manage_db.py and create_db.py,
# these should maybe be refactored to remove duplication.
import sys
import os.path

db_shell_path = __file__
new_path = [ os.path.join( os.path.dirname( db_shell_path ), os.path.pardir,  "lib" ) ]
new_path.extend( sys.path[1:] )  # remove scripts/ from the path
sys.path = new_path

from galaxy.model.orm.scripts import get_config

from galaxy import eggs
eggs.require( "decorator" )
eggs.require( "Tempita" )
eggs.require( "SQLAlchemy" )

db_url = get_config( sys.argv )['db_url']


# Setup DB scripting environment
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *

from galaxy.model.mapping import init
sa_session = init( '/tmp/', db_url ).context
from galaxy.model import *
