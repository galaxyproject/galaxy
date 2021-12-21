#!/bin/sh

#######
# NOTE: To downgrade to a specific version, use something like:
# TODO add instructions
# To create a revision for galaxy:
# ./manage_db.sh revision --head=gxy@head
# To create a revision for tool_shed_install:
# ./manage_db.sh revision --head=tsi@head
#######

ALEMBIC_CONFIG='lib/galaxy/model/migrations/alembic.ini'

cd `dirname $0`

. ./scripts/common_startup_functions.sh

setup_python

find lib/galaxy/model/migrations/alembic -name '*.pyc' -delete
python ./scripts/manage_db.py --config "$ALEMBIC_CONFIG" "$@"
