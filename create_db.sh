#!/bin/sh

#######
# Use this script to verify the state of the Galaxy and Tool Shed Install
# database(s). If the database does not exist or is empty, it will be created
# and initialized.
# (Use create_toolshed_db.sh to create and initialize a new
# Tool Shed database.)
#
# To pass a galaxy config file, use `--galaxy-config`
#
# You may also override the galaxy database url and/or the
# tool shed install database url, as well as the database_template
# and database_encoding configuration options with env vars:
# GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION=my-db-url ./create_db.sh
# GALAXY_INSTALL_CONFIG_OVERRIDE_DATABASE_CONNECTION=my-other-db-url ./create_db.sh
#######

cd "$(dirname "$0")"

. ./scripts/common_startup_functions.sh

setup_python

python ./scripts/create_db.py "$@"
