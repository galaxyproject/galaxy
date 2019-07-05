#!/bin/sh

#######
# NOTE: To downgrade to a specific version, use something like:
# sh manage_db.sh downgrade --version=3 <tool_shed if using that webapp - galaxy is the default>
#######

cd `dirname $0`

. ./scripts/common_startup_functions.sh

setup_python

python ./scripts/manage_db.py $@
