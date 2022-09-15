#!/bin/env python3
#
# Use Galaxy's .venv python to set up the database stuff
#
# Prereqs:
#  * GALAXY_ROOT env must be set to the galaxy installation directory
#  * Must be run with galaxy's .venv python
#
# This is based on scripts/db_shell.py
# TODO: this should end up in the galaxy repository as part of the post or configure scripts!
import os
import sys
import argparse
import hashlib
import time

# Setup DB scripting environment
from sqlalchemy import *  # noqa
from sqlalchemy.orm import *  # noqa
from sqlalchemy.exc import *  # noqa
from sqlalchemy.sql import label  # noqa

# set up galaxy libraries to be in the path...
if 'GALAXY_ROOT' not in os.environ:
    print("The GALAXY_ROOT environment variable must be set")
    exit(1)
sys.path.insert(0, os.environ['GALAXY_ROOT'])
sys.path.insert(0, os.environ['GALAXY_ROOT'] + "/lib")

from galaxy.datatypes.registry import Registry
from galaxy.model import *  # noqa
from galaxy.model import set_datatypes_registry  # More explicit than `*` import
from galaxy.model.mapping import init
from galaxy.security.idencoding import IdEncodingHelper

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("galaxy_admin_user", help="Galaxy Admin account")
    parser.add_argument("galaxy_admin_password", help="Galaxy Admin Password")
    parser.add_argument("id_secret", help="The id_secret value")
    args = parser.parse_args()

    registry = Registry()
    registry.load_datatypes()
    set_datatypes_registry(registry)
    db_url = f"sqlite:///{os.environ['GALAXY_ROOT']}/database/universe.sqlite?isolation_level=IMMEDIATE"
    print(f"INFO: Using database at {db_url}", file=sys.stderr)
    sa_session = init('/tmp/', db_url).context


    # check the user, and add it if it doesn't exist
    #admin_user = sa_session.query(User).filter(User.email==args.galaxy_admin_user).first()
    admin_user = sa_session.query(User).filter(User.username=='ampuser').first()
    if admin_user is None:
        print("INFO: Creating user", file=sys.stderr)
        admin_user = User(args.galaxy_admin_user)
        admin_user.username = 'ampuser'
        admin_user.active = True
        admin_user.set_password_cleartext('abcdef')
        sa_session.add(admin_user)
        sa_session.flush()

    # update the password to match the config
    print("INFO: Resetting Email", file=sys.stderr)
    admin_user.email = args.galaxy_admin_user    
    print("INFO: Resetting password", file=sys.stderr)
    admin_user.set_password_cleartext(args.galaxy_admin_password)
    sa_session.add(admin_user)
    sa_session.flush()
    
    # set up the API key
    admin_key = sa_session.query(APIKeys).filter(APIKeys.user_id==admin_user.id).first()
    if admin_key:
        print("INFO: Clearing old API Key", file=sys.stderr)
        sa_session.delete(admin_key)
        sa_session.flush()
    api_key = hashlib.md5(bytes(args.galaxy_admin_user + args.galaxy_admin_password + str(time.time()), 'utf-8')).hexdigest()
    print(f"INFO: Creating a new API key -- {api_key}", file=sys.stderr)
    admin_key = APIKeys()
    admin_key.user_id = admin_user.id
    admin_key.key = api_key
    sa_session.add(admin_key)
    sa_session.flush()

    print("INFO: Generating the encoded user_id value", file=sys.stderr)
    security = IdEncodingHelper(id_secret=args.id_secret)
    user_hash = security.encode_id(admin_user.id)
    print(f"user_id={user_hash}")


if __name__ == "__main__":
    main()
