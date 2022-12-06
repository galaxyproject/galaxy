#!/bin/sh

#######
# Use this script to manage Tool Shed database migrations.
# NOTE: If your database is empty, use create_toolshed_db.sh instead.
#######

cd "$(dirname "$0")" || exit

. ./scripts/common_startup_functions.sh

setup_python

python ./scripts/migrate_toolshed_db.py "$@" tool_shed
