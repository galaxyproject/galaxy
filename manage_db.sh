#!/bin/sh

#######
# NOTE: To downgrade to a specific version, use something like:
# sh manage_db.sh downgrade --version=3
#######

cd `dirname $0`
python ./scripts/manage_db.py $@
