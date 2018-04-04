#!/bin/sh

cd `dirname $0`

. ./scripts/common_startup_functions.sh

setup_python

python ./scripts/create_db.py $@
