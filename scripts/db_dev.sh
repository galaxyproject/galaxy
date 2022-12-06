#!/bin/sh

#######
# Extended set of database schema migration operaions.
# For help, run `sh db_dev.sh -h`. 
# For detailed help, see documentation at lib/galaxy/model/migrations/README.md.
#######

cd "$(dirname "$0")" || exit

cd ..

. ./scripts/common_startup_functions.sh

setup_python

python scripts/db_dev.py "$@"
