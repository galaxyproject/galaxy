#!/bin/sh

#######
# Use this script to manage Tool Shed database migrations.
# For help, run `sh manage_db.sh -h`. 
# For detailed help, see documentation at https://docs.galaxyproject.org/en/master/admin/db_migration.html
#######

cd "$(dirname "$0")" || exit

. ./scripts/common_startup_functions.sh

setup_python

python ./scripts/toolshed_db.py "$@"
