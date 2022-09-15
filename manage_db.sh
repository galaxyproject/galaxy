#!/bin/sh

#######
# Use this script to manage Galaxy database schema migrations.
# For help, run `sh manage_db.sh -h`. 
# For detailed help, see documentation at lib/galaxy/model/migrations/README.md.
#######

cd "$(dirname "$0")" || exit

. ./scripts/common_startup_functions.sh

setup_python

python ./scripts/db.py "$@"
