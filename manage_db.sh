#!/bin/sh

#######
# NOTE: To downgrade to a specific version, use something like:
# sh manage_db.sh downgrade --version=3 <community if using that webapp - galaxy is the default>
#######

cd `dirname $0`
python ./scripts/manage_db.py $@
