#!/bin/sh

# draft of script to replace manage_db.sh
cd `dirname $0`

. ./scripts/common_startup_functions.sh

setup_python

python ./scripts/db.py "$@"
