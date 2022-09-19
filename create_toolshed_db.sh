#!/bin/sh

#######
# Use this script to verify the state of the Tool Shed database.
# If the database does not exist or is empty, it will be created
# and initialized.
# (For Galaxy and Tool Shed Install databases, use create_db.sh).
#######

cd "$(dirname "$0")"

. ./scripts/common_startup_functions.sh

setup_python

python ./scripts/create_toolshed_db.py "$@" tool_shed
